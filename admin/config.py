from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH: Path = Path(__file__).resolve().parent.parent / "config" / "conf.yml"


class ConfigManager:

    def __init__(self, path: Path = CONFIG_PATH) -> None:
        self.path: Path = path
        self.config: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        with open(self.path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def projects(self) -> dict[str, dict[str, Any]]:
        return self.config.setdefault("projects", {})

    @property
    def default_files(self) -> list[str]:
        return self.config.get("defaults", {}).get("export_files", [])

    def save(self) -> None:
        self._resolve_default_files()

        with open(self.path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.config,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

    def _resolve_default_files(self) -> None:
        for project in self.projects.values():
            if project.get("export", {}).get("files") == "USE_DEFAULTS":
                project["export"]["files"] = self.default_files

    def save_project(self, key: str, data: dict[str, Any]) -> None:
        self.projects[key] = data
        self.save()

    def delete_project(self, key: str) -> None:
        del self.projects[key]
        self.save()
