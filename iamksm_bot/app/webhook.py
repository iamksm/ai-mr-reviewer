import logging
from threading import Thread
from typing import Dict

from flask import Flask, request
from gitlab.v4.objects.projects import Project

from iamksm_bot.app.ai import IAMKSM
from iamksm_bot.config.settings import settings

LOGGER: logging.Logger = logging.getLogger(__name__)
FLASK_APP = Flask(__name__)
GITLAB_TOKEN = settings.GITLAB_TOKEN
GITLAB_HEADER_TOKEN = settings.GITLAB_HEADER_TOKEN


@FLASK_APP.route("/review-mr", methods=["POST"])
def mr_review_webhook() -> tuple[str, int]:
    X_GITLAB_TOKEN = request.headers.get("X-Gitlab-Token")

    if X_GITLAB_TOKEN != GITLAB_HEADER_TOKEN:
        LOGGER.error(f"UNAUTHORIZED: {X_GITLAB_TOKEN = } is incorrect")
        return "UNAUTHORIZED", 401

    data: Dict = request.json
    project = data["project"]
    obj_attrs = data["object_attributes"]
    mr_id = obj_attrs["iid"]

    is_an_mr = data["event_type"] == "merge_request"
    is_not_draft = obj_attrs["draft"] is False
    is_not_wip = obj_attrs["work_in_progress"] is False
    no_unresolved_comments: bool = obj_attrs["blocking_discussions_resolved"] is True
    mr_action_is_valid = obj_attrs["action"] in ("update", "open")
    is_an_open_mr = obj_attrs["state"] == "opened"

    can_review: bool = all(
        (
            is_an_open_mr,
            is_not_draft,
            is_not_wip,
            no_unresolved_comments,
            is_an_mr,
            mr_action_is_valid,
        )
    )

    if not can_review:
        return log_and_forbid_review(
            data,
            obj_attrs,
            is_an_mr,
            is_not_draft,
            is_not_wip,
            no_unresolved_comments,
            mr_action_is_valid,
            is_an_open_mr,
        )

    project: Project = AIR.gl.projects.get(project["id"])
    thread = Thread(
        target=AIR.review_project_open_merge_request, args=(project, mr_id), daemon=True
    )
    thread.start()

    return "OK", 200


def log_and_forbid_review(
    data,
    obj_attrs,
    is_an_mr,
    is_not_draft,
    is_not_wip,
    no_unresolved_comments,
    mr_action_is_valid,
    is_an_open_mr,
):
    event_type = f"\n {data['event_type'] = } should be `merge_request`"
    draft_status = f"\n {obj_attrs['draft'] = } should be `False`"
    work_in_progress = f"\n {obj_attrs['work_in_progress'] = } should be `False`"
    pending_threads = (
        f"\n {obj_attrs['blocking_discussions_resolved'] = } should be `True`"
    )
    is_valid_action = f"\n {obj_attrs['action'] = } should be either open or update"
    mr_status = f" \n {obj_attrs['state'] = } should be opened"

    msg_to_state_map: Dict[bool, str] = {
        is_an_mr: event_type,
        is_not_draft: draft_status,
        is_not_wip: work_in_progress,
        no_unresolved_comments: pending_threads,
        mr_action_is_valid: is_valid_action,
        is_an_open_mr: mr_status,
    }

    final_msg = "Cannot Review due to: "

    for status, msg in msg_to_state_map.items():
        if not status:
            final_msg += msg

    LOGGER.error(final_msg)

    return "FORBIDDEN", 403


AIR = IAMKSM()
