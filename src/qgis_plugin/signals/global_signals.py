from qgis.PyQt.QtCore import QObject, pyqtSignal

class ContinueAfterConfigCheck(QObject):
    confirmationReady = pyqtSignal(bool)

class LaunchCartoProjectConfiguration2ndPage(QObject):
    launchCartoConfig2ndPage = pyqtSignal(bool)

cac_check = ContinueAfterConfigCheck(None)

lcpc2p = LaunchCartoProjectConfiguration2ndPage()


