from pathlib import Path
from typing import Any

import yaml

CONF_YML_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "conf.yml"


def load() -> dict[str, Any]:
    with open(CONF_YML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


CONF_YML = load()
PROJECTS = CONF_YML.get("projects", [])
DATA_NAME = "00_Data"
