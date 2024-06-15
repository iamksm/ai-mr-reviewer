import logging
import os
import time
import zipfile
from collections import defaultdict
from functools import wraps
from pathlib import Path

LOGGER: logging.Logger = logging.getLogger(__name__)


def timer(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start: float = time.perf_counter()
        func(*args, **kwargs)
        finish: float = time.perf_counter()

        function_name: str = func.__name__
        time_taken: float = round(finish - start, 2)
        msg: str = f"Finished {function_name = } in {time_taken} seconds"

        LOGGER.info(msg)

    return wrapper


def download_and_read_repo_files_from_path(
    name: str, zipped_archive: bytes, base_path="/tmp/repos"
):
    Path(base_path).mkdir(exist_ok=True)

    repos = defaultdict()
    path_to_downloaded_zipped_repo = f"{base_path}/{name}.zip"
    path_to_unzipped_repo = f"{base_path}/{name}"

    if not Path(path_to_unzipped_repo).exists():
        with open(path_to_downloaded_zipped_repo, "wb") as f:
            f.write(zipped_archive)

        with zipfile.ZipFile(path_to_downloaded_zipped_repo) as f:
            Path(path_to_unzipped_repo).mkdir(exist_ok=True)
            f.extractall(path_to_unzipped_repo)
            os.remove(path_to_downloaded_zipped_repo)

    repo_folder_path = os.path.join(
        path_to_unzipped_repo, os.listdir(path_to_unzipped_repo)[0]
    )
    for root, dirs, files in os.walk(repo_folder_path):
        # Filter out unwanted directories first
        dirs[:] = [dir for dir in dirs if not dir.startswith(".")]

        for file in files:
            if file.endswith((".ini", ".pyc")) or file.startswith("."):
                continue

            path = os.path.join(root, file)

            try:
                repos[path] = Path(path).read_text()
            except UnicodeDecodeError:
                continue

    LOGGER.info(f"Done reading the {name} repository contents")
    return repos
