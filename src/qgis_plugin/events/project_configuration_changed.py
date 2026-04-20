from __future__ import annotations
import json
import logging
import os
from pathlib import Path
import xml.etree.ElementTree as ET

from PyQt5.QtWidgets import QMessageBox

from qgis._core import QgsProject, QgsApplication
from ..constants import QGIS_SCOPE_NAME, QGIS_PROJECT_CONFIG_KEY, QGIS_PLUGIN_NAME, CARTODRUID_CONFIG_NAME
from ..dialog.project_wizard.project_wizard_data import ProjectWizardData
from ..i18n import tr
from ..localsync.core.sync_engine import SyncEngine
from ..localsync.device.device_manager import DeviceManager
from ..logger.qgis_logger_handler import QgisLoggerHandler
from ..tasks.read_config_file_carto import ReadConfigFileCarto
from ..signals.global_signals import cac_check, lcpc2p

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..local_sync_plugin import SyncListener


class ProjectConfigurationChanged:

    """
        Event used to compare between previously downloaded Cartodruid configuration and device Cartodruid.
        :ivar last_configuration: last stored project configuration of the QGIS project.
        :vartype last_configuration: ProjectWizardData
        :ivar logger: logger of the application.
        :vartype logger: logging.Logger
        :ivar s_task: Reference to the ReadConfigFileCarto task if it is active. None if it is not active.
        :vartype s_task: QgsTask
    """

    last_configuration = ProjectWizardData()

    def __init__(self, s_eng:SyncEngine, s_listener: SyncListener):
        """
        Constructor.
        :param s_eng: reference to the synchronization engine used by the application to download/upload files from/to the device.
        :param s_listener: reference to the synchronization listener used by the application to create messageBars on the main thread.
        """

        self.s_eng = s_eng
        self.s_listener = s_listener

        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.s_task = None


    def check_project_configuration_changed(self, device:DeviceManager):
        """
            Loads the current Cartodruid project configuration of the QGIS project and starts the download of the configuration on the device
            Cartodruid project configuration. If there is no need to compare the configurations (new QGIS project, for example) it returns False.
            True otherwise.
            :param device: data of the device from where the Cartodruid configuration will be consulted.
            :return: True if there will be a further process to compare the configurations, False otherwise.
        """
        self.logger.info("Comparing configuration files between Cartodruid and QGIS...")
        project = QgsProject.instance()
        value, ok = project.readEntry(
            QGIS_SCOPE_NAME,
            QGIS_PROJECT_CONFIG_KEY
        )

        try:
            if ok:
                config = json.loads(value)
                self.last_configuration = ProjectWizardData.from_dict(config)
            else:
                return False
        except json.JSONDecodeError:
            self.logger.warning("There was an error while trying to read the project configuration for this QGIS project. Json malformed.")

        if not self.s_task:
            self.carto_conf_pc_dir = os.path.join(
                QgsApplication.qgisSettingsDirPath(),
                QGIS_PLUGIN_NAME,
                "conf",
                self.last_configuration.get_project_selected().project_name
            )

            os.makedirs(self.carto_conf_pc_dir, exist_ok=True)
            self.s_task = ReadConfigFileCarto(self.s_eng, self.last_configuration.get_project_selected(),
                                              device, self.carto_conf_pc_dir, self.s_listener)
            self.logger.info("Looking for data files in cartodruid project...")
            self.s_task.taskCompleted.connect(self._downloaded_conf_completed)
            self.s_task.taskTerminated.connect(self._downloaded_conf_terminated)
            QgsApplication.taskManager().addTask(self.s_task)
        return True

    def _downloaded_conf_completed(self):
        """
            Callback function called when the Cartodruid project configuration download is completed. Compares it to the last configuration.
            an event (qgis_plugin.signals.cac_check) with True if the configurations are different and False otherwise.
            Creates a message box for the user to open the Configuration Project Wizard so he can add the new files to the configuration.
        """
        if self.s_task:
            self.logger.info("Comparing configurations...")
            tree = ET.parse((Path(self.carto_conf_pc_dir) / CARTODRUID_CONFIG_NAME).as_posix())
            root = tree.getroot()
            not_found = False
            files_not_found = []
            for source in root.iter("es.jcyl.ita.crtcyl.client.dao.source.SpatiaLiteServiceDescriptor"):
                dburl = source.find("dbURL")
                if dburl.text not in self.last_configuration.data_list_full:
                    not_found = True
                    files_not_found.append(dburl.text)
                    self.logger.info("Data file " + dburl.text + " not found in the saved list for this QGIS project.")
                    self.logger.info("Launching 'New layers found' message box.")
            if not_found:
                if self.check_new_layers_message_box():
                    self.logger.info("User answered 'Ok' to 'New layers found' message box.")
                    self.logger.info("Canceling load files process and launching Cartodruid project finder wizard.")
                    cac_check.confirmationReady.emit(True)
                    lcpc2p.launchCartoConfig2ndPage.emit(True)

                else:
                    self.logger.info("User answered 'Cancel' to 'New layers found' message box.")
                    self.logger.info("Resuming load files process.")
                    self.save_current_found_config(files_not_found)
                    cac_check.confirmationReady.emit(False)
            else:
                self.logger.info("No differences found between configurations.")
                cac_check.confirmationReady.emit(False)
        else:
            self.logger.warning("ReadConfigFileCarto Task not found in ProjectConfigurationChanged.")
            cac_check.confirmationReady.emit(False)

        self.s_task = None

    def save_current_found_config(self, not_founds):
        """
            Add some file to the last configuration and write it on the current QGIS project.
        """
        for file_not_found in not_founds:
            self.last_configuration.data_list_full.append(file_not_found)
        project = QgsProject.instance()
        project.writeEntry(
            QGIS_SCOPE_NAME,
            QGIS_PROJECT_CONFIG_KEY,
            json.dumps(self.last_configuration.to_dict())
        )



    def _downloaded_conf_terminated(self):
        """
            Callback function called when the Cartodruid project configuration download is terminated. Launch confirmationReady event
            with False to notice the listener that the compare process was terminated.
        """
        if self.s_task:
            cac_check.confirmationReady.emit(False)
        self.s_task = None


    def check_new_layers_message_box(self) -> bool:
        """
            Creates a MessageBox to notify the user that new layers were found while comparing configurations.
            :return: True if user answered 'Ok' to 'New layers found' message box, False otherwise.
        """
        result = QMessageBox.question(
            None,
            tr("New layers found"),
            tr("New layers were found for this project on CartoDruid. Would you like to add them to the synchronization?\n\n"
               "This will open the project configuration menu, so you can select what do you want to synchronize."),
            QMessageBox.Ok | QMessageBox.Cancel
        )

        if result == QMessageBox.Ok:
            return True
        else:
            return False