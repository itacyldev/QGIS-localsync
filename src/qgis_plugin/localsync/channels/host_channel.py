import logging
import os

from ...constants import QGIS_PLUGIN_NAME
from ..data_actions.file_scanner import FileScanner
from pathlib import Path

from ...logger.qgis_logger_handler import QgisLoggerHandler


class HostChannel:
    """
        List of file management utilities for the PC.
    """

    @staticmethod
    def check_file_exists(directory: str) -> bool:
        """
            Check if the given directory exists.
            :param: directory: Directory to check.
            :return: bool True if the directory exists. False otherwise.
        """
        return os.path.exists(directory)

    @staticmethod
    def create_directory_in_host(directory_path: str):
        """
            Create directory in the PC.
            :param directory_path: string path of the directory to create.
        """
        if not HostChannel.check_file_exists(directory_path):
            logger = QgisLoggerHandler(
                QGIS_PLUGIN_NAME,
                level=logging.INFO
            ).get_logger()

            logger.info(f"Creating directory {directory_path}.")
            os.makedirs(f"{directory_path}", exist_ok=True)

    @staticmethod
    def get_file_list(input_path: str, include_filters: list[str], exclude_filters: list[str],
                      only_directories: bool = False) -> list:
        """
            Get the list of files from the pc.
            :param input_path: path to the folder where the files will be searched.
            :param include_filters: list of filters that when applied the object filtered will be included.
            :param exclude_filters: list of filters that when applied the object filtered will be excluded.
            :return: list containing the files and their paths.
        """
        input_path = input_path.rstrip("/")
        if only_directories:
            file_list = HostChannel._create_directories_list_from_pc_path(input_path)
        else:
            file_list = HostChannel._create_list_from_pc_path(input_path)
        file_list = FileScanner.filter_files_list(file_list, include_filters, True)
        file_list = FileScanner.filter_files_list(file_list, exclude_filters, False)
        return file_list


    @staticmethod
    def _create_list_from_pc_path(path: str)-> list:
        """
            Scan recursively a directory to find theirs files and directories.
            Empty directories are removed.
            :param path: path where the files will be searched.
            :return: list with Path(file_path) in it.
        """
        result = []
        if os.path.exists(path):
            if os.path.isfile(path):
                result = [Path(path)]
            else:
                for root, directories, files in os.walk(path):
                    for f in files:
                        full_path = Path(root) / f
                        result.append(full_path)

        return result

    @staticmethod
    def _create_directories_list_from_pc_path(path: str)-> list:
        """
          Scan recursively a directory to find their subdirectories.
          :param path: path where the subdirectories will be searched.
          :return: list with the subdirectories found.
        """
        result = []
        for root, directories, files in os.walk(path):
            result.append(Path(root))
        return result


