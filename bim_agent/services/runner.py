import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Union

from bim_agent.services.config import DIRS


class Runner:
    def run_nwd_export(self, foldefs: list[str], output_path: Union[str, Path]) -> None:
        tasks = [NWDData(folder, output_path) for folder in foldefs]

        with ThreadPoolExecutor(max_workers=3) as pool_ex:
            futures = {pool_ex.submit(task.bat_activate): task for task in tasks}

            for future in as_completed(futures):
                task = futures[future]

                try:
                    future.result()
                except subprocess.CalledProcessError as ex:
                    print(f"{task.baf_file.name} — ошибка: {ex.returncode}")

    def stlit_coll_xml(self):
        pass

    def create_mc_data(self):
        pass


class NWDData:
    def __init__(self, folder_name: str, output_path: Union[str, Path]) -> None:
        if isinstance(output_path, str):
            pt = Path(output_path)
        else:
            pt = output_path

        self.data_patch = pt / folder_name / DIRS["nwd_data"]
        self.baf_file = self.data_patch / f"{folder_name}.bat"
        self.config = self.data_patch / f"{folder_name}.txt"

    def bat_activate(self):
        subprocess.run(["cmd", "/c", self.baf_file], cwd=self.data_patch, check=True)


class CollisionsData:
    def __init__(self) -> None:
        pass


class ModelCheckerData:
    def __init__(self) -> None:
        pass


Runner().run_nwd_export(
    foldefs=["KGN_GP06"],
    output_path=r"\\fs\bim\Projects\00.BIM_Export\Tests_zone",
)
