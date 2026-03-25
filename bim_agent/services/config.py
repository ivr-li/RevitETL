from pathlib import Path
from typing import Any

import yaml

CONF_YML_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "conf.yml"


def load() -> dict[str, Any]:
    with open(CONF_YML_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return data


CONF_YML = load()
DEFAULTS = CONF_YML.get("defaults", {})
PROJECTS = CONF_YML.get("projects", {})

DATA_NAME = "00_Data"
NAVISWORKS_EXE = DEFAULTS.get("navisworks_exe", "")

DIRS = {
    "nwd": Path("01_NWD"),
    "nwd_data": Path("01_NWD") / DATA_NAME,
    "collisions": Path("02_Collisions"),
    "collisions_data": Path("02_Collisions") / DATA_NAME,
    "collisions_file": "Проверка на пересечения.xml",
    "model_checker": Path("03_ModelChecker"),
    "model_checker_data": Path("03_ModelChecker") / DATA_NAME,
    "model_checker_temp": Path("00_Templates") / "model_checker",
}
