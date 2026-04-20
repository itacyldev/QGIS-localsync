from __future__ import annotations
import logging
import traceback

from qgis.core import QgsTask
from ..constants import QGIS_PLUGIN_NAME
from ..localsync.project.project_manager import ProjectManager
from ..logger.qgis_logger_handler import QgisLoggerHandler
from ..i18n import tr

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..local_sync_plugin import SyncListener


class SearchProjects(QgsTask):

    """
        Task for search Cartodruid projects in a connected device.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
    """

    def __init__(self, p_manager: ProjectManager, device_id: str, s_listener: SyncListener):
        """
            Constructor.
            :param p_manager: used to request the search of projects and get the results.
            :param device_id: the id of the device to connect to.
            :param s_listener: used to create message bars according to the current task.
        """
        super().__init__(flags = QgsTask.Flag.CanCancel)
        self.p_manager = p_manager
        self.device_id = device_id
        self.s_listener = s_listener
        self.result = []
        self.exception = ""
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()


    def run(self):
        """
            Main process of the task. Request from ProjectManager what projects are present in the installation of
            Cartodruid in the current device.
        """
        try:
            self.s_listener.create_or_update_message_bar(tr("Searching for projects on device."))
            self.result = self.p_manager.list_projects(self.device_id)
            return True
        except Exception as e:
            self.exception = e
            return False