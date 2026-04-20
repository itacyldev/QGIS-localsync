from __future__ import annotations
import logging
import traceback
from pathlib import Path

from qgis._core import Qgis
from qgis.core import QgsTask
from ..constants import QGIS_PLUGIN_NAME
from typing import TYPE_CHECKING

from ..localsync.project.project_manager import ProjectData

if TYPE_CHECKING:
    from ..local_sync_plugin import SyncListener
from ..localsync.core.sync_engine import SyncEngine
from ..localsync.device.device_manager import DeviceManager
from ..logger.qgis_logger_handler import QgisLoggerHandler
from ..localsync.host.host_manager import HostManager
from ..localsync.project.sync_mapper_reader import SyncMapperData
from ..i18n import tr

class ReadConfigFileCarto(QgsTask):

    """
        Task for downloading/uploading files between pc and a device.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
        :ivar canceled: bool that indicate if the task has been cancelled.
        :vartype canceled: bool
    """

    def __init__(self, s_eng: SyncEngine, project: ProjectData, device: DeviceManager, save_path:str, s_listener:SyncListener):
        """
            Constructor.
            :param s_eng: used to call the download/upload functions.
            :param project: project from where the Cartodruid configuration will be downloaded.
            :param device: device from where the Cartodruid configuration will be downloaded.
            :param save_path: path to where the Cartodruid configuration will be downloaded.
            :param s_listener: used to create messages bar using the main thread.
        """
        super().__init__(None, QgsTask.Flag.Silent)
        self.s_eng = s_eng
        self.project = project
        self.device = device
        self.host_save_path = save_path
        self.device.path_to_project = (Path(project.path) / "config").as_posix()
        self.s_listener = s_listener
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.canceled = False


    def run(self):
        """
            Downloads the Cartodruid project configuration file into a special folder in QGIS configuration files.
        """
        try:
            self.logger.info("Starting cartodruid configuration download...")
            mapper = SyncMapperData(self.host_save_path, self.device.path_to_project,
                                    ["crtdrdLayers.xml"], [])
            host = HostManager("", mapper.source)
            ft_successful = self.s_eng.file_transport(self.device, host, mapper.includes, mapper.excludes, True)
            if self.canceled:
                self.logger.warning("Process canceled by the user.")
                self.s_listener.create_or_update_message_bar(tr("Process canceled by the user."), Qgis.Warning,
                                                             clear_messages=False)
                self.canceled = False
                return False
            if not ft_successful:
                self.s_listener.create_or_update_message_bar(tr("Something went wrong. Check the log."), Qgis.Critical,
                                                             clear_messages=False)
                return False

            self.logger.info("Configuration file downloaded correctly.")
            return True
        except Exception:
            self.s_eng.supports()
            self.s_listener.create_or_update_message_bar(tr("Error while trying to load the files,"
                                                            " check log."), Qgis.Critical, clear_messages=False)
            self.logger.error(traceback.format_exc())
            return False




    def cancel(self):
        """
            Cancel this task.
        """
        self.s_eng.cancel_load_process()
        self.canceled = True