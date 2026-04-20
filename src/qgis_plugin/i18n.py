from qgis.PyQt.QtCore import QCoreApplication
from .constants import QGIS_PLUGIN_NAME

def tr(message):
    return QCoreApplication.translate(QGIS_PLUGIN_NAME, message)