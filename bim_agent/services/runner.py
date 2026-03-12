import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Union

from bim_agent.services.config import DIRS

COMPLETE_MARKER = "Завершено"
LOG_POLL_INTERVAL = 30
LOG_POLL_TIMEOUT = 25200  # The average export time is 7 hours


class Runner:
    def run_nwd_export(self, foldefs: list[str], output_path: Union[str, Path]) -> None:
        tasks = [NWDData(folder, output_path) for folder in foldefs]

        with ThreadPoolExecutor(max_workers=3) as pool_ex:
            futures = {pool_ex.submit(task.run): task for task in tasks}

            for future in as_completed(futures):
                task = futures[future]

                try:
                    future.result()
                    print(f"{task.folder_name} — завершён")
                except Exception as ex:
                    print(f"{task.folder_name} — ошибка: {ex}")

    def stlit_coll_xml(self):
        pass

    def create_mc_data(self):
        pass


class NWDData:
    def __init__(self, folder_name: str, output_path: Union[str, Path]) -> None:
        pt = Path(output_path) if isinstance(output_path, str) else output_path

        self.folder_name = folder_name
        self.data_path = pt / folder_name / DIRS["nwd_data"]
        self.bat_file = self.data_path / f"{folder_name}.bat"
        self.log_file = self.data_path / f"{folder_name}.log"

    def run(self) -> None:
        self._start_bat()
        self._wait_for_log()

    def _start_bat(self) -> None:
        subprocess.run(
            ["cmd", "/c", str(self.bat_file)],
            cwd=str(self.data_path),
            check=True,
        )

    def _wait_for_log(self) -> None:
        elapsed = 0
        while elapsed < LOG_POLL_TIMEOUT:
            if self._is_complete():
                return
            time.sleep(LOG_POLL_INTERVAL)
            elapsed += LOG_POLL_INTERVAL

        raise TimeoutError(f"{self.folder_name}: timeout {LOG_POLL_TIMEOUT}s")

    def _is_complete(self) -> bool:
        if not self.log_file.exists():
            return False
        content = self.log_file.read_text(encoding="utf-8", errors="ignore")
        return COMPLETE_MARKER in content


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
