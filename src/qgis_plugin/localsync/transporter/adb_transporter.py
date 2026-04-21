import logging
import pathlib

from .transporter import Transporter
from ..channels.adb_channel import AdbChannel
from ..channels.host_channel import HostChannel
from ...constants import QGIS_PLUGIN_NAME
from ..data_actions.file_scanner import FileScanner
from ...i18n import tr
from pathlib import Path

from ...logger.qgis_logger_handler import QgisLoggerHandler


class AdbTransporter(Transporter):

    """
        Class in charge of transport files from pc to device and vice versa, using the ADB connection type.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: QgisLoggerHandler
        :ivar root_names: list of possible names for the root.
        :vartype root_names: list[str]
        :ivar cancel_load_process: bool for canceling the upload/download process.
        :vartype cancel_load_process: bool
    """


    def __init__(self):
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.root_names = ["/sdcard/", "/storage/self/primary/", "/storage/emulated/0/"]
        self.cancel_load_process = False


    def cancel_file_load(self):
        """
            Set cancel_load_process to True. It will cancel the loading process before the next file.
        """
        self.cancel_load_process = True


    def check_if_directory_exists(self, directory: str, pc_path: bool, storages: list[str] = None) -> bool:
        """
            Check if a directory exists in the pc or check if the directory have a compatible root for device.
            :param directory: directory to check.
            :param pc_path: indicates if the directory is a pc path or a device path.
            :param storages: list of storages to check if the directory path have a valid root directory.
            :return: True if the directory exists, false otherwise.
        """

        if storages is None:
            storages = []
        if pc_path:
            return HostChannel.check_file_exists(directory)
        else:
            return self._search_usual_names_and_storages(directory, storages)


    def _search_usual_names_and_storages(self, directory: str, storages: list[str]) -> bool:

        """
            Check if the directory given have a subpath that matches one of the root_names or storages given
            :param directory: directory to check.
            :param storages: list of storages to check if the directory path have a valid root directory.
            :return: True if a directory is found, False otherwise.
        """

        try:
            found = False
            for name in self.root_names:
                if name in directory:
                    found = True
                    break
            if not found:
                for storage in storages:
                    if storage in directory:
                        found = True
                        break
            return found
        except Exception as e:
            self.logger.error("Error when checking if directory exists: {error}".format(error = str(e)))
            return False


    def pull(self, file_list: list[Path], source: str, destination: str):

        """
            Download files from a pre-selected device into the pc.
            :param file_list: list of path to files that will be downloaded.
            :param source: path where the files are located. (Device)
            :param destination: path where the files will be copied. (PC)
        """
        HostChannel.create_directory_in_host(destination)
        if file_list:
            for file in file_list:
                self._pull_main_process(source, file, destination)
                if self.cancel_load_process:
                    break
        else:
            self.logger.info("The destination path provided: {source} have no files or the filters are too restrictive.".format(source=source))

        self.cancel_load_process = False



    def _pull_main_process(self, source: str, file_path: Path, destination: str):
        """
            Main process for download files from a pre-selected device into the pc.
            :param source: path where the files are located.
            :param file_path: path of the current file to be downloaded.
            :param destination: path where the files will be copied.
        """
        if len(source) <= len(file_path.parent.as_posix().rstrip('/')):
            output_sub = file_path.parent.as_posix().replace(source, "")
        else:
            output_sub = ""
        destination_pathlib = pathlib.Path(destination.rstrip("/"))
        destination_pathlib = destination_pathlib / output_sub.lstrip("/")
        folder_to_create = destination_pathlib.as_posix()
        if output_sub:
            HostChannel.create_directory_in_host(folder_to_create)
        AdbChannel.pull_file(file_path.as_posix(), destination_pathlib.as_posix())


    def push(self, file_list: list[Path], source: str, destination: str):
        """
            Upload files to a pre-selected device from the pc.
            :param file_list: list of path to files that will be uploaded.
            :param source: path where the files are located. (PC)
            :param destination: path where the files will be copied. (Device)
        """
        if file_list:
            self.create_base_output_directory_in_device(destination)
            for file_path in file_list:
                output_sub = AdbChannel.check_create_directory_device(file_path.parent.as_posix(), source, destination)
                destination_pathlib = pathlib.Path(destination.rstrip("/"))
                destination_pathlib = destination_pathlib / output_sub.lstrip("/")
                AdbChannel.push_file(file_path.as_posix(), destination_pathlib.as_posix())
                if self.cancel_load_process:
                    break
            AdbChannel.update_cartodruid_device_db()
        else:
            self.logger.info("The source path provided: {destination} have no files or the filters are too restrictive.".format(destination=destination))
        self.cancel_load_process = False


    def create_base_output_directory_in_device(self, output_path: str):
        """
        Create the directory and any intermediate directory in output_path for the device using ADB.
        :param output_path: Path with the directories that need to be created.
        :return: True if the final directory was created o was already created, False otherwise.
        """
        pathlib_path = Path(output_path)
        if not AdbChannel.check_directory_exists(pathlib_path.as_posix()):
            removed_directories = []
            create_directory_on = pathlib_path.as_posix()
            final_directory_created = False
            while not final_directory_created:
                if AdbChannel.create_directory_in_device(create_directory_on):
                    if not removed_directories:
                        final_directory_created = True
                    else:
                        create_directory_on = removed_directories.pop().as_posix()
                else:
                    pathlib_parent = pathlib_path.parent
                    if pathlib_parent != Path("/"):
                        removed_directories.append(pathlib_path)
                        create_directory_on = pathlib_parent.as_posix()
                        pathlib_path = pathlib_parent
                    else:
                        return False
            return final_directory_created
        return True


    def get_file_list(self, input_path:str, includes_filters:list[str], excludes_filters:list[str],
                      check_directories:bool = False) -> list:
        """
        Get the list of files from the device.
        :param input_path: path to the folder where the files will be searched.
        :param includes_filters: list of string filters glob style. Those paths that fulfill one of the patterns will be transported
        :param excludes_filters: list of string filters glob style. Those paths that fulfill one of the patterns will not be transported.
        :param check_directories: boolean to check only files (False) or directories (True).
        :return: a list containing Path of the files found.
        """
        file_list = []
        if AdbChannel.check_directory_exists(input_path) or AdbChannel.check_file_exists(input_path):
            input_path = input_path.rstrip("/")
            if check_directories:
                file_list = AdbChannel.get_directories_list(input_path)
            else:
                file_list = AdbChannel.get_file_list(input_path)
            print(file_list)
            file_list = FileScanner.filter_files_list(file_list, includes_filters, True)
            file_list = FileScanner.filter_files_list(file_list, excludes_filters, False)
            print(file_list)
        return file_list





