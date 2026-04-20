from __future__ import annotations
import logging

from PyQt5.QtGui import QPaintEvent
from PyQt5.QtWidgets import QWidget, QMessageBox, QStylePainter, QStyleOptionComboBox

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QComboBox, QStyle
from qgis._core import Qgis
from qgis.core import QgsApplication
from ..constants import QGIS_PLUGIN_NAME
from typing import TYPE_CHECKING

from ..localsync.channels.adb_channel import AdbErrorType

if TYPE_CHECKING:
    from ..local_sync_plugin import SyncListener
from ..localsync.core.sync_engine import SyncEngine
from ..logger.qgis_logger_handler import QgisLoggerHandler
from ..tasks.read_devices import ReadDevices
from ..i18n import tr



class DevicesCombo(QComboBox):

    """
        Controller for the UI combo of devices.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
        :ivar task: current task of request of connected devices.
        :vartype task: QgsTask
        :ivar check_availability: bool that indicates if pc has been checked for ADB/MTP availability.
        :vartype check_availability: bool
    """

    def __init__(self,s_eng: SyncEngine, s_listener: SyncListener, parent: QWidget=None):
        """
            Constructor.
            :param s_eng: SyncEngine for the task to request information about connected devices.
            :param s_listener: Creates messages in the message bar accordingly with the current task.
            :param parent: parent QWidget.
        """

        super().__init__(parent)
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.task = None
        self.check_availability = True
        self.s_eng = s_eng
        self.s_listener = s_listener
        self.loading_show_popup = False



    def showPopup(self):
        """
            Override of the method to open de combobox popup. It checks for availability and create a task to
            request the current connected devices. Prevents the popup from being displayed.
        """

        self.clear()
        available_protocols = {}
        if not self.task and not self.loading_show_popup:
            self.loading_show_popup = True
            if self.check_availability:
                self.s_listener.create_or_update_message_bar(tr("Checking availability and looking for devices..."))
                available_protocols = self.s_eng.supports()
                if "adb" in available_protocols and "mtp" in available_protocols:
                    self.check_availability = not (available_protocols["adb"].available and available_protocols["mtp"].available)
            else:
                self.s_listener.create_or_update_message_bar(tr("Looking for devices..."))

            if available_protocols:
                adb_active = self.s_eng.adb_active
                if adb_active and "adb" in available_protocols and not available_protocols["adb"].available:
                    msg = tr("You have selected ADB protocol, but it is not available.\n\n Reason: ") + available_protocols["adb"].error_type.value
                    msg += self._create_warning_message(adb_active,available_protocols)
                    QMessageBox.warning(None , "ADB error", msg)
                    self.loading_show_popup = False
                    self.logger.warning(msg)
                    self.s_listener.create_or_update_message_bar("Search devices couldn't be completed.",
                                                                 Qgis.Warning, 5000, clear_messages=False)
                    return

            self.task = ReadDevices(self.s_eng)
            self.task.taskCompleted.connect(self.get_devices_response)
            QgsApplication.taskManager().addTask(self.task)


    def _create_warning_message(self, check_adb: bool, availability: dict) -> str:
        if check_adb:
            error_type = availability["adb"].error_type
            if error_type == AdbErrorType.ADB_NOT_FOUND:
                return tr("\n Open the plugin configuration doing click on the blue gears and make sure that the ADB binary path is correctly set.")
        return ""


    def _write_devices_combo_value(self, device):
        if not device.no_data:
            self.logger.info("Device found: %s", device.name)
            self.addItem(device.name + " - " + device.brand + " - " + device.model, device)
        else:
            icon = self.style().standardIcon(getattr(QStyle, "SP_MessageBoxWarning"))
            self.logger.info("Unauthorized device found: {id}".format(id=device.device_id))
            self.addItem(icon, tr("Unauthorized device"))
            self.setItemData(self.count() - 1, tr("Check the device to authorize the connection."), Qt.ToolTipRole)

    # noinspection PyMethodOverriding
    def paintEvent(self, event: QPaintEvent) -> None:
        """
            Override of QPaintEvent. This method is used to paint the placeholder text.
            :param event: QPaintEvent.
        """
        super().paintEvent(event)
        if self.currentIndex() < 0 and self.placeholderText:
            painter = QStylePainter(self)
            opt = QStyleOptionComboBox()
            self.initStyleOption(opt)
            opt.currentText = self.placeholderText
            painter.drawControl(QStyle.CE_ComboBoxLabel, opt)


    def get_devices_response(self):
        """
            Callback for the task to request current connected devices. It populates the combobox with the result of the
            task and finally shows the popup.
        """
        if self.task and self.task.successful:
            result = self.task.result
            self.blockSignals(True)

            self.s_listener.create_or_update_message_bar(tr("Search devices task completed successfully."),
                                                         Qgis.Success, 5000, clear_messages=False)
            if not result:
                self.logger.info("No devices found!")
                self.addItem(tr("No devices found!"), None)
                QMessageBox.warning(self, tr("No devices found"),
                                     tr("Make sure your phone is properly connected to your computer and the <b>ADB debuggin"
                                        " mode</b> is On. See this for more information:<br>{link}")
                                    .format(link= "<a href = 'https://docs.cartodruid.es/es/latest/qgisPlugin/qgis_plugin/'>"
                                                  "https://docs.cartodruid.es/es/latest/qgisPlugin/qgis_plugin/</a>")
                                        )
            else:
                self.logger.info("Devices found!")
                self.addItem("", None)
                for device in result:
                    if device:
                        self._write_devices_combo_value(device)
                super().showPopup()
        else:
            self.task = None
            self.s_eng.supports()
            self.s_listener.create_or_update_message_bar(tr("Something went wrong!. Check the log."),
                                                         Qgis.Critical, clear_messages=False)
        self.task = None
        self.loading_show_popup = False
        self.blockSignals(False)


