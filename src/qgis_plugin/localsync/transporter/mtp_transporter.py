import logging
import os
import pathlib
import traceback

from qgis._core import QgsApplication
from ..channels.host_channel import HostChannel
from ...constants import QGIS_PLUGIN_NAME
from ..transporter.transporter import Transporter
from ..channels.mtp_channel import MtpChannel
from ..data_actions.file_scanner import FileScanner
from ...logger.qgis_logger_handler import QgisLoggerHandler
from ...i18n import tr
from pathlib import Path


class MtpTransporter(Transporter):

    """
        Class in charge of transport files from pc to device and vice versa, using the MTP connection type.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
        :ivar cancel_load_process: bool for canceling the upload/download process.
        :vartype cancel_load_process: bool
    """

    def __init__(self):
        """Constructor."""
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.cancel_load_process = False


    def cancel_file_load(self):
        """
            Set cancel_load_process to True. It will cancel the loading process before the next file.
        """
        self.cancel_load_process = True

    def check_if_directory_exists(self, directory:str, pc_path:bool, storages:list[str]=None):
        """
            Check if a directory exists on the pc or check if the directory have a compatible root for device.
            :param directory: directory to check.
            :param pc_path: indicates if the directory is a pc path or a device path.
            :param storages: list of storages to check if the directory path have a valid root directory.
            :return: True if the directory exists, false otherwise.
        """
        if storages is None:
            storages = []
        try:
            if pc_path:
                return HostChannel.check_file_exists(directory)
            else:
                found = False
                for storage in storages:
                    if storage in directory:
                        found = True
                return found
        except Exception:
            self.logger.error(traceback.format_exc())
            return False



    def get_subfolder(self, source:str, file_path: Path) -> str:
        """
            Remove the base path source from directory_path, and returns the result.
            :param source: string path used as base.
            :param file_path: string path that have source + subfolders as value.
            :return: string path with the subfolders part of directory_path.
        """
        source = Path(source).as_posix().rstrip('/')
        if len(source) <= len(file_path.parent.as_posix().rstrip('/')):
            return file_path.parent.as_posix().replace(source, '')
        else:
            return ""

    def push(self, file_list: list[Path], source: str, destination: str):
        """
         Upload files to a pre-selected device from the pc.
        :param file_list: dictionary with paths to files and file names.
        :param source: string path used as source base. It is a PC path.
        :param destination: string path used as destination base. It is a device path.
        """

        if file_list:
            destination = destination.rstrip("/")
            MtpChannel.create_path_folder(destination)
            folders_created = []
            for file_path in file_list:
                outputsub = self.get_subfolder(source, file_path)
                destination_pathlib = Path(destination)
                destination_pathlib = destination_pathlib / outputsub.lstrip("/")
                final_destination = destination_pathlib.as_posix().rstrip("/")
                if outputsub and final_destination not in folders_created:
                    folders_created.append(final_destination)
                    MtpChannel.create_path_folder(final_destination)
                temporal_dir = os.path.join(
                    QgsApplication.qgisSettingsDirPath(),
                    QGIS_PLUGIN_NAME,
                    "tmp"
                )
                MtpChannel.push_file(file_path, final_destination, temporal_dir)
                if self.cancel_load_process:
                    break
        else:
            self.logger.info("The source path provided: {destination} have no files or the filters are too restrictive.".format(destination=destination))

        self.cancel_load_process = False


    def pull(self, file_list: list[Path], source: str, destination:str):
        """
         Download files from a pre-selected device into the pc.
        :param file_list: dictionary with paths to files and file names.
        :param source: string path used as source base. It is a device path.
        :param destination: string path used as destination base. It is a PC path.
        """

        if file_list:
            destination = destination.rstrip("/")
            HostChannel.create_directory_in_host(destination)
            folders_created = []
            for file_path in file_list:
                outputsub = self.get_subfolder(source, file_path)
                destination_pathlib = Path(destination)
                destination_pathlib = destination_pathlib / outputsub.lstrip("/")
                final_destination = destination_pathlib.as_posix().rstrip("/")
                if outputsub and final_destination not in folders_created:
                    folders_created.append(final_destination)
                    HostChannel.create_directory_in_host(final_destination)
                MtpChannel.pull_file(file_path, final_destination)
                if self.cancel_load_process:
                    break
        else:
            self.logger.info("The destination path provided: {source} have no files or the filters are too restrictive.".format(source=source))

        self.cancel_load_process = False


    def get_file_list(self, input_path:str, includes_filters:list[str], excludes_filters:list[str], check_directories:bool = False) -> list:
        """
        Get the list of files from the device.
        :param input_path: path to the folder where the files will be searched.
        :param includes_filters: list of string filters glob style. Those paths that fulfill one of the patterns will be transported
        :param excludes_filters: list of string filters glob style. Those paths that fulfill one of the patterns will not be transported.
        :param check_directories: boolean to check only files (False) or directories (True).
        :return: a list containing Path of the files found.
        """
        input_path = input_path.rstrip("/")
        if check_directories:
            file_list = MtpChannel.get_directories_list(input_path)
        else:
            file_list = MtpChannel.get_file_list(input_path)

        file_list = FileScanner.filter_files_list(file_list, includes_filters, True)
        file_list = FileScanner.filter_files_list(file_list, excludes_filters, False)

        return file_list



