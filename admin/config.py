from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "conf.yml"


class ConfigManager:
    """Reads and writes conf.yml."""

    def __init__(self, path=CONFIG_PATH):
        self.path = path
        self.config = self._load()

    def _load(self):
        with open(self.path, encoding="utf-8") as f:
            return yaml.safe_load(f)

    @property
    def projects(self):
        return self.config.setdefault("projects", {})

    @property
    def default_files(self):
        return self.config.get("defaults", {}).get("export_files", [])

    def save(self):
        self._resolve_default_files()

        with open(self.path, "w", encoding="utf-8") as f:
            yaml.dump(
                self.config,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

    def _resolve_default_files(self):
        for project in self.projects.values():
            if project.get("export", {}).get("files") == "USE_DEFAULTS":
                project["export"]["files"] = self.default_files

    def add_project(self, key, data):
        self.projects[key] = data
        self.save()

    def update_project(self, key, data):
        self.projects[key] = data
        self.save()

    def delete_project(self, key):
        del self.projects[key]
        self.save()
