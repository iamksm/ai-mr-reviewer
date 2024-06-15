import logging
import os
from pathlib import Path
from typing import Any, Dict

import yaml

logging.basicConfig(
    level=logging.INFO,
    format="[AI Reviewer] %(levelname)s %(asctime)s %(name)s:%(lineno)s %(message)s",
)


def load_config() -> Dict:
    config_file = os.environ.get("CONFIG_FILE_PATH", "config-example.yml")
    path = Path(config_file)

    if not path.exists():
        raise FileNotFoundError(f"Config file {config_file} does not exist")

    return yaml.safe_load(stream=path.read_text())


site_settings: Dict[Any, Any] = load_config()

GITLAB_TOKEN: str = site_settings["GITLAB_TOKEN"]
REPO_INSTALL_PATH: str = site_settings.get("REPO_INSTALL_PATH", "/tmp/repos")
GITLAB_URL: str = site_settings["GITLAB_URL"]
GITLAB_HEADER_TOKEN: str = site_settings.get("GITLAB_HEADER_TOKEN", "")

# For options details see the below link
# https://github.com/ollama/ollama/blob/main/docs/modelfile.md#valid-parameters-and-values  # noqa
ollama_default_options = {
    "top_k": 25,  # Increase to reduce hallucinations
    "mirostat_tau": 5.0,  # Decrease for more coherence
    "temperature": 0.5,  # Decrease for less creativity
    "top_p": 0.5,  # Decrease for more focus
}
OLLAMA_OPTIONS: Dict = site_settings.get("OLLAMA_OPTIONS", ollama_default_options)
OLLAMA_MODEL: str = str(site_settings.get("OLLAMA_MODEL", "llama3:8b"))
