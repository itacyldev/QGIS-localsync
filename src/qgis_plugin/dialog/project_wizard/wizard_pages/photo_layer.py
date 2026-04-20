import os
import traceback
from pathlib import Path

from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QStandardItemModel
from PyQt5.QtWidgets import QCheckBox, QListWidgetItem, QListWidget

from qgis import processing
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QWizardPage, QMessageBox, QListView

from qgis.PyQt.Qt import Qt
from qgis._core import QgsApplication, QgsProject, QgsLayerTreeLayer, QgsEditorWidgetSetup, QgsVectorLayer
from ....configuration.photo_layers_configuration import PhotoLayersConfiguration
from ....constants import WIZARD_PHOTO_LAYERS_HTML_NOTICE
from ....i18n import tr
from ....tasks.search_projects import SearchProjects


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '..', 'photo_layer_page.ui'))

class PhotoLayer(QWizardPage, FORM_CLASS):
    """
        Manages the photo layer page of the Wizard. Read the pictures folder downloaded in a previous step and
        populates a QListView where the user can select the image folders that will be used to create new layers.
        :ivar pictures_folder: stores the task that manages the reading of the projects from the device.
        :vartype pictures_folder: str
        :ivar progress: progress bar of the page.
        :vartype progress: QProgressBar
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: QgisLoggerHandler
    """

    def __init__(self):
        super().__init__(None)
        self.setupUi(self)
        self.pictures_folder = os.path.join(
            Path(QgsProject.instance().fileName()).parent.as_posix(),
            "cartodruid",
            "pictures"
        )
        self.progress = None


    def initializePage(self):
        """
            Populate the list view with the folders found inside pictures.
        """
        self.pictures_folder = os.path.join(
            Path(QgsProject.instance().fileName()).parent.as_posix(),
            "cartodruid",
            "pictures"
        )
        if not self.progress:
            self.progress = self.wizard().create_progress_bar()
            self.layout().addWidget(self.progress)

        if Path(self.pictures_folder).exists():
            picture_folders = [f for f in os.listdir(self.pictures_folder) if os.path.isdir(os.path.join(self.pictures_folder, f))]
        else:
            picture_folders = []
        self.photo_view.clear()
        self.save_check.setChecked(self.wizard().save_photo_layers)
        if picture_folders:
            for folder in picture_folders:
                check_box = QListWidgetItem(folder)
                check_box.setFlags(check_box.flags() | Qt.ItemIsUserCheckable)
                check_box.setCheckState(Qt.Checked if folder in self.wizard().current_options.photo_selected_folders else Qt.Unchecked)
                self.photo_view.addItem(check_box)


    def validatePage(self):
        """
        Create the new layers from the selected in the QListView by the user.
        """
        self.wizard().photo_configuration.change_save_config_value(self.save_check.checkState() == Qt.Checked)
        self.wizard().save_photo_layers = self.save_check.checkState() == Qt.Checked
        self.wizard().current_options.photo_selected_folders = []
        self.wizard().photo_configuration.restart_config()
        if self.photo_view.count() > 0:
            self.progress.show()
            for i in range(self.photo_view.count()):
                item = self.photo_view.item(i)
                if item.checkState() == Qt.Checked:
                    self.wizard().current_options.photo_selected_folders.append(item.text())
                    self.wizard().photo_configuration.add_to_config(item.text(), item.text())

            self.wizard().photo_configuration.create_or_update_photo_layers()
            self.progress.hide()
        self.wizard().save_carto_project_selections()
        return True