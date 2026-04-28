import logging
import os
import platform
from pathlib import Path

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from qgis.core import QgsTask, QgsApplication
import requests

from ..constants import QGIS_PLUGIN_NAME, WINDOWS_ADB_DOWNLOAD_URL, LINUX_ADB_DOWNLOAD_URL
from ..i18n import tr
from ..logger.qgis_logger_handler import QgisLoggerHandler


class DownloadTask(QgsTask):

    """
        Task that to download a file from internet.
        :ivar exception: exception raised by the task.
        :vartype exception: Exception
        :ivar result: True if there is a result, False otherwise.
        :vartype result: bool
    """
    download_adb_error = pyqtSignal(str, str)



    def __init__(self, url: str, output_path: str):
        """
            Constructor.
            :param url: url to download from.
            :param output_path: path to save the downloaded file.
        """
        super().__init__("", QgsTask.CanCancel)
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.url = url
        self.output_path = output_path
        self.exception = None
        self.result = False


    def error_response(self):
        op_sys = platform.system()
        link = WINDOWS_ADB_DOWNLOAD_URL
        path = Path(self.output_path).parent.as_posix()
        carto_link = "https://docs.cartodruid.es/es/latest/qgisPlugin/qgis_plugin/"
        adb = "adb.exe"
        if op_sys == "Linux":
            link = LINUX_ADB_DOWNLOAD_URL
            adb = "adb"
        error = "An error has occurred during the download, you will need to download the ADB manually."
        translate_error = tr("An error has occurred during the download, you will need to download the ADB manually.<br> Download the file from:<br>{link}<br><br> Unzip it and copy the contents to:<br>{path}.<br><br>You will have to configure the {adb} path with the {adb} found inside the zip in the plugin configuration window.<br>More information at: {carto_link}").format(
            link=f"<a href = '{link}'>{link}</a>", path=path, carto_link=f"<a href = '{carto_link}'>{carto_link}</a>", adb = adb)
        self.logger.error(error)
        self.download_adb_error.emit(error, translate_error)
        self.result = False


    def run(self):
        """
            Download the file to the designated location and indicates its progress.
        """
        try:
            self.logger.info("Sending download request...")
            response = requests.get(self.url, stream=True, timeout=5)
            self.logger.info("Response received.")
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            self.logger.info("Downloading in file: " + self.output_path)
            with open(self.output_path, 'wb') as f:
                self.logger.info("Starting download...")
                for chunk in response.iter_content(chunk_size=4096):
                    if self.isCanceled():
                        self.logger.info("Download cancelled.")
                        return False

                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = (downloaded / total_size) * 100
                            self.setProgress(progress)
            self.result = True
            self.logger.info("Download completed.")
            return True
        except Exception as e:
            self.logger.error("An error happened: " + str(e))
            self.error_response()
            self.exception = e
            self.result = False
            return False

