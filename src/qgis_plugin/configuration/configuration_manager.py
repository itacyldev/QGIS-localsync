import copy
import json
import logging
import os
from pathlib import Path
from typing import Tuple

from qgis.PyQt.QtCore import pyqtSignal, QObject
from qgis.PyQt.QtWidgets import QMessageBox, QDialog

from qgis._core import QgsApplication, QgsProject, QgsSettings
from .. import constants
from ..constants import QGIS_PLUGIN_NAME, QGIS_SCOPE_NAME, QGIS_CONFIG_KEY, QGIS_ADB_OR_MTP_KEY, \
    CARTODRUID_PROJECT_SPLITTERS
from ..i18n import tr
from ..localsync.channels.adb_channel import AdbChannel, FindAdb
from ..localsync.core.sync_engine import SyncEngine
from ..localsync.device.device_manager import DeviceManager
from ..localsync.project.project_manager import ProjectManager
from ..logger.qgis_logger_handler import QgisLoggerHandler


class ConfigurationManager(QObject):

    """
        Manages the configuration for the synchronising.
        :ivar adb_activated: indicates whether ADB (True) is the protocol to use or MTP (False).
        :vartype adb_activated: bool
        :ivar config: current configuration of the plugin.
        :vartype config: list[dict]
        :ivar conf_dlg: reference to the configuration dialog object.
        :vartype conf_dlg: QDialog
        :ivar configuration_changed: Signal used to broadcast that the configuration has been changed.
        :vartype conf_dlg: pyqtSignal
    """

    config = []
    conf_dlg = None
    adb_activated = True
    configuration_changed = pyqtSignal()

    def __init__(self, s_eng: SyncEngine):
        """
            Constructor.
           :param s_eng: reference to the SyncEngine object. Main functionality of the plugin.
        """
        super().__init__()
        self.s_eng = s_eng
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

        self.project_label = None

        self.read_config()
        self.search_and_save_adb()


    def set_conf_dlg(self, conf_dlg: QDialog):
        """
        Sets the configuration dialog object.
        :param conf_dlg: reference to the configuration dialog object.
        """
        self.conf_dlg = conf_dlg

    def search_for_projects_in_config(self) -> list[str]:
        """
        Search for a name project in the current configuration. A project name is gathered from the folder name after
        cartodroid/projects or cartodruid/projects.
        :return: a list with the project names found.
        """

        found_projects = []
        for config in self.config:
            if "destination" in config:
                for cartodruid_project in CARTODRUID_PROJECT_SPLITTERS:
                    found_project = ProjectManager.get_project_name_from_path(Path(config["destination"]), cartodruid_project)
                    if found_project and found_project not in found_projects:
                        found_projects.append(found_project)
        return found_projects

    def _find_adb_in_the_same_folder(self, list_dir:list[str], adb_path:str) -> Tuple[bool, str]:
        """
            Tries to find the adb binary in the given folder.
            :param list_dir: list of files found on abd_path.
            :param adb_path: Absolute path to where the adb binary is supposed to be.
            :return: True if adb binary is found, False otherwise, and a string containing the path.
        """

        found = False
        correct_path = ""
        for item in list_dir:
            if item == "adb.exe" or item == "adb":
                found = True
                correct_path = os.path.join(adb_path, item)
                break
        return found, correct_path

    def _find_adb_inside_folder(self, list_dir:list, adb_path: str) -> Tuple[bool, str]:
        """
            Tries to find the adb binary inside a folder from a list given.
            :param list_dir: list of files found on abd_path.
            :param adb_path: Absolute path to where the adb binary is supposed to be.
            :return: True if adb binary is found, False otherwise, and a string containing the path.
        """
        found = False
        correct_path = ""
        adb_sub_path = os.path.join(adb_path, list_dir[0])
        new_list_dir = os.listdir(adb_sub_path)
        for item in new_list_dir:
            if item == "adb.exe" or item == "adb":
                found = True
                correct_path = os.path.join(adb_sub_path, item)
                break
        return found, correct_path

    def find_adb_in_automatic_path(self) -> Tuple[bool, str]:
        """
            Try to find the ADB executable in automatic download path.
            :return: True if ADB was found, False otherwise. String of the ADB executable path.
        """

        adb_path = os.path.join(
            QgsApplication.qgisSettingsDirPath(),
            constants.QGIS_PLUGIN_NAME,
            "adb_binary"
        )
        adb_path = Path(adb_path).as_posix()
        found = False
        correct_path = ""
        if os.path.exists(adb_path):
            list_dir = os.listdir(adb_path)
            if len(list_dir) > 1:
                found, correct_path = self._find_adb_in_the_same_folder(list_dir, adb_path)
            else:
                if len(list_dir) > 0:
                    found, correct_path = self._find_adb_inside_folder(list_dir, adb_path)
            correct_path = Path(correct_path).as_posix()

        return found, correct_path



    def read_config(self):
        """
            Read the configuration stored in the project file of QGIS and set them as current configuration.
        """
        project = QgsProject.instance()
        value, ok = project.readEntry(
            QGIS_SCOPE_NAME,
            QGIS_CONFIG_KEY
        )
        try:
            if ok:
                self.config = json.loads(value)
        except json.JSONDecodeError:
            self.logger.warning("Json malformed")
            QMessageBox.warning(self.conf_dlg, "Json malformed", tr("The json provided is malformed. Changes are not saved."))


        value, ok = project.readEntry(
            QGIS_SCOPE_NAME,
            QGIS_ADB_OR_MTP_KEY
        )
        if ok:
            self.adb_activated = value == "1"
            self.s_eng.activate_mtp_or_adb(self.adb_activated)
        else:
            self.adb_activated = True
            self.s_eng.activate_mtp_or_adb(self.adb_activated)

        self.configuration_changed.emit()


    def save_config(self, new_config : list[dict] = None, check_paths : bool = False, device: DeviceManager = None):
        """
            Save the new configuration in the project file of QGIS and set it as the current configuration.
            :param new_config: configuration json string to be loaded and saved.
            :param check_paths: if True, the paths of the configuration will be checked, False otherwise.
            :param device: device used to check if the configuration paths are correct.
        """
        project = QgsProject.instance()
        path_found = False
        if check_paths:
            transformed_config = self.convert_config_relative_path_to_absolute(new_config)
            path_found =  self.check_if_config_path_exists(transformed_config, False, device)
        if not check_paths or path_found:
            if new_config != self.config:
                self.config = new_config

            project.writeEntry(
                constants.QGIS_SCOPE_NAME,
                constants.QGIS_CONFIG_KEY,
                json.dumps(self.config)
            )

            self.configuration_changed.emit()


    def convert_config_relative_path_to_absolute(self, new_config: list[dict]) -> list[dict]:
        """
            Check if the source path in the configuration is relative and transforms it to absolute.
            :param new_config: configuration dictionary to convert.
            :return: configuration with absolute paths.
        """
        transformed_config = copy.deepcopy(new_config)
        for config in transformed_config:
            if "source" in config and config["source"] and config["source"][0] == ".":
                config["source"] = Path(os.path.dirname(
                                    QgsProject.instance().fileName())).joinpath(config["source"]).resolve().as_posix()
        return transformed_config

    def check_if_config_path_exists(self, configs: list, check_destination:bool, device: DeviceManager) -> bool:
        """
            Check if all the paths in the given config exists. The paths not found are shown in a dialog.
             Device paths only are at the root level.
            :param configs: List of configs to check.
            :param check_destination: True it will check the device path with the current device, False otherwise.
            :param device: device to check on if the different paths exists.
            :return: True if all the paths exist, False otherwise.
        """

        no_exists_paths = []
        if device:
            for config in configs:
                no_exists_paths = self.check_source_exists(config, no_exists_paths, check_destination, device)

            if no_exists_paths:
                path_string = "\n" + "\n".join(no_exists_paths)
                self.logger.warning("Configuration path does not exist")
                QMessageBox.warning(None, tr("Configuration path does not exist"),
                                    tr("The following configuration paths does not exist: {path}").format(path=path_string))
                return False
        return True


    def check_source_exists(self, config:dict, no_exists_paths:list, check_destination:bool, device: DeviceManager) -> list:
        """
            Check the source and destination paths exists for the given config. The device paths only are at the root level.
            :param config: Instance of config to check.
            :param no_exists_paths: List os passed paths that were not found.
            :param check_destination: True it will check the destination path with the curren phone, False otherwise.
            :param device: device to check on if the different paths exists.
            :return: accumulated list of paths that were not found.
        """

        if "source" in config:
            if not self.s_eng.check_if_directory_exists(config["source"], device, True):
                no_exists_paths.append(config["source"])
        # Check if destination storage path (root path) exists.
        if check_destination and "destination" in config:
            if not self.s_eng.check_if_directory_exists(config["destination"], device, False):
                no_exists_paths.append(config["destination"])
        return no_exists_paths


    def change_protocol_used(self, use_adb):
        """
            Changed the procol used by the plugin.
            :param use_adb: True change the protocol to use to ADB, False it changes to MTP.
        """
        self.adb_activated = use_adb
        self.s_eng.activate_mtp_or_adb(use_adb)


    def save_adb_path(self, path):
        """
            Gives the adb executable path to the adb_channel.
            :param path: Path to adb executable.
        """
        AdbChannel.put_adb_path(path)

    def search_and_save_adb(self):
        """
            Search the ADB executable path in the QGIS settings, automatic download path and usual places and saves it in
            AdbChannel.
        """
        settings = QgsSettings()
        path = settings.value(constants.QGIS_SCOPE_NAME + "/" + constants.QGIS_CUSTOM_ADB_PATH, "",
                              type=str)
        if not path:
            found, path = self.find_adb_in_automatic_path()
            if not found:
                path = FindAdb.find_adb()
        if path:
            self.save_adb_path(path)
        else:
            self.logger.info("Could not find adb binary path. Please add the path in the configuration menu.")