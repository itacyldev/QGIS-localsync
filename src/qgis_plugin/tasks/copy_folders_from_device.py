from __future__ import annotations
import logging

from qgis._core import QgsTask
from ..constants import QGIS_PLUGIN_NAME
from ..i18n import tr

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..local_sync_plugin import SyncListener
from ..localsync.core.sync_engine import SyncEngine
from ..localsync.device.device_manager import DeviceManager
from ..localsync.host.host_manager import HostManager
from ..localsync.project.sync_mapper_reader import SyncMapperData
from ..logger.qgis_logger_handler import QgisLoggerHandler


class CopyFoldersFromDevice(QgsTask):

    """
        Task for downloading/uploading files between pc and a device.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
        :ivar result: boolean that indicates if the task was successful
        :vartype result: bool
        :ivar exception: Contains the exception threw during the task process
        :vartype exception: Exception
    """

    def __init__(self, s_eng: SyncEngine, config: list[dict], device: DeviceManager, s_listener:SyncListener):
        """
            Constructor.
            :param s_eng: used to call the download/upload functions.
            :param config: configuration dictionary.
            :param device: device from whom files will be downloaded/uploaded.
            :param s_listener: used to create messages bar using the main thread.
        """
        super().__init__(None, QgsTask.Flag.Silent)
        self.s_eng = s_eng
        self.config = config
        self.device = device
        self.exception = None
        self.s_listener = s_listener
        self.result = False
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.canceled = False
        self.key_filter_word = ["pictures", "values", "config", "data"]



    def convert_filters(self, mapper: SyncMapperData) -> SyncMapperData:
        new_includes = []
        for item in self.key_filter_word:
            for map in mapper.includes:
                if item in map:
                    if item == "pictures":
                        new_includes.append("*/"+item+"/*")
                    new_includes.append("*/"+item)
        mapper.includes = new_includes
        return mapper



    def run(self):
        """
            Creates the folder structure of config sources given in the designed destinations.
        """
        try:
            self.exception = None
            self.result = False
            accumulated_result = True
            for config in self.config:
                mapper = SyncMapperData(config["source"], config["destination"],
                                        config["includes"], config["excludes"])
                mapper = self.convert_filters(mapper)
                host = HostManager("", mapper.source)
                self.device.path_to_project = config["destination"]
                accumulated_result = accumulated_result and self.s_eng.recreate_device_structure(self.device, host, mapper.includes, mapper.excludes)
            self.result = accumulated_result
            return accumulated_result
        except Exception as e:
            self.exception = e
            return False
