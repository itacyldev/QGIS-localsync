import logging
import traceback

from qgis.core import QgsTask
from ..constants import QGIS_PLUGIN_NAME
from ..localsync.core.sync_engine import SyncEngine
from ..logger.qgis_logger_handler import QgisLoggerHandler
from ..i18n import tr


class ReadDevices(QgsTask):

    """
        Task for reading the connected devices to the pc.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
        :ivar result: contains the result of the request for connected devices.
        :vartype result: List
        :ivar successful: True if there is a result, False otherwise.
        :vartype successful: bool
    """

    def __init__(self, s_eng: SyncEngine):
        """
            Constructor.
            :param s_eng: used to make request about connected devices.
        """
        super().__init__(None, QgsTask.Flag.Silent)
        self.s_eng = s_eng
        self.result = None
        self.successful = False
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

    def run(self):
        """
            Main process of the task. Request from SyncEngine what devices are connected to the pc.
        """
        try:
            self.logger.info("Searching for devices...")
            self.result, ok = self.s_eng.discover_devices()
            self.successful = ok
            return True
        except Exception:
            self.logger.error(traceback.format_exc())
            self.successful = False
            return False