from pathlib import Path

from bim_agent.services.config import DIRS, NAVISWORKS_EXE, PROJECTS

BAT_TEMPLATE = (
    'pushd "{nwd_dir}" && del /q *.nwd 2>nul & popd\n'
    'pushd "{nwc_dir}" && del /q *.nwc 2>nul & popd\n'
    "\n"
    'start "{name} Экспорт NWD"^\n'
    ' "{navisworks_exe}"^\n'
    ' /i "{txt_conf}"^\n'
    ' /od "{nwd_dir}"^\n'
    ' /log "{log_file}"\n'
)


def create_project_dirs():
    for id, project in PROJECTS.items():
        output_path = project.get("output_path", "")

        if not output_path:
            continue

        folder_name = project.get("folder_name", "")
        root = Path(output_path) / folder_name

        if Path(root).is_dir():
            continue

        for d in DIRS.values():
            (root / d).mkdir(parents=True, exist_ok=True)

        export = project.get("export", "")
        source_path = export.get("source_path", "")
        files = export.get("files", "")

        nwd_data = root / DIRS["nwd_data"]
        txt_conf = nwd_data / f"{id}.txt"
        with open(txt_conf, "w", encoding="utf-8") as f:
            for item in files:
                f.write(rf"{source_path}\{item}" + "\n")

        nwd_out = root / DIRS["nwd"]
        nwc_dir = Path(source_path)
        log_file = nwd_data / f"{id}.log"

        bat_content = BAT_TEMPLATE.format(
            nwd_dir=nwd_out,
            nwc_dir=nwc_dir,
            name=project.get("name", id),
            navisworks_exe=NAVISWORKS_EXE,
            txt_conf=txt_conf,
            log_file=log_file,
        )

        bat_path = root / DIRS["nwd_data"] / f"{id}.bat"
        Path(bat_path).write_text(bat_content, encoding="cp866")


create_project_dirs()
