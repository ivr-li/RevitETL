import mimetypes
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import traceback
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Union
from uuid import UUID

import requests
from dotenv import load_dotenv
from lxml import etree

from bim_agent.services.config import DIRS, PROJECTS

dotenv_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path)


class BaseXMLTask(ABC):
    def __init__(self, folder_name: str, output_path: Union[str, Path]):
        self.folder_name = folder_name
        self.base_path = Path(output_path) / self.folder_name / DIRS["collisions_data"]
        self.pattern = re.compile(r"<clashresult\b[^>]*>(.*?)</clashresult>", re.DOTALL)
        self.xml_file = self.base_path / DIRS["collisions_file"]

    @abstractmethod
    def run(self) -> None:
        pass


class NWDData:
    COMPLETE_MARKER = "Завершено"
    LOG_POLL_INTERVAL = 30
    LOG_POLL_TIMEOUT = 25200  # The average export time is 7 hours

    def __init__(self, folder_name: str, output_path: Union[str, Path]):
        pt = Path(output_path) if isinstance(output_path, str) else output_path

        self.folder_name = folder_name
        self.data_path = pt / folder_name / DIRS["nwd_data"]
        self.bat_file = self.data_path / f"{folder_name}.bat"
        self.log_file = self.data_path / f"{folder_name}.log"

    def run(self) -> None:
        if self.log_file.exists():
            self.log_file.unlink()
        self._start_bat()
        self._wait_for_log()

    def _start_bat(self) -> None:
        path = str(self.data_path)
        subprocess.run(
            ["cmd", "/c", str(self.bat_file)],
            cwd=None if path.startswith("\\\\") else path,
            check=True,
        )

    def _wait_for_log(self) -> None:
        elapsed = 0
        while elapsed < self.LOG_POLL_TIMEOUT:
            if self._is_complete():
                return
            time.sleep(self.LOG_POLL_INTERVAL)
            elapsed += self.LOG_POLL_INTERVAL

        raise TimeoutError(f"{self.folder_name}: timeout {self.LOG_POLL_TIMEOUT}s")

    def _is_complete(self) -> bool:
        if not self.log_file.exists():
            return False

        content = self.log_file.read_text(encoding="utf-8", errors="ignore")

        return self.COMPLETE_MARKER in content


class CleanXMLData(BaseXMLTask):
    def __init__(self, folder_name: str, output_path: Union[str, Path]):
        super().__init__(folder_name, output_path)

    def run(self) -> None:
        """
        Cleaning and splitting into separate files
        """
        parent_path = self.base_path.parent
        backup_dir = self._create_backup()
        self._move_ex_files(parent_path, backup_dir)

        if not self.xml_file:
            print(f"XML файл не найден в {self.base_path}")
            return

        unique_names = self._extract_unique_names(self.xml_file)
        xml_text = self.xml_file.read_text(encoding="utf-8")

        for name in unique_names:
            filtered = self._filter_xml(xml_text, name)
            out_file = parent_path / f"{name}.xml"
            out_file.write_text(filtered, encoding="utf-8")
            print(f"Создан файл: {out_file}")

        self._copy_files_folders(parent_path)
        print(f"Готово: {self.folder_name}")

    def _create_backup(self) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = self.base_path / f"archive_{date_str}"
        print(self.base_path)
        backup_dir.mkdir(parents=True, exist_ok=True)
        return backup_dir

    def _move_ex_files(self, parent: Path, backup: Path) -> None:
        for item in parent.iterdir():
            if item.suffix == ".xml" or item.name.endswith("_files"):
                try:
                    shutil.move(str(item), str(backup / item.name))
                except Exception as e:
                    print(f"Ошибка перемещения {item.name}: {e}")

    def _find_xml(self) -> Optional[Path]:
        for file in self.base_path.glob("*.xml"):
            return file
        return None

    def _extract_unique_names(self, xml_file: Path) -> List[str]:
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(str(xml_file), parser)
        root = tree.getroot()

        names = set()
        for clash in root.findall(".//clashresult"):
            obj = clash.find(".//clashobject")
            if obj is not None:
                for tag in obj.findall(".//smarttag/value"):
                    if tag.text and tag.text.endswith(".rvt"):
                        name = Path(tag.text).stem
                        names.add(name)
        return list(names)

    def _filter_xml(self, xml_text: str, keyword: str) -> str:
        def keep_block(match):
            block = match.group(1)
            obj = re.search(
                r"<clashobject\b[^>]*>(.*?)</clashobject>", block, re.DOTALL
            )
            return match.group(0) if obj and keyword in obj.group(1) else ""

        return self.pattern.sub(keep_block, xml_text)

    def _copy_files_folders(self, destination: Path) -> None:
        for item in self.base_path.iterdir():
            if item.is_dir() and item.name.endswith("_files"):
                dest = destination / item.name
                try:
                    shutil.copytree(item, dest, dirs_exist_ok=True)
                except Exception as e:
                    print(f"Ошибка копирования {item.name}: {e}")


class UpdateXMLData(BaseXMLTask):
    def __init__(self, folder_name: str, output_path: Union[str, Path]):
        super().__init__(folder_name, output_path)

    def run(self) -> None:
        """
        Основной запуск обновления XML
        """
        clashresult_dict = self._build_clashresult_dict()

        if not clashresult_dict:
            print(f"Нет данных для обновления в {self.folder_name}")
            return

        self._update_xml_file(clashresult_dict)

    def _build_clashresult_dict(self) -> Dict[str, str]:
        """
        Собирает clashresult из ВСЕХ XML файлов в родительской папке
        """
        result: Dict[str, str] = {}

        xml_files = list(self.base_path.parent.glob("*.xml"))

        if not xml_files:
            print(f"В папке {self.base_path.parent} не найдено XML файлов")
            return result

        for xml_file in xml_files:
            print(f"Обрабатываем файл: {xml_file.name}")

            try:
                content = xml_file.read_text(encoding="utf-8")

                for match in self.pattern.finditer(content):
                    block = match.group(0)

                    guid_match = re.search(r'guid="([^"]+)"', block)
                    if guid_match:
                        guid = guid_match.group(1)
                        result[guid] = block

            except Exception as e:
                print(f"Ошибка чтения {xml_file}: {e}")

        print(f"Собрано {len(result)} clashresult для {self.folder_name}")
        return result

    def _update_xml_file(self, clashresult_dict: Dict[str, str]) -> None:
        """
        Обновляет целевой XML файл
        """
        target_xml = next(self.base_path.glob("*.xml"), None)

        if not target_xml:
            print(f"Целевой XML не найден в {self.base_path}")
            return

        try:
            content = target_xml.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Ошибка чтения целевого XML {target_xml}: {e}")
            return

        found_guids = set()

        def replacer(match):
            block = match.group(0)

            guid_match = re.search(r'guid="([^"]+)"', block)
            if guid_match:
                guid = guid_match.group(1)
                found_guids.add(guid)

                if guid in clashresult_dict:
                    print(f"Замена для GUID {guid}")
                    return clashresult_dict[guid]

            return block

        updated_content = self.pattern.sub(replacer, content)

        new_guids = set(clashresult_dict.keys()) - found_guids
        if new_guids:
            print("Новые GUID, отсутствующие в целевом XML:")
            for guid in new_guids:
                print(guid)

        if "</clashresult>" not in updated_content:
            print("Проблема с закрывающими тегами </clashresult>!")

        output_file = self.xml_file

        try:
            output_file.write_text(updated_content, encoding="utf-8")
            print(f"Сохранено: {output_file}")
        except Exception as e:
            print(f"Ошибка записи файла {output_file}: {e}")


class ModelCheckerData:
    def __init__(self):
        pass


class SignalUploader:
    def __init__(self, api_base_url: str = "https://api.sgnl.pro/public"):
        self.api_base_url: str = api_base_url
        self.auth_token: Optional[str] = None
        self.headers: Dict[str, str] = {}

    def get_auth_token(self) -> bool:
        api_id: Optional[str] = os.getenv("SIGNAL_API_ID")
        secret_key: Optional[str] = os.getenv("SIGNAL_SECRET_KEY")

        if not all([api_id, secret_key]):
            raise ValueError(
                "Не заданы SIGNAL_API_ID или SIGNAL_SECRET_KEY в окружении"
            )

        url: str = f"{self.api_base_url}/v1/auth/token"

        payload: Dict[str, Any] = {
            "clientId": api_id,
            "clientSecret": secret_key,
            "scopes": [
                "project:update",
                "project:read",
                "project:create",
                "project:delete",
                "project:list",
                "project:user:create",
                "project:user:read",
                "project:user:update",
                "project:user:delete",
                "project:user:list",
                "project:role:create",
                "project:role:delete",
                "project:role:list",
                "docs:folder:create",
                "docs:folder:read",
                "docs:folder:update",
                "docs:folder:delete",
                "docs:folder:list",
                "docs:item:create",
                "docs:item:read",
                "docs:item:update",
                "docs:item:delete",
                "docs:item:list",
                "docs:version:create",
                "docs:version:read",
                "docs:version:update",
                "docs:version:delete",
                "docs:version:list",
                "docs:object:create",
                "docs:object:read",
                "docs:object:update",
                "docs:object:delete",
                "docs:object:list",
                "docs:viewer:execute",
            ],
        }

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            self.auth_token = response.json().get("token")
            self.headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json",
            }

            return self.auth_token is not None
        except requests.RequestException:
            return False

    @staticmethod
    def extract_ids(url: str) -> Tuple[str, str]:
        regex: str = r"projects/([a-f0-9\-]+).*folders/([a-f0-9\-]+)"
        match = re.search(regex, url)

        if match:
            project_id: str = match.group(1)
            folder_id: str = match.group(2)

            return project_id, folder_id

        raise ValueError("Не удалось извлечь ProjectId и FolderId")

    @staticmethod
    def get_mime_type(file_path: str) -> str:
        mime_type, _ = mimetypes.guess_type(file_path)
        return mime_type or "application/octet-stream"

    def get_signed_url(
        self, folder_id: str, mime_type: str, size: int, project_id: str
    ) -> Tuple[str, str]:
        url: str = f"{self.api_base_url}/v1/objects"
        body: Dict[str, Any] = {
            "mimeType": mime_type,
            "size": size,
            "projectId": project_id,
        }

        response = requests.put(url, headers=self.headers, json=body)
        response.raise_for_status()
        data: Dict[str, Any] = response.json()

        return data["signedUrl"], data["objectId"]

    @staticmethod
    def upload_file_to_s3(file_path: str, signed_url: str, mime_type: str) -> bool:
        with open(file_path, "rb") as f:
            response = requests.put(
                signed_url, data=f, headers={"Content-Type": mime_type}
            )
            response.raise_for_status()
            return True

    def confirm_upload(self, object_id: str) -> bool:
        url: str = f"{self.api_base_url}/v1/objects/{object_id}/uploading/commit"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return True

    def uploadToDocs(self, from_path: str, to_url: str) -> None:
        project_id, folder_id = self.extract_ids(to_url)
        name: str = os.path.basename(from_path)
        file_size: int = os.path.getsize(from_path)
        mime_type: str = self.get_mime_type(from_path)

        signed_url, object_id = self.get_signed_url(
            folder_id, mime_type, file_size, project_id
        )

        if not self.upload_file_to_s3(from_path, signed_url, mime_type):
            raise RuntimeError("Ошибка загрузки файла в S3")

        if not self.confirm_upload(object_id):
            raise RuntimeError("Ошибка подтверждения загрузки")

        version_response = requests.post(
            f"{self.api_base_url}/v1/versions",
            headers=self.headers,
            json={"name": name, "objectId": object_id, "projectId": project_id},
        )
        version_response.raise_for_status()
        version_id: str = version_response.json()["data"]

        folder_items_response = requests.get(
            f"{self.api_base_url}/v1/items?folderId={folder_id}&deleted=false",
            headers=self.headers,
        )
        folder_items_response.raise_for_status()
        items: List[Dict[str, Any]] = folder_items_response.json()

        target_item: Optional[Dict[str, Any]] = next(
            (item for item in items if item.get("name") == name), None
        )
        target_item_id: Optional[str] = target_item.get("id") if target_item else None

        if not target_item_id:
            create_item_response = requests.put(
                f"{self.api_base_url}/v1/items/file",
                headers=self.headers,
                json={"folderId": folder_id, "name": name, "versionId": version_id},
            )
            create_item_response.raise_for_status()
            target_item_id = create_item_response.json()["data"]
        else:
            item_version_response = requests.put(
                f"{self.api_base_url}/v1/items/versions",
                headers=self.headers,
                json={"itemId": target_item_id, "versionId": version_id},
            )
            item_version_response.raise_for_status()

        forge_convert = requests.post(
            f"{self.api_base_url}/v1/forge/convert",
            headers=self.headers,
            json={"versionId": version_id, "projectId": project_id},
        )
        forge_convert.raise_for_status()

    def upload_single_file(self, file_info: Tuple[str, str, Optional[str]]) -> None:
        file_path, to_url, _ = file_info
        self.uploadToDocs(file_path, to_url)

    @classmethod
    def upload_files_parallel(
        cls,
        file_list: Iterable[Tuple[str, str, Optional[str]]],
        max_workers: int = 9,
    ) -> None:
        uploader = cls()
        if not uploader.get_auth_token():
            raise RuntimeError("Не удалось получить токен авторизации")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(
                    uploader.upload_single_file,
                    (file_path, to_url, uploader.auth_token),
                ): file_path
                for file_path, to_url, _ in file_list
            }

            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    future.result()
                except Exception as exc:
                    print(f"Файл {file_path} вызвал исключение: {exc}", file=sys.stderr)

    @classmethod
    def from_signal_paths(
        cls, signal_paths_file: str, nwd_patch: str
    ) -> Tuple["SignalUploader", List[Tuple[str, str]]]:
        with open(signal_paths_file, encoding="utf-8") as file:
            signal_paths: str = file.read()

        files_to_upload: List[Tuple[str, str]] = []

        for data in signal_paths.split("\n"):
            if " - " in data:
                project, singal_path = data.split(" - ", 1)
                folder_nwd = pathlib.Path(nwd_patch) / project
                if folder_nwd.exists():
                    for file in os.listdir(folder_nwd):
                        if file.endswith(".nwd") and "Сборка" in file:
                            file_path = str(folder_nwd / file)
                            files_to_upload.append((file_path, singal_path.strip()))

        return cls(), files_to_upload


class Runner:
    def __init__(self, uploader: SignalUploader):
        self.uploader = uploader

    def run_nwd_export(self, folders: list[str], output_path: Union[str, Path]):
        tasks = [NWDData(folder, output_path) for folder in folders]
        successful, failed = self._run_export_tasks(tasks)
        print(
            "\nNWD_export finished:", f"successful - {successful}", f"failed - {failed}"
        )
        # self._upload_to_signal(successful, output_path)
        print("выгрузка в сингла прошла")
        return successful, failed

    def xml_export(
        self,
        folders: list[str],
        output_path: Union[str, Path],
        nwd_success: Optional[list[str]],
    ) -> None:
        if nwd_success:
            folders = [f for f in folders if f in nwd_success]

        # Update
        update_tasks: list[BaseXMLTask] = [
            UpdateXMLData(folder, output_path) for folder in folders
        ]

        update_success, update_failed = self._run_export_tasks(update_tasks)

        print(
            "\nUpdate stage finished:",
            f"successful - {update_success}",
            f"failed - {update_failed}",
        )

        # Clean
        clean_folders = update_success

        clean_tasks: list[BaseXMLTask] = [
            CleanXMLData(folder, output_path) for folder in clean_folders
        ]

        clean_success, clean_failed = self._run_export_tasks(clean_tasks)

        print(
            "\nClean stage finished:",
            f"successful - {clean_success}",
            f"failed - {clean_failed}",
        )

    def run_full_pipeline(
        self, folders: list[str], output_path: Union[str, Path]
    ) -> None:
        """
        Runs all tasks sequentially for each folder
        """
        successful, failed = self.run_nwd_export(folders, output_path)
        self.xml_export(folders, output_path, successful)
        print("\n=== Пайплайн завершён ===")

    def _run_export_tasks(
        self, tasks: Union[Sequence[BaseXMLTask], list[NWDData]]
    ) -> tuple[list[str], list[tuple[str, str]]]:
        successful: list[str] = []
        failed: list[tuple[str, str]] = []

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {pool.submit(t.run): t for t in tasks}
            for future in as_completed(futures):
                task = futures[future]
                try:
                    future.result()
                    successful.append(task.folder_name)
                except Exception as ex:
                    failed.append((task.folder_name, str(ex)))
                    print(f"✗ Ошибка в {task.folder_name}:\n{traceback.format_exc()}")

        return successful, failed

    def _upload_to_signal(
        self, folders: list[str], output_path: Union[str, Path]
    ) -> None:
        file_list: list[tuple[str, str, None]] = []

        for folder in folders:
            file_list.extend(self._collect_upload_files(folder, output_path))
        self.uploader.upload_files_parallel(file_list)

    def _collect_upload_files(
        self, folder: str, output_path: Union[str, Path]
    ) -> list[tuple[str, str, None]]:
        project_conf = PROJECTS.get(folder, {})
        signal_conf = project_conf.get("signal", {})
        to_url = signal_conf.get("signal_url", "")

        if not to_url:
            raise ValueError(f"{folder}: signal_url not set in conf.yml")

        project_id, folder_id = SignalUploader.extract_ids(to_url)
        self._validate_uuid(project_id, "project_id")
        self._validate_uuid(folder_id, "folder_id")

        nwd_dir = Path(output_path) / folder / DIRS["nwd"]
        signal_filter = signal_conf.get("filter", "")

        return [
            (str(f), to_url, None)
            for f in nwd_dir.glob("*.nwd")
            if signal_filter in f.name
        ]

    @staticmethod
    def _validate_uuid(value: str, name: str) -> None:
        if not value:
            raise ValueError(f"{name} не задан в conf.yml")

        try:
            UUID(value, version=4)
        except ValueError:
            raise ValueError(f"Неверный {name}: {value}")


Runner(SignalUploader()).xml_export(
    # folders=["testp", "testp2", "testp3"],
    folders=["KGN_GP5.2"],
    output_path=r"\\fs\bim\Projects\00.BIM_Export\Tests_zone",
    nwd_success=None,
)
