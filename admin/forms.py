import streamlit as st

FORM_FIELDS = [
    "name",
    "folder",
    "source",
    "output",
    "files",
    "pid",
    "fid",
    "filter",
    "dpath",
]


class ProjectForm:
    """Renders and collects project form fields."""

    def __init__(self, prefix, project=None):
        self.prefix = prefix
        self.project = project or {}

    def render(self):
        self._render_general()
        self._render_export()
        self._render_signal()
        self._render_checker()
        return self._collect()

    def _render_general(self):
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

    def _render_export(self):
        st.subheader("Экспорт")
        export = self.project.get("export", {})

        st.text_input(
            "Путь к RVT (source_path)",
            value=export.get(
                "source_path", r"C:\Users\dved\Desktop\RVT_ETL_tests\KGN_GP5.2\02_NWD"
            ),
            key=f"{self.prefix}_source",
        )

        st.text_input(
            "Путь для NWD (output_path)",
            value=export.get(
                "output_path",
                r"C:\Users\dved\Desktop\RVT_ETL_tests\KGN_GP5.2\KGN_GP5.2_nwd",
            ),
            key=f"{self.prefix}_output",
        )

        st.checkbox(
            "Стандартный набор файлов",
            value=True,
            key=f"{self.prefix}_defaults",
        )

        if not st.session_state[f"{self.prefix}_defaults"]:
            st.text_area(
                "Файлы (по одному на строку)",
                height=120,
                value="\n".join(export.get("files", [])),
                key=f"{self.prefix}_files",
            )

    def _render_signal(self):
        st.subheader("SIGNAL")
        signal = self.project.get("signal", {})
        col1, col2 = st.columns(2)

        with col1:
            st.text_input(
                "Project ID",
                value=signal.get("project_id", "Ввредите код project из ссылки"),
                key=f"{self.prefix}_pid",
            )

        with col2:
            st.text_input(
                "Folder ID",
                value=signal.get("folder_id", "Ввредите код folder из ссылки"),
                key=f"{self.prefix}_fid",
            )

        st.text_input(
            "Фильтр", value=signal.get("filter", "Сборка"), key=f"{self.prefix}_filter"
        )

    def _render_checker(self):
        st.subheader("Checker")
        checker = self.project.get("checker", {})

        st.text_input(
            "Путь к данным (data_path)",
            value=checker.get("data_path", ""),
            key=f"{self.prefix}_dpath",
        )

    def _collect(self):
        s = st.session_state
        p = self.prefix
        use_defaults = s[f"{p}_defaults"]

        if use_defaults:
            files = "USE_DEFAULTS"
        else:
            raw = s.get(f"{p}_files", "")
            files = [f.strip() for f in raw.strip().split("\n") if f.strip()]

        return {
            "name": s[f"{p}_name"],
            "folder_name": s[f"{p}_folder"],
            "export": {
                "source_path": s[f"{p}_source"],
                "output_path": s[f"{p}_output"],
                "files": files,
            },
            "signal": {
                "project_id": s[f"{p}_pid"],
                "folder_id": s[f"{p}_fid"],
                "filter": s[f"{p}_filter"],
            },
            "checker": {
                "data_path": s[f"{p}_dpath"],
            },
        }
