import re
import shutil
import time

try:
    import winreg
    WINDOWS = True
except ImportError:
    WINDOWS = False

from pathlib import Path, PureWindowsPath
import subprocess
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import os

from ...i18n import tr

from ... import constants
from ...constants import QGIS_PLUGIN_NAME
from ...logger.qgis_logger_handler import QgisLoggerHandler

ADB_WINDOWS_NAME = "adb.exe"

class FindAdb:

    @staticmethod
    def get_full_windows_path() -> str:
        """
            Try to get the paths from system and user environment variable PATH. Also expands the variables.
            :return: The full system and user environment variable PATH for WINDOWS and the PATH environment variable for
            other systems.
        """
        if WINDOWS:
            # System PATH
            key_system = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                                        r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment')
            system_path, _ = winreg.QueryValueEx(key_system, 'PATH')
            winreg.CloseKey(key_system)

            # User PATH
            try:
                key_user = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment')
                user_path, _ = winreg.QueryValueEx(key_user, 'PATH')
                winreg.CloseKey(key_user)
            except Exception:
                user_path = ''

            # Combine
            full_path = f"{user_path};{system_path}" if user_path else system_path

            # Expand environment variables (%SystemRoot%, etc.)
            return os.path.expandvars(full_path)
        else:
            return os.environ.get('PATH', '')

    @staticmethod
    def find_adb() -> str:
        """
            Try to find the adb binary from the system environment PATH variable.
            :return: The adb binary path if found. If not found try to search in common places (_search_in_common_locations).
        """
        # Get PATH depending on OS
        system_path = FindAdb.get_full_windows_path()

        path_separator = ';' if WINDOWS else ':'

        # Binary name for every OS
        adb_name = ADB_WINDOWS_NAME if WINDOWS else 'adb'

        # Search in every directory of PATH
        for directory in system_path.split(path_separator):
            adb_path = os.path.join(directory, adb_name)
            if os.path.isfile(adb_path) and os.access(adb_path, os.X_OK):
                if WINDOWS:
                    return str(PureWindowsPath(adb_path))
                else:
                    return Path(adb_path).as_posix()

        # ADB common locations.
        return FindAdb._search_in_common_locations()


    @staticmethod
    def _search_in_common_locations() -> str:
        """
            Try to find the adb binary in common locations depending on OS.
            :return: If the adb binary is found then is returned. If not returns an empty string.
        """
        # ADB common locations.
        common_locations = []
        if WINDOWS:  # Windows
            common_locations = [
                os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Android', 'Sdk', 'platform-tools', ADB_WINDOWS_NAME),
                os.path.join(os.environ.get('USERPROFILE', ''), 'AppData', 'Local', 'Android', 'Sdk', 'platform-tools',
                             ADB_WINDOWS_NAME),
                'C:\\Android\\sdk\\platform-tools\\adb.exe',

            ]
        else:  # Linux/Mac
            common_locations = [
                os.path.expanduser('~/Android/Sdk/platform-tools/adb'),
                os.path.expanduser('~/Library/Android/sdk/platform-tools/adb'),
                '/usr/local/bin/adb',
                '/usr/bin/adb',
            ]

        for path in common_locations:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                if WINDOWS:
                    return str(PureWindowsPath(path))
                else:
                    return Path(path).as_posix()
        return ""

    @staticmethod
    def initialisation_required(method):
        """
            Initialise AdbChannel with the correct adb binary.
            :param method: method of AdbChannel that was called.
            :return: the call of the method of AdbChannel that was called.
        """

        def wrapper(*args, **kwargs):
            cls = AdbChannel  # class reference
            if not cls._initialised:
                logger = QgisLoggerHandler(
                    QGIS_PLUGIN_NAME,
                    level=logging.INFO
                ).get_logger()

                try:
                    adb_path = FindAdb.find_adb()
                    # Execute "adb version" to see if ADB is installed
                    if adb_path:
                        result = subprocess.run(
                            adb_path + " version",
                            stdout=subprocess.PIPE,  # get standard output
                            stderr=subprocess.PIPE,  # get errors
                            creationflags=subprocess.CREATE_NO_WINDOW,
                            text=True,  # output text not bytes
                        )
                        logger.info("ADB installed.")
                        logger.info(result.stdout.strip())  # show version
                        cls._adb_path = adb_path
                except FileNotFoundError:
                    raise FileNotFoundError("Error: Adb not installed, or isn't in the path")
                except subprocess.CalledProcessError as e:
                    raise subprocess.CalledProcessError(e.returncode, e.cmd,e.output.strip(),
                                                        "Error while executing adb: {error}".format(error=e.stderr.strip()))
                cls._initialised = True
            return method(*args, **kwargs)
        return wrapper


class AdbErrorType(Enum):
    ADB_NOT_FOUND = tr("ADB not found")
    ADB_NOT_EXECUTABLE = tr("ADB found but is not executable")
    ADB_SERVER_ERROR = tr("Error when initialising ADB server")
    DEVICE_UNAUTHORIZED = tr("Not authorized device (check USB debugging)")
    DEVICE_OFFLINE = tr("Offline device")
    USB_DEBUGGING_DISABLED = tr("USB debugging disabled")
    PERMISSIONS_ERROR = tr("Not enough permissions")
    MULTIPLE_DEVICES = tr("Too many devices without specification")
    ADB_OUTDATED = tr("ADB version deprecated or not compatible")
    SUBPROCESS_ERROR = tr("Error while executing subprocess")
    UNKNOWN_ERROR = tr("Unknown error")


@dataclass
class AdbStatus:
    available: bool
    error_type: Optional[AdbErrorType]
    error_message: str
    details: dict


class AdbChannel:

    """
        Group of methods that use adb to query/change data on the mobile device using ADB.

        :ivar _initialised: boolean that verifies whether the class has been initialised.
        :vartype _initialised: bool
        :ivar _selected_device_id: string id of the device where the commands will be executed.
        :vartype _selected_device_id: str
        :ivar _so_id: string id of the so that was detected on the pc.
        :vartype _so_id: str
        :ivar _adb_path: string path of the adb executable.
        :vartype _adb_path: str
    """

    _initialised = False
    _selected_device_id = ""
    _so_id = 0
    _adb_path = ""

    class AdbChecker:

        def check_availability(self) -> AdbStatus:
            """
                Verify that ADB is available and returns the current state.
                Check if the adb binary exists in the given path, if it can be executed and that the adb servers is
                running.
                :return: AdbStatus of the current state.
            """

            # 1. Verify that ADB exists
            adb_check = self._check_adb_binary()
            if not adb_check["available"]:
                return AdbStatus(
                    available=False,
                    error_type=adb_check["error_type"],
                    error_message=adb_check["message"],
                    details=adb_check
                )



            # 2. Verify ADB version
            version_check = self._check_adb_version()
            if not version_check["available"]:
                return AdbStatus(
                    available=False,
                    error_type=version_check["error_type"],
                    error_message=version_check["message"],
                    details=version_check
                )

            # 3. Verify ADB server
            server_check = self._check_adb_server()
            if not server_check["available"]:
                return AdbStatus(
                    available=False,
                    error_type=server_check["error_type"],
                    error_message=server_check["message"],
                    details=server_check
                )


            return AdbStatus(
                available=True,
                error_type=None,
                error_message="",
                details={
                    "adb_path": self.adb_path,
                    "version": version_check.get("version"),
                }
            )

        def _check_adb_binary(self) -> dict:
            """
                Check if the adb binary path is correct and that the adb binary can be executed.
                :return: AdbStatus of the current state.
            """

            if AdbChannel._adb_path:
                self.adb_path = AdbChannel._adb_path
            else:
                self.adb_path = ""


            # If a path was given, then verify it.
            if self.adb_path:
                if not os.path.exists(self.adb_path):
                    return {
                        "available": False,
                        "error_type": AdbErrorType.ADB_NOT_FOUND,
                        "message": "ADB not found on the given path: {path}".format(path = self.adb_path),
                        "path": self.adb_path
                    }
                if not os.access(self.adb_path, os.X_OK):
                    return {
                        "available": False,
                        "error_type": AdbErrorType.ADB_NOT_EXECUTABLE,
                        "message": "ADB found but do not have execute permission: {path}".format(path = self.adb_path),
                        "path": self.adb_path
                    }

                return { "available": True, "path": self.adb_path }
            else:
                return {
                    "available": False,
                    "error_type": AdbErrorType.ADB_NOT_FOUND,
                    "message": "ADB not found on PATH or usual places"
                }

        def _check_adb_version(self) -> dict:
            """
                Execute the adb binary to get it version and check for possible errors.
                :return: AdbStatus of the current state.
            """

            try:
                result = subprocess.run(
                    [self.adb_path, "version"],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    text=True,
                    timeout=5
                )

                if result.returncode == 0:
                    version = result.stdout.strip()
                    return {"available": True, "version": version}
                else:
                    return {
                        "available": False,
                        "error_type": AdbErrorType.ADB_OUTDATED,
                        "message": "Error while obtaining ADB version: {error}".format(error=result.stderr)
                    }

            except subprocess.TimeoutExpired:
                return {
                    "available": False,
                    "error_type": AdbErrorType.SUBPROCESS_ERROR,
                    "message": "Timeout when executing 'adb version'"
                }
            except PermissionError:
                return {
                    "available": False,
                    "error_type": AdbErrorType.PERMISSIONS_ERROR,
                    "message": "Not enough permission to execute ADB"
                }
            except Exception as e:
                return {
                    "available": False,
                    "error_type": AdbErrorType.UNKNOWN_ERROR,
                    "message": "Error while verifying the version: {error}".format(error=str(e))
                }



        def _check_adb_server(self) -> dict:
            """
                Try to start the ADB server and check for possible errors.
                :return: AdbStatus of the current state.
            """
            try:
                # Intentar iniciar el servidor
                result = subprocess.run(
                    [self.adb_path, "start-server"],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 or "daemon started successfully" in result.stdout.lower():
                    return {"available": True}
                else:
                    return {
                        "available": False,
                        "error_type": AdbErrorType.ADB_SERVER_ERROR,
                        "message": "Error when starting the ADB server: {error}".format(error=result.stderr),
                        "details": result.stdout
                    }

            except subprocess.TimeoutExpired:
                return {
                    "available": False,
                    "error_type": AdbErrorType.ADB_SERVER_ERROR,
                    "message": "Timeout when starting ADB Server"
                }
            except Exception as e:
                return {
                    "available": False,
                    "error_type": AdbErrorType.SUBPROCESS_ERROR,
                    "message": "Error when verifying the ADB server: {error}".format(error=str(e))
                }

    @staticmethod
    def put_adb_path(adb_path: str):
        """
            Saves the adb binary path into an internal attribute, and set it as initialised.
            :param adb_path: string path of the adb executable.
        """
        AdbChannel._adb_path = adb_path
        AdbChannel._initialised = True

    @staticmethod
    def get_adb_path() -> str:
        """
            Returns the adb binary path stored in this class.
            :return: string path of the adb executable.
        """
        return AdbChannel._adb_path

    @staticmethod
    def get_initialised() -> bool:
        """
            Returns the bool stored in this class that indicates if the class was initialised.
            :return: bool.
        """
        return AdbChannel._initialised


    @staticmethod
    def is_available() -> AdbStatus:
        """
            Execute a serie of methods to check if ADB is available.
            :return: AdbStatus with the current state.
        """
        checker = AdbChannel.AdbChecker()
        adb_availability = checker.check_availability()
        if adb_availability.available:
            AdbChannel._initialised = True
            AdbChannel._adb_path = adb_availability.details.get('adb_path')
        return adb_availability


    @staticmethod
    @FindAdb.initialisation_required
    def get_devices() -> str:
        """
            Get the list of devices connected devices to the pc via adb.
            :return: string of all devices connected.
        """
        cmd = [AdbChannel._adb_path, "devices"]
        return subprocess.check_output(cmd, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    @staticmethod
    def set_default_device_id(device_id: str):
        """
            Set the default id of the device where the commands will be executed.
            :param device_id: string id of the device where the commands will be executed.
        """
        AdbChannel._selected_device_id = device_id

    @staticmethod
    def get_default_device_id() -> str:
        """
            Get the current device id that's been used.
            :return: string id of the current device.
        """
        return AdbChannel._selected_device_id

    @staticmethod
    @FindAdb.initialisation_required
    def pull_file(file_path: str, output_path:str):
        """
            Pull a file from the connected device with id _selected_device_id.
            :param file_path: string path of the file.
            :param output_path: string path on the pc where the file will be saved.
        """

        logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

        if AdbChannel._adb_path:
            logger.info("Copying file {file}".format(file=file_path))
            cmd = [AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "pull", "-p", file_path, output_path]
            subprocess.check_output(cmd, text=True, creationflags=subprocess.CREATE_NO_WINDOW)



    @staticmethod
    @FindAdb.initialisation_required
    def push_file(file_path: str, output_path: str):
        """
            Push a file from the pc to the connected device with id _selected_device_id.
            :param file_path: string path of the file.
            :param output_path: string path on the device where the file will be saved.
        """
        logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

        if AdbChannel._adb_path:
            logger.info("Copying file {file}".format(file=file_path))
            cmd = [AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "push", "-p", file_path, output_path]
            subprocess.check_output(cmd, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

    @staticmethod
    @FindAdb.initialisation_required
    def no_recursive_ls(path: str, device_id: str = "") -> str:
        """
            Get the list of files/directories found on a path at first level.
            :param path: string path on device where the ls will be performed.
            :param device_id: string id of the device where the ls will be performed.
            :return: list of files/directories at first level on the device as a string.
        """
        if AdbChannel._adb_path:
            device_id_to_use = device_id if device_id else AdbChannel._selected_device_id
            cmd = [AdbChannel._adb_path, "-s", device_id_to_use, "shell", "ls", path]
            return subprocess.check_output(cmd, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            return ""

    @staticmethod
    @FindAdb.initialisation_required
    def get_current_used_id(device_id: str = "") -> str:
        """
            Get the id of the current user in the device.
            :param device_id: string id of the device where the search of the current user will be performed.
            :return: current user id.
        """
        if AdbChannel._adb_path:
            device_id_to_use = device_id if device_id else AdbChannel._selected_device_id
            cmd = [AdbChannel._adb_path, "-s", device_id_to_use, "shell",  "dumpsys activity"]
            result = subprocess.run(cmd, text=True, capture_output=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
            match = re.search(r"mCurrentUser=(\d+)", result.stdout)
            current_user = match.group(1) if match else None
            return current_user
        else:
            return ""

    @staticmethod
    @FindAdb.initialisation_required
    def create_directory_in_device(directory_path: str) -> bool:
        """
            Create a directory in the device if it can.
            :param directory_path: string path where directory will be created on the selected device.
            :return: Bool to know if the directory was created.
        """
        if AdbChannel._adb_path:
            if not AdbChannel.check_directory_exists(directory_path):
                logger = QgisLoggerHandler(
                    QGIS_PLUGIN_NAME,
                    level=logging.INFO
                ).get_logger()


                logger.info("Creating directory {directory}".format(directory = directory_path))
                cmd = [AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "shell", "mkdir",
                       "-p", f"{directory_path}"]
                subprocess.check_output(cmd, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                return True
            return False
        else:
            return False


    @staticmethod
    @FindAdb.initialisation_required
    def check_directory_exists(directory_path: str) -> bool:
        """
            Create a directory in the device if it can.
            :param directory_path: string path where directory will be created on the selected device.
            :return: bool to know if the directory exists. True exists, False not exists.
        """
        if AdbChannel._adb_path:
            return subprocess.run([AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "shell", "test", "-d" ,
                               f"{directory_path}","&& echo 0 || echo 1"],
                              capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip() == "0"
        else:
            raise FileNotFoundError("ADB binary not found.")

    @staticmethod
    @FindAdb.initialisation_required
    def check_file_exists(file_path: str) -> bool:
        """
            Create a directory in the device if it can.
            :param file_path: string path where directory will be created on the selected device.
            :return: Bool to know if the directory exists. True exists, False not exists.
        """
        if AdbChannel._adb_path:
            return subprocess.run([AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "shell", "test", "-e" ,
                               f"{file_path}","&& echo 0 || echo 1"],
                              capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout.strip() == "0"
        else:
            raise FileNotFoundError("ADB binary not found.")

    @staticmethod
    @FindAdb.initialisation_required
    def update_cartodruid_device_db():
        """
            Send a message to the device app Cartodruid to update all the referenced databases.
        """
        if AdbChannel._adb_path:
            db_updated = subprocess.run([AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "shell", "am", "broadcast" ,
                               "-a","es.jcyl.ita.crtdrd.REFRESH_DATABASE"],
                                        capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if db_updated.returncode != 0:
                raise subprocess.CalledProcessError(db_updated.returncode,db_updated.args, output=db_updated.stdout, stderr=db_updated.stderr)

        else:
            raise FileNotFoundError("ADB binary not found.")



    @staticmethod
    @FindAdb.initialisation_required
    def get_file_list(input_path: str) -> list:
        """
             Get the list of files (recursively) on the designated path.
             :param input_path: string path where the search of files will be executed.
             :return: list of all files found on input_path.
        """

        if AdbChannel._adb_path:
            files_paths = ""
            cmd = [AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "shell", "find", input_path, "-type f"]
            try:
                files_paths = subprocess.run(cmd, text=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
            except subprocess.CalledProcessError as e:
                raise subprocess.CalledProcessError(e.returncode, e.cmd,e.output.strip(),
                                                        "Error while executing adb: {error}".format(error = e.stderr.strip()))
            return AdbChannel._convert_to_path_list(files_paths)
        else:
            return []


    @staticmethod
    @FindAdb.initialisation_required
    def get_directories_list(path: str) -> list:
        """
            Get the list of all directories on the designated path.
            :param path: string path where the search of directories will be executed.
            :return: list of all directories found on path.
        """
        if AdbChannel._adb_path:
            directories_paths = ""
            cmd = [AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "shell", "find", path, "-type", "d"]
            try:
                directories_paths = subprocess.run(cmd, text=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW).stdout
            except subprocess.CalledProcessError as e:
                raise subprocess.CalledProcessError(e.returncode, e.cmd,e.output.strip(),
                                                        "Error while executing adb: {error}".format(error=e.stderr.strip()))
            return AdbChannel._convert_to_path_list(directories_paths)
        else:
            return []


    @staticmethod
    @FindAdb.initialisation_required
    def extract_file_type(path_to_file: str, file_name: str) -> str:
        """
             Get the type (directory or file) of the file from the connected device with id _selected_device_id.
             :param path_to_file: string path to the file that we will check for its type.
             :param file_name: string name of the file that we will check for its type.
             :return: string type of the file.
        """
        if AdbChannel._adb_path:
            result_sub = subprocess.run(
                [AdbChannel._adb_path, "-s", AdbChannel._selected_device_id, "shell",
                 f'if [ -d "{path_to_file}/{file_name}" ]; then echo {constants.DIRECTORY_TYPE}; elif '
                 f'[ -f "{path_to_file}/{file_name}" ]; then echo {constants.FILE_TYPE}; else echo "No exist"; fi'],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result_sub.stdout.strip()
        else:
            return ""


    @staticmethod
    @FindAdb.initialisation_required
    def get_information_about_device(getprop: str, device_id: str = "") -> str:
        """
             A prepared command to get the information about the connected device with id device_id.
             In this case we will not use _selected_device_id as the id of the device where the commands will be executed.
             :param device_id: string id of the device to get the information about.
             :param getprop: string of the property that will be retrieved.
             :return: The property information of the connected device asked.
        """
        if AdbChannel._adb_path:
            device_id_to_use = device_id if device_id else AdbChannel._selected_device_id
            info = subprocess.run(
                [AdbChannel._adb_path, "-s", device_id_to_use, "shell", "getprop", getprop],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )

            return info.stdout.strip()
        else:
            return ""

    @staticmethod
    def check_create_directory_device(directory_path: str, input_path: str, output_path: str) -> str:
        """
        Check if a directory exists on the designated path. If not, it is created.
        :param directory_path: string path where the directory is in the PC.
        :param input_path: string path used to clean the base folder from directory_path.
        :param output_path: string path where the directory will be created on the selected device.
        :return: the difference between directory_path and input_path.
        """
        pathlib_outputsub = Path()
        clean_directory_path = Path(directory_path.rstrip("/")).as_posix()
        clean_input_path = Path(input_path.rstrip("/")).as_posix()
        clean_output_path_path = Path(output_path.rstrip("/")).as_posix()
        if len(clean_input_path) <= len(clean_directory_path):
            output_subdirectories = clean_directory_path.replace(clean_input_path, "")
            pathlib_outputsub = Path(output_subdirectories.lstrip("/"))
            directories = []
            accumulated = Path()
            for part in pathlib_outputsub.parts:
                accumulated = accumulated / part
                directories.append(accumulated)
            if directories and len(directories) != 0:
                for directory in directories:
                    current_directory = clean_output_path_path.rstrip("/") + "/" + directory.as_posix()
                    AdbChannel.create_directory_in_device(current_directory)
        return pathlib_outputsub.as_posix()


    @staticmethod
    def _convert_to_list_adb_search_directories_output(output: str) -> list:
        '''
            Creates a list with the output of search directories of AdbChannel.
            :param output: string paths to directories in multiple lines
            :return: list with a line of output for every list value.
        '''

        return [line.strip() for line in output.splitlines() if line.strip() != ""]

    @staticmethod
    def _convert_to_path_list(output: str)-> list:
        """
            Converts the output of find path -type f to a dictionary.
            Empty directories are removed.
            :param output: string output of ls -R with adb over a device folder
            :return: list with Path(path) in it.
        """
        result = []

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            result.append(Path(line))

        return result