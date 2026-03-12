import streamlit as st
from forms import FORM_FIELDS, ProjectForm

from config import ConfigManager


class AdminApp:
    def __init__(self) -> None:
        self.manager: ConfigManager = ConfigManager()

    def run(self) -> None:
        st.set_page_config(page_title="RevitETL — Управление проектами", layout="wide")
        st.title("RevitETL — Управление проектами")

        self._render_global_settings()

        tab_list, tab_add = st.tabs(["Проекты", "Добавить проект"])

        with tab_list:
            self._render_projects()

        with tab_add:
            self._render_add_form()

    def _render_global_settings(self) -> None:
        with st.sidebar:
            st.header("Глобальные настройки")
            output_path = st.text_input(
                "Путь к хранилищу (output_path)",
                value=self.manager.default_output_path,
                key="global_output_path",
            )
            export_files = st.text_area(
                "Файлы экспорта (по одному на строку)",
                value="\n".join(self.manager.default_files),
                height=200,
                key="global_export_files",
            )
            xml_template = st.text_input(
                "XML шаблон",
                value=self.manager.default_xml_template,
                key="global_xml_template",
            )
            if st.button("Сохранить настройки"):
                files = [f.strip() for f in export_files.strip().split("\n") if f.strip()]
                self.manager.save_defaults({
                    "output_path": output_path,
                    "export_files": files,
                    "xml_template": xml_template,
                })
                st.success("Настройки сохранены")
                st.rerun()

    def _render_projects(self) -> None:
        if not self.manager.projects:
            st.info("Нет проектов. Добавьте первый во вкладке «Добавить проект».")
            return

        for key, data in self.manager.projects.items():
            with st.expander(f"{key} — {data.get('name', '')}", expanded=False):
                form = ProjectForm(key, data, self.manager.default_output_path)
                updated = form.render()
                self._render_action_buttons(key, updated)

    def _render_action_buttons(self, key: str, updated: dict) -> None:
        col_save, col_del, _ = st.columns([1, 1, 4])

        with col_save:
            if st.button("Сохранить", key=f"save_{key}"):
                self.manager.save_project(key, updated)
                st.success("Сохранено")
                st.rerun()

        with col_del:
            if st.button("Удалить", key=f"del_{key}", type="secondary"):
                self.manager.delete_project(key)
                st.success(f"Проект {key} удалён")
                st.rerun()

    def _render_add_form(self) -> None:
        new_key = st.text_input("ID проекта (ключ в YAML, например KGN_GP06)")
        if not new_key:
            return

        form = ProjectForm("new", output_path=self.manager.default_output_path)
        new_project = form.render()

        if st.button("Добавить проект"):
            if new_key in self.manager.projects:
                st.error(f"Проект {new_key} уже существует")
                return

            self.manager.save_project(new_key, new_project)
            self._clear_new_form()

            st.success(f"Проект {new_key} добавлен")
            st.rerun()

    @staticmethod
    def _clear_new_form() -> None:
        for field in FORM_FIELDS:
            key = f"new_{field}"

            if key in st.session_state:
                del st.session_state[key]


app = AdminApp()
app.run()
