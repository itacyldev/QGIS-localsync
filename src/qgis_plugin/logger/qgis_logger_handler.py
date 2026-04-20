# logger.py
from __future__ import annotations

import os
import traceback

from PyQt5.QtCore import pyqtSignal, pyqtSlot, QObject

from qgis.core import QgsMessageLog, Qgis
import logging
from qgis.PyQt import QtWidgets
from qgis.core import QgsApplication
from logging.handlers import RotatingFileHandler

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..dialog.messages_dialog import MessagesDialog


class QgisLoggerHandler:
    """
        Logs messages into a file, a dialog and to the message registry in QGIS.
        :ivar logger: custom loggger with custom handlers that make it possible to write in different places.
        :vartype  logger: logging.Logger
    """
    def __init__(
        self,
        plugin_name: str,
        filename: str="localsync.log",
        level: int=logging.INFO,
        rotate: bool=True,
        max_bytes: int=2 * 1024 * 1024,
        backup_count: int=5
    ):
        """
        Constructor.
        :param plugin_name: name to get the logger.
        :param filename: name of the file where the messages will be written.
        :param level: logging level.
        :param rotate: whether to rotate the file logs.
        :param max_bytes: maximum number of bytes to write per file log
        :param backup_count: max number of file logs before they will get overwritten.
        """
        plugin_name = plugin_name.replace(" ", "_")
        self.logger = logging.getLogger(plugin_name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        log_dir = os.path.join(
            QgsApplication.qgisSettingsDirPath(),
            plugin_name,
            "logs"
        )

        os.makedirs(log_dir, exist_ok=True)

        log_path = os.path.join(log_dir, filename)

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )

        self._ensure_qgis_handler(formatter)
        self._ensure_file_handler(
            log_path, formatter, rotate, max_bytes, backup_count
        )


    def _ensure_qgis_handler(self, formatter: logging.Formatter):
        """
            Add QGIS handler to the logger, so the saved messages will appear in the message registry and the message dialog.
            :param formatter: format of the message.
        """
        for h in self.logger.handlers:
            if getattr(h, "_handler_id", None) == "qgis":
                return

        h = QgisLogHandler()
        h._handler_id = "qgis"
        h.setFormatter(formatter)
        self.logger.addHandler(h)



    def _ensure_file_handler(self, log_path: str, formatter: logging.Formatter, rotate: bool, max_bytes: int,
                             backup_count: int):
        """
            Add file handler to the logger, so the saved messages will on the log files.
            :param log_path: path of the log file.
            :param formatter: format of the message.
            :param rotate: whether to rotate the file logs.
            :param max_bytes: maximum number of bytes to write per file log.
            :param backup_count: max number of file logs before they will get overwritten.
        """
        for h in self.logger.handlers:
            if getattr(h, "_handler_id", None) == "file":
                return

        if rotate:
            h = RotatingFileHandler(
                log_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8"
            )
        else:
            h = logging.FileHandler(log_path, encoding="utf-8")

        h._handler_id = "file"
        h.setFormatter(formatter)
        self.logger.addHandler(h)


    def get_logger(self):
        """
            Return the logger.
            :return: logger of the application.
        """
        return self.logger



class QgisLogHandler(logging.Handler):

    """
    Handler for the QGIS Logger to add the messages to the message registry and the message dialog.
    :ivar _handler_id: id of the handler.
    :vartype _handler_id: str
    :ivar dialog: reference to the message dialog.
    :vartype dialog: MessagesDialog
    :ivar emit_on_dialog_signal: Signal emitter to write a message in the message dialog.
    :vartype emit_on_dialog_signal: PYQT_SIGNAL
    :ivar dialog_logger: reference to the writer for dialog messages.
    :vartype dialog_logger: DialogLogger
    """

    _handler_id = "qgis"
    dialog = None

    emit_on_dialog_signal = pyqtSignal(logging.LogRecord, dict, str, QtWidgets.QDialog)

    def __init__(self):
        """Constructor."""
        self.dialog_logger = DialogLogger()
        self.dialog_logger.log_signal.connect(
            self.dialog_logger.emit_on_dialog
        )
        super().__init__()

    def set_dialog(self, dialog: MessagesDialog):
        """
        Set the dialog object.
        :param dialog: dialog object.
        """
        self.dialog = dialog


    def emit(self, record: logging.LogRecord):
        """
        Emit a record to the message registry and message dialog if available.
        :param record: record to emit.
        """
        msg = self.format(record)

        level_map = {
            logging.DEBUG: Qgis.Info,
            logging.INFO: Qgis.Info,
            logging.WARNING: Qgis.Warning,
            logging.ERROR: Qgis.Critical,
            logging.CRITICAL: Qgis.Critical,
        }
        QgsMessageLog.logMessage(
            msg,
            record.name,
            level_map.get(record.levelno, Qgis.Info)
        )

        if self.dialog and self.dialog_logger:
            self.dialog_logger.log_signal.emit(record, level_map, msg, self.dialog)


class DialogLogger(QObject):

    """
        Class that writes messages into the message dialog using the main thread of QGIS.
    """
    log_signal = pyqtSignal(logging.LogRecord, dict, str, QtWidgets.QDialog)


    @pyqtSlot(logging.LogRecord, dict, str, QtWidgets.QDialog)
    def emit_on_dialog(self, record: logging.LogRecord, level_map: dict, msg: str, dialog: QtWidgets.QDialog):
        """
            Writes a message into the message dialog, using the main thread of QGIS.
            :param record: record to emit with the level to emit.
            :param level_map: map with the matches for log levels.
            :param msg: message to write in the dialog.
            :param dialog: reference to the message dialog object.
        """
        qgis_level = level_map.get(record.levelno, Qgis.Info)
        qgis_level_text = {
            Qgis.Info: "info",
            Qgis.Warning: "warning",
            Qgis.Critical: "critical",
        }.get(qgis_level, "INFO")

        dialog.notify_msg(qgis_level_text, msg)