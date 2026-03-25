from typing import Any

import streamlit as st

FORM_FIELDS: list[str] = [
    "name",
    "folder",
    "source",
    "files",
    "signal_url",
    "filter",
]


class ProjectForm:
    """Renders and collects project form fields."""

    def __init__(
        self, prefix: str, project: dict[str, Any] | None = None, output_path: str = ""
    ) -> None:
        self.prefix: str = prefix
        self.project: dict[str, Any] = project or {}
        self.output_path: str = output_path

    def render(self) -> dict[str, Any]:
        self._render_general()
        self._render_export()
        self._render_signal()
        return self._collect()

    def _render_general(self) -> None:
        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "Название проекта",
                value=self.project.get("name", "Курган ГП5.2"),
                key=f"{self.prefix}_name",
            )

        with col2:
            st.text_input(
                "Имя папки (folder_name)",
                value=self.project.get("folder_name", "KGN_GP5.2"),
                key=f"{self.prefix}_folder",
            )

    def _render_export(self) -> None:
        st.subheader("Экспорт RTV в NWD")
        export = self.project.get("export", {})

        st.text_input(
            "Путь к RVT",
            value=export.get(
                "source_path", r"C:\Users\dved\Desktop\RVT_ETL_tests\KGN_GP5.2\02_NWD"
            ),
            key=f"{self.prefix}_source",
        )

        st.checkbox(
            "Стандартный набор файлов",
            value=True,
            key=f"{self.prefix}_defaults",
        )

        if not st.session_state[f"{self.prefix}_defaults"]:
            files_value = "\n".join(export.get("files", []))
            line_count = max(files_value.count("\n") + 1, 3)
            st.text_area(
                "Файлы (по одному на строку)",
                height=line_count * 25 + 20,
                value=files_value,
                key=f"{self.prefix}_files",
            )

    def _render_signal(self) -> None:
        st.subheader("Отправка NWD в SignalDocs")
        signal = self.project.get("signal", {})

        st.text_input(
            "Ссылка на папку SIGNAL",
            value=signal.get("signal_url", ""),
            key=f"{self.prefix}_signal_url",
            placeholder="https://docs.sgnl.pro/projects/.../folders/...",
        )

        st.text_input(
            "Фильтр", value=signal.get("filter", "Сборка"), key=f"{self.prefix}_filter"
        )

    def _collect(self) -> dict[str, Any]:
        session = st.session_state
        pref = self.prefix
        use_defaults = session[f"{pref}_defaults"]

        if use_defaults:
            files = "USE_DEFAULTS"
        else:
            raw = session.get(f"{pref}_files", "")
            files = [f.strip() for f in raw.strip().split("\n") if f.strip()]

        return {
            "name": session[f"{pref}_name"],
            "folder_name": session[f"{pref}_folder"],
            "output_path": self.output_path,
            "export": {
                "source_path": session[f"{pref}_source"],
                "files": files,
            },
            "signal": {
                "signal_url": session[f"{pref}_signal_url"],
                "filter": session[f"{pref}_filter"],
            },
        }
