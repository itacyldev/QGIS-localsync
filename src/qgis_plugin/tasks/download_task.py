import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QMessageBox

from qgis.core import QgsTask, QgsApplication
import requests

from ..constants import QGIS_PLUGIN_NAME
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
    ssl_error = pyqtSignal(str, str)



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
        except requests.exceptions.SSLError as e:
            error="SSL certificate verification failed. If you are behind a corporate proxy, you will have to download and configura adb manually."
            translate_error = tr("SSL certificate verification failed. If you are behind a corporate proxy, you will have to download and configura adb manually. More information at:{path}").format(path = "<a href = 'https://docs.cartodruid.es/es/latest/qgisPlugin/qgis_plugin/'>https://docs.cartodruid.es/es/latest/qgisPlugin/qgis_plugin/</a>")
            self.logger.error(error)
            self.ssl_error.emit(error, translate_error)
            self.result = False
            raise RuntimeError(error) from e
        except Exception as e:
            self.logger.error("An error happened: " + str(e))
            self.exception = e
            self.result = False
            return False

