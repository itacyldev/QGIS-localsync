from __future__ import annotations
import logging
import threading
import traceback

from qgis._core import Qgis
from qgis.core import QgsTask
from ..constants import QGIS_PLUGIN_NAME
from typing import TYPE_CHECKING

from ..events.project_configuration_changed import ProjectConfigurationChanged
from ..signals.global_signals import cac_check

if TYPE_CHECKING:
    from ..local_sync_plugin import SyncListener
from ..localsync.core.sync_engine import SyncEngine
from ..localsync.device.device_manager import DeviceManager
from ..logger.qgis_logger_handler import QgisLoggerHandler
from ..localsync.host.host_manager import HostManager
from ..localsync.project.sync_mapper_reader import SyncMapperData
from ..i18n import tr

class LoadFiles(QgsTask):

    """
        Task for downloading/uploading files between pc and a device.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
        :ivar canceled: bool that indicate if the task has been cancelled.
        :vartype canceled: bool
    """

    def __init__(self, s_eng: SyncEngine, config: list[dict], device: DeviceManager, pull:bool, s_listener:SyncListener):
        """
            Constructor.
            :param s_eng: used to call the download/upload functions.
            :param config: configuration dictionary.
            :param device: device from whom files will be downloaded/uploaded.
            :param pull: whether to download (True) or upload (False) files.
            :param s_listener: used to create messages bar using the main thread.
        """
        super().__init__(None, QgsTask.Flag.Silent)
        self.s_eng = s_eng
        self.config = config
        self.device = device
        self.pull = pull
        self.s_listener = s_listener
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.canceled = False
        self.wait_check_project_config = threading.Event()
        self.cancel_before_start = False


    """
        def add_sub_path(self, conf_source, conf_des, sub_path, pull):
            source_path = Path(conf_source)
            des_path = Path(conf_des)
            sub_path = Path(sub_path)
            if pull:
                des_path = des_path / sub_path
                if sub_path.parent != Path("."):
                    source_path = source_path / sub_path.parent
            else:
                source_path = source_path / sub_path
                if sub_path.parent != Path("."):
                    des_path = des_path / sub_path.parent
            return [source_path.as_posix(), des_path.as_posix()]
    """

    def run(self):
        """
            Download/upload main process. Gives the SyncEngine what is necessary to start downloading/uploading files and
            create message bars accordingly.
        """
        try:
            ft_successful = True
            msg = tr("Files uploaded successfully.")
            if self.pull:
                msg = tr("Files downloaded successfully.")
                self.s_listener.create_or_update_message_bar(tr("Downloading files from the device."))
            else:
                self.s_listener.create_or_update_message_bar(tr("Uploading files to the device."))
            for config in self.config:
                mapper = SyncMapperData(config["source"], config["destination"],
                                        config["includes"], config["excludes"])
                host = HostManager("", mapper.source)
                self.device.path_to_project = config["destination"]
                ft_successful = self.s_eng.file_transport(self.device, host, mapper.includes, mapper.excludes, self.pull)
                if self.canceled:
                    self.logger.warning("Process canceled by the user.")
                    self.s_listener.create_or_update_message_bar(tr("Process canceled by the user."), Qgis.Warning, clear_messages=False)
                    break

            self.canceled = False
            if not ft_successful:
                self.s_listener.create_or_update_message_bar(tr("Something went wrong. Check the log."), Qgis.Critical, clear_messages=False)
                return False
            if self.config:
                self.s_listener.create_or_update_message_bar(msg, Qgis.Success, 5000, clear_messages=False)
                return True
            else:
                self.s_listener.create_or_update_message_bar(tr("Search paths in configuration was empty."
                                                             " No files where transported."), Qgis.Warning, 5000, clear_messages=False)
                self.logger.warning("Search paths in configuration was empty. No files where transported.")
                return False
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