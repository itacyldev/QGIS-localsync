# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import logging
import os
import platform
import zipfile
from pathlib import Path

from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QShowEvent
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import QFileDialog, QWidget, QMessageBox

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis._core import QgsProject, QgsApplication, QgsSettings
from .. import constants
from typing import TYPE_CHECKING

from ..configuration.configuration_manager import ConfigurationManager
from ..configuration.json_reader import JsonReader
from ..configuration.photo_layers_configuration import PhotoLayersConfiguration

if TYPE_CHECKING:
    from ..local_sync_plugin import LocalSyncPlugin
from ..localsync.channels.adb_channel import AdbChannel
from ..constants import QGIS_PLUGIN_NAME, WINDOWS_ADB_DOWNLOAD_URL, SYSTEM_ADB_DOWNLOAD_ENV_NAME, \
    QGIS_ADB_BINARY_FOLDER, LINUX_ADB_DOWNLOAD_URL
from ..logger.qgis_logger_handler import QgisLoggerHandler
from ..tasks.download_task import DownloadTask
from ..i18n import tr


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'localsync_conf_panel.ui'))


class LocalsyncConfPanel(QtWidgets.QDialog, FORM_CLASS):

    """
        Class that control the actions of the Configuration Panel.

        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: QgisLoggerHandler
        :ivar project: reference to the current opened project in qgis.
        :vartype project: QgsProject
        :ivar adb_or_mtp_changed: When true it means that the protocol has been changed.
        :vartype adb_or_mtp_changed: bool
        :ivar custom_path: path to the adb binary,
        :vartype custom_path: str
        :ivar adb_or_mtp: Indicates if ADB or MTP is activated. True for ADB, False for MTP.
        :vartype adb_or_mtp: bool
        :ivar json_reader: Used to manage json conversions and reading from text.
        :vartype json_reader: JsonReader
    """


    def __init__(self, localsync_plugin: LocalSyncPlugin, c_manager: ConfigurationManager, photo_conf:PhotoLayersConfiguration,
                 parent: QWidget=None):
        """
            Constructor.
            :param localsync_plugin: reference to the main class.
            :param c_manager: reference to the configuration manager.
            :param parent: parent of the configuration dialog.
        """
        super(LocalsyncConfPanel, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

        self.project = QgsProject.instance()
        self.json_reader = JsonReader()
        self.localsync_plugin = localsync_plugin
        self.c_manager = c_manager
        self.button_box.accepted.connect(self._accept_action)
        self.button_box.rejected.connect(self.reject)
        self.browse.clicked.connect(self._browse_action)
        self.download.clicked.connect(self._download_action)
        self.adb_radio.clicked.connect(self._adb_clicked)
        self.mtp_radio.clicked.connect(self._mtp_clicked)
        self.qsettins = QgsSettings()
        self.adb_or_mtp_changed = False
        self.custom_path = ""
        self.photo_conf = photo_conf

        self.d_task = None
        self.adb_or_mtp = True



    def showEvent(self, event: QShowEvent):
        """
            Add an initialisation when the dialog is opened.
        """
        super().showEvent(event)
        self.on_open_init()

    def on_open_init(self):
        """
            Initialise the radio buttons, and the adb_path found on browse_text.
        """
        value, ok = self.project.readEntry(
            constants.QGIS_SCOPE_NAME,
            constants.QGIS_ADB_OR_MTP_KEY
        )

        if ok:
            value = value == "1"
            if value:
                self.adb_radio.setChecked(True)
                self.adb_radio.repaint()
            else:
                self.mtp_radio.setChecked(True)
                self.mtp_radio.repaint()
            self.adb_or_mtp = value
        else:
            self.adb_or_mtp = True
            self.adb_radio.setChecked(True)
            self.adb_radio.repaint()
        self.get_custom_adb_path()
        if self.custom_path:
            self.browse_text.setText(self.custom_path)

        if AdbChannel.get_initialised() and not self.custom_path:
            self.browse_text.setText(AdbChannel.get_adb_path())

        self.save_check_box.setChecked(self.photo_conf.get_save_layers_bool())


    def save_protocol_conf(self):
        """
            Save the value of adb_or_mtp in the current project file.
        """
        self.project.writeEntry(
            constants.QGIS_SCOPE_NAME,
            constants.QGIS_ADB_OR_MTP_KEY,
            self.adb_or_mtp
        )

    def get_custom_adb_path(self):
        """
            Get the value of custom adb path saved in QGIS settings and saves it on the attribute custom_path.
        """
        self.custom_path = self.qsettins.value(constants.QGIS_SCOPE_NAME + "/" + constants.QGIS_CUSTOM_ADB_PATH, "", type=str)

    def save_custom_adb_path(self):
        """
            Save the value of custom_path int QGIS settings.
        """
        self.qsettins.setValue(constants.QGIS_SCOPE_NAME + "/" + constants.QGIS_CUSTOM_ADB_PATH, self.custom_path)


    def _adb_clicked(self):
        """
            Change the value of adb_or_mtp to True and adb_or_mtp_changed to True as well.
        """
        self.adb_or_mtp = True
        self.adb_or_mtp_changed = True



    def _mtp_clicked(self):
        """
            Change the value of adb_or_mtp to False and adb_or_mtp_changed to True.
        """
        self.adb_or_mtp = False
        self.adb_or_mtp_changed = True


    def _download_action(self):
        """
            Start the download of the adb binary. Create a connection to know when it is finished.
            If the adb_binary is already found on the download path, then the download will be skipped and the user will be notified.
        """
        if not self.d_task:
            found, path = self.c_manager.find_adb_in_automatic_path()
            if not found:
                adb_path = os.path.join(
                    QgsApplication.qgisSettingsDirPath(),
                    constants.QGIS_PLUGIN_NAME,
                    "adb_binary"
                )
                os.makedirs(adb_path, exist_ok=True)
                adb_path = os.path.join(adb_path, "adb.zip")

                adb_download_env = os.environ.get(SYSTEM_ADB_DOWNLOAD_ENV_NAME)
                self.logger.info("Getting adb download url from system environment variables...")
                if not adb_download_env:
                    self.logger.info("System environment variable not found, using default download url.")
                    if platform.system() == "Windows":
                        adb_download_env = WINDOWS_ADB_DOWNLOAD_URL
                    elif platform.system() == "Linux":
                        adb_download_env = LINUX_ADB_DOWNLOAD_URL
                self.d_task = DownloadTask(adb_download_env,
                                           adb_path)
                self.d_task.download_adb_error.connect(self.download_adb_error)
                self.logger.info("Starting download of adb binary.")
                self.d_task.taskCompleted.connect(self._download_completed)
                self.d_task.taskTerminated.connect(self._download_terminated)
                QgsApplication.taskManager().addTask(self.d_task)
            else:
                self.logger.info("Adb was already downloaded and installed at: " + path)
                self.browse_text.setText(path)
        else:
            self.logger.info("There is already a download task. Aborting download.")


    def download_adb_error(self, text:str, translated_text:str):
        """
            Show an error to the user showing possible alternatives. Used for download_task if there is some SSL
            problem.
            :param text: text to show.
            :param translated_text: translated text to show.
        """
        self.d_task.download_adb_error.disconnect(self.download_adb_error)
        self.logger.error(text)
        QMessageBox.critical(None, tr("Download ADB error"), translated_text)


    def _download_terminated(self):
        """
            Used for DownloadTask task as terminated event. Shows errors and reset download task variable.
        """
        self.logger.info("Download process finished abruptly.")
        if not self.d_task.result:
            self.logger.error("Error while downloading the file:" + str(self.d_task.exception))
        self.d_task = None

    def _download_completed(self):
        """
            Method used to be launched when the download of the adb binary is finished. Writes the downloaded data
            to the destination and unzip the file. Finally search the adb binary in the unzipped content.
        """
        self.logger.info("Download process finished.")
        if not self.d_task.result:
            self.logger.error("Error while downloading the file:" + str(self.d_task.exception))
            self.d_task = None
            return

        adb_path = os.path.join(
            QgsApplication.qgisSettingsDirPath(),
            constants.QGIS_PLUGIN_NAME,
            "adb_binary"
        )

        zip_file = os.path.join(adb_path, "adb.zip")

        with zipfile.ZipFile(zip_file) as zip:
            zip.extractall(adb_path)

        os.remove(zip_file)

        found, path = self.c_manager.find_adb_in_automatic_path()

        if found:
            self.logger.info("Successfully downloaded adb: " + path)
            self.browse_text.setText(path)
            self.c_manager.save_adb_path(path)
            self.custom_path = path

        else:
            path = os.path.join(QgsApplication.qgisSettingsDirPath(), QGIS_PLUGIN_NAME, QGIS_ADB_BINARY_FOLDER)
            self.logger.error("Something when wrong with the installation. The file was downloaded but it couldn't be find."
                              " Look for the file at " + path + " and add it manually.")
        self.d_task = None


    def _browse_action(self):
        """
            Open a browse dialog to get the path of adb binary.
        """
        ruta, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",
            self.browse_text.text(),
            "Todos los archivos (*.*)"
        )
        if ruta:
            self.custom_path = ruta
            self.browse_text.setText(ruta)


    def use_adb_path(self, adb_path):
        """
            Change the adb path for AdbChannel.
        """
        AdbChannel.put_adb_path(adb_path)


    def _accept_action(self):
        """
            Action launched when the dialog accept button is clicked. Get the new config and try to save it.
            If it can be saved then also saves the value of adb binary path, the selection of MTP/ADB and clean
            the device combo.
        """
        new_config = self.conf_text_edit.toPlainText()
        malformed, config_json  = self.json_reader.create_config_from_text(new_config, False)
        if not malformed:
            photo_config = self.photo_layers_edit.toPlainText()
            try:
                photo_config_dict = json.loads(photo_config)
                if not all(isinstance(k, str) and isinstance(v, str) for k, v in photo_config_dict.items()) or \
                    len(photo_config_dict.values()) != len(set(photo_config_dict.values())):
                    self.logger.warning("Json malformed")
                    self.logger.warning("The Photo layers configuration json provided is malformed. Press cancel if you"
                                        " want to reset the configuration state or use"
                                            " a configuration that is not malformed. Check if there are duplicates, this configuration"
                                            " does not allow to duplicate values.")
                    QMessageBox.critical(self, "Json malformed",
                                         tr("The Photo layers configuration json provided is malformed. Press cancel if"
                                            " you want to reset the configuration state or use"
                                            " a configuration that is not malformed. Check if there are duplicates, this configuration"
                                            " does not allow to duplicate values."))
                    return
            except json.decoder.JSONDecodeError:
                self.logger.warning("Json malformed")
                self.logger.warning(
                    "The Photo layers configuration json provided is malformed. Press cancel if you want to reset the"
                    " configuration state or use"
                    " a configuration that is not malformed.")
                QMessageBox.critical(self, "Json malformed",
                                     tr("The Photo layers configuration json provided is malformed. Press cancel if you"
                                        " want to reset the configuration state or use"
                                        " a configuration that is not malformed."))

                return
            self.c_manager.save_config(config_json, True)
            self.photo_conf.set_save_layers_bool(self.save_check_box.isChecked())
            self.photo_conf.save_new_config(photo_config_dict)

            self.custom_path = self.browse_text.text()
            self.c_manager.change_protocol_used(self.adb_or_mtp)
            self.save_custom_adb_path()
            self.c_manager.save_adb_path(self.custom_path)
            if self.adb_or_mtp_changed:
                self.adb_or_mtp_changed = False
                if self.adb_or_mtp:
                    self.logger.info("ADB selected.")
                else:
                    self.logger.info("MTP selected.")
                self.save_protocol_conf()
                self.localsync_plugin.clear_devices_combo()
            self.accept()
        else:
            self.logger.warning("Json malformed")
            self.logger.warning("The Synchronization configuration json provided is malformed. Press cancel if you want"
                                " to reset the configuration state or use"
                                    " a configuration that is not malformed.")
            QMessageBox.critical(self, "Json malformed",
                                 tr("The Synchronization configuration json provided is malformed. Press cancel if you"
                                    " want to reset the configuration state or use"
                                    " a configuration that is not malformed."))


