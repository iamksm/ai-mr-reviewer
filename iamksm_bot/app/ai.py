import base64
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Iterable, List

import gitlab
import ollama
import ollama._client
from gitlab.base import RESTObjectList
from gitlab.v4.objects.merge_request_approvals import ProjectMergeRequestApproval
from gitlab.v4.objects.merge_requests import ProjectMergeRequest
from gitlab.v4.objects.projects import Project
from requests import Response

from iamksm_bot.app.template import PROMPT_TEMPLATE, SYSTEM_PERSONA
from iamksm_bot.app.utils import download_and_read_repo_files_from_path, timer
from iamksm_bot.config.settings import settings

LOGGER: logging.Logger = logging.getLogger(__name__)
GITLAB_URL: str = settings.GITLAB_URL
GITLAB_TOKEN: str = settings.GITLAB_TOKEN
REPO_INSTALL_PATH = settings.REPO_INSTALL_PATH
OLLAMA_OPTIONS = settings.OLLAMA_OPTIONS
OLLAMA_MODEL = settings.OLLAMA_MODEL
GITLAB_BOT_USER_ID = 352


class IAMKSM:
    def __init__(self):
        self.gl = gitlab.Gitlab(url=GITLAB_URL, private_token=GITLAB_TOKEN)
        self.gl.auth()
        workers: int = min(os.cpu_count() * 5, 10)
        self.executor = ThreadPoolExecutor(max_workers=workers)

    def read_blob(self, path, project: Project, default_branch: str) -> str:
        file = project.files.get(file_path=path, ref=default_branch)
        file_contents = base64.b64decode(file.content).decode("utf-8")

        return file_contents.replace("\\n", "\n")

    def set_file_path(self, file_path, project, default_branch, repo_files_content):
        content: str = self.read_blob(file_path, project, default_branch)
        repo_files_content[file_path] = content

    def work_on_item(
        self,
        item: Dict[str, Any],
        repo_files_content: Dict[str, str],
        project: Project,
        default_branch: str,
    ) -> None:
        if item["type"] == "blob" and item["path"]:
            self.executor.submit(
                self.set_file_path,
                item["path"],
                project,
                default_branch,
                repo_files_content,
            )

        elif item["type"] == "tree":
            self.read_tree(
                project=project,
                default_branch=default_branch,
                file_path=item["path"],
                repo_files_content=repo_files_content,
            )

    def read_tree(
        self,
        project: Project,
        default_branch: str,
        file_path: str = "",
        repo_files_content=None,
    ) -> Dict[str, str]:
        repo_files_content: Dict[str, Any] = repo_files_content or {}

        options: Dict[str, Any] = {
            "recursive": True,
            "ref": default_branch,
            "all": True,
        }

        if file_path is not None:
            options["path"] = file_path

        for item in project.repository_tree(**options):
            self.work_on_item(item, repo_files_content, project, default_branch)

        return repo_files_content

    def get_repo_context(self, project: Project, default_branch: str) -> Dict[str, Any]:
        repo_files_content: Dict[str, str] = {}

        return self.read_tree(
            project=project,
            default_branch=default_branch,
            repo_files_content=repo_files_content,
        )

    def setup_commit_info(self, commits: RESTObjectList):
        for msg in commits:
            yield {"Commit title": msg.title, "Commit description": msg.message}

    def map_changes_to_file_path(
        self, project: Project, changes: Iterable, default_branch: str
    ) -> Dict[str, str]:
        file_paths_context: Dict[str, str] = {}

        threads = (
            self.executor.submit(
                self.set_file_path,
                change["new_path"],
                project,
                default_branch,
                file_paths_context,
            )
            for change in changes
        )

        for t in as_completed(threads):
            t.exception()

        return file_paths_context

    def map_changes_to_file_paths(self, project: Project, mr_changes) -> Dict[str, str]:
        return self.map_changes_to_file_path(
            project=project,
            changes=mr_changes["changes"],
            default_branch=project.default_branch,
        )

    def get_repository_contents(self, project: Project) -> Dict[str, str]:
        zipped_archive = project.repository_archive(format="zip")
        return download_and_read_repo_files_from_path(
            name=project.name,
            zipped_archive=zipped_archive,
            base_path=REPO_INSTALL_PATH,
        )

    def construct_prompt(
        self,
        mr: ProjectMergeRequest,
        repo_contents: Dict[str, str],
        file_paths_context: Dict[str, str],
        mr_changes,
    ) -> str:
        mr_title = mr_changes["title"]
        mr_desc = mr_changes["description"]
        commits = tuple(self.setup_commit_info(commits=mr.commits()))
        changes = mr_changes["changes"]

        return PROMPT_TEMPLATE.format(
            repo=repo_contents,
            mr_title=mr_title,
            mr_desc=mr_desc,
            commits=commits,
            changes=changes,
            file_paths_context=file_paths_context,
            all_changes=mr_changes,
        )

    def define_system_persona(self) -> str:
        return SYSTEM_PERSONA

    def generate_response(self, prompt: str) -> str:
        response = ollama.generate(
            model=OLLAMA_MODEL,
            prompt=prompt,
            system=SYSTEM_PERSONA,
            options=OLLAMA_OPTIONS,
            stream=False,
        )
        return response["response"]

    def process_response(
        self, mr: ProjectMergeRequest, response: str, mr_changes
    ) -> None:
        """
        Processes the response of an MR review and takes actions based on the response.

        Explanation:
        - Checks if the response indicates approval or disapproval.
        - Creates notes or discussions accordingly and updates the approval status.
        - Logs the outcome of the approval process.

        Args:
        - `mr`: ProjectMergeRequest object representing the merge request.
        - `response`: String containing the response of the review.
        - `mr_changes`: Dictionary containing the changes in the merge request.

        Returns:
        - None
        """
        approvals: ProjectMergeRequestApproval = mr.approvals.get()
        approved_by: List[Dict[str, Dict[str, Any]]] = getattr(
            approvals, "approved_by", []
        )
        bot_already_approved: bool = any(
            payload["user"]["id"] == GITLAB_BOT_USER_ID for payload in approved_by
        )

        if "✅ Approved" in response:
            if not bot_already_approved:
                mr.notes.create({"body": response})
                mr.approve()

            LOGGER.info(f"APPROVED: {mr_changes['title']}")
        else:
            mr.discussions.create({"body": response})

            if bot_already_approved:
                mr.unapprove()

            LOGGER.info(f"NOT APPROVED: {mr_changes['title']}")

    @timer
    def review_project_open_merge_request(self, project: Project, mr_id: int) -> None:
        """
        Performs a series of actions to review an open merge request in a project.

        Explanation:
        - Retrieves the merge request and its changes.
        - Maps changes to file paths and fetches repository contents.
        - Constructs a prompt for review and generates a response.
        - Processes the response and logs relevant information.

        Args:
        - `project`: Project object representing the project.
        - `mr_id`: Integer representing the merge request ID.

        Returns:
        - None
        """
        mr: ProjectMergeRequest = project.mergerequests.get(id=mr_id)
        mr_changes: Dict[str, Any] | Response = mr.changes()

        file_paths_context: Dict[str, str] = self.map_changes_to_file_paths(
            project, mr_changes
        )
        repo_contents: Dict[str, str] = self.get_repository_contents(project)
        LOGGER.info("Done getting MR and Repository context")

        prompt: str = self.construct_prompt(
            mr, repo_contents, file_paths_context, mr_changes
        )
        LOGGER.info("Prompt is now ready to be processed")

        model_resp: str = self.generate_response(prompt)
        LOGGER.info("Model Response ready. Commenting on the MR")

        self.process_response(mr, model_resp, mr_changes)
