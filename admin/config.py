from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH: Path = Path(__file__).resolve().parent.parent / "config" / "conf.yml"

DEFAULT_CONFIG: dict[str, Any] = {
    "defaults": {
        "navisworks_exe": r"C:\Program Files\Autodesk\Navisworks Manage 2022\FileToolsTaskRunner.exe",
        "signal_max_workers": 9,
        "bim_agent_url": "http://host.docker.internal:8000",
        "export_files": [
            "01.Сборка_Общая.rvt",
            "02.Сборка_Архитектура.rvt",
            "03.1 Сборка_Конструктив.rvt",
            "03.3 Сборка_Конструктив и Инженерные сети.rvt",
            "04.1 Сборка_Коробка здания.rvt",
            "04.2 Сборка_Коробка здания и Инженерные сети.rvt",
            "05.Сборка_Отопление и Вентиляция.rvt",
            "06.Сборка_Водоснабжение и Водоотведение.rvt",
            "07.Сборка_Общая Инженерные сети.rvt",
            "99_AS.rvt",
            "99_SC.rvt",
        ],
        "xml_template": "Проверка_файлов.xml",
    },
    "projects": {},
}


class ConfigManager:
    def __init__(self, path: Path = CONFIG_PATH) -> None:
        self.path: Path = path
        self.config: dict[str, Any] = self._load()

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

    def save_project(self, key: str, data: dict[str, Any]) -> None:
        self.projects[key] = data
        self.save()

    def delete_project(self, key: str) -> None:
        del self.projects[key]
        self.save()

    def _load(self) -> dict[str, Any]:
        try:
            if not self.path.exists():
                return DEFAULT_CONFIG.copy()

            with open(self.path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

            return self._merge_defaults(data)

        except Exception as e:
            print(f"Config load error: {e}")
            return DEFAULT_CONFIG.copy()

    def _merge_defaults(self, data: dict[str, Any]) -> dict[str, Any]:
        merged = DEFAULT_CONFIG.copy()

        for key, value in data.items():
            if isinstance(value, dict) and key in merged:
                merged[key].update(value)
            else:
                merged[key] = value

        return merged

    def _resolve_default_files(self) -> None:
        for project in self.projects.values():
            if project.get("export", {}).get("files") == "USE_DEFAULTS":
                project["export"]["files"] = self.default_files
