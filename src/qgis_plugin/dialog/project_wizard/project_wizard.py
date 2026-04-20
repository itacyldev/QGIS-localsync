from __future__ import annotations

import json
import logging
import os

from qgis.PyQt.QtCore import QItemSelectionModel, Qt
from qgis.PyQt.QtGui import QStandardItemModel
from qgis.PyQt.QtWidgets import QProgressBar, QWizard, QMessageBox, QListView

from qgis.PyQt import uic
from qgis._core import QgsProject
from .project_wizard_data import ProjectWizardData
from .wizard_pages.add_layers import AddLayers
from .wizard_pages.photo_layer import PhotoLayer
from ...configuration.configuration_manager import ConfigurationManager
from ...configuration.photo_layers_configuration import PhotoLayersConfiguration
from ...constants import QGIS_PLUGIN_NAME, CARTODRUID_CONNECT_CONFIG_BOX, CARTODRUID_CONNECT_IMAGE_BOX, \
    CARTODRUID_CONNECT_DATA_BOX, CARTODRUID_CONNECT_DATA_LIST, CARTODRUID_CONNECT_PROJECT, QGIS_SCOPE_NAME, \
    QGIS_PROJECT_CONFIG_KEY, CARTODRUID_CONNECT_DATA_LIST_FULL, CARTODRUID_CONNECT_PHOTO_SAVE_LAYERS
from ...i18n import tr
from ...localsync.core.sync_engine import SyncEngine
from ...localsync.device.device_manager import DeviceManager
from ...localsync.project.project_manager import ProjectManager, ProjectData
from ...logger.qgis_logger_handler import QgisLoggerHandler
from .wizard_pages.project_finder import ProjectFinder
from .wizard_pages.file_selector import FileSelector

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...local_sync_plugin import SyncListener, LocalSyncPlugin

from ...tasks.search_projects import SearchProjects

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'project_wizard.ui'))


class ProjectWizard(QWizard, FORM_CLASS):

    """
    Wizard manager. Contains the data needed for the pages and manages the state save of the wizard and the page controllers and order.
    :ivar logger: logger of the application.
    :vartype logger: logging.Logger
    :ivar current_options: current state of the wizard. It is retained between executions.
    :vartype current_options: ProjectWizardData
    :ivar device: current device that will be used for the operations of the wizard.
    :vartype device: DeviceManager
    :ivar start_second_page: indicates whether start from the second page of the wizard or not.
    :vartype start_second_page: bool
    :ivar initialize_first_page: indicates whether initialise the first page or not.
    :vartype initialize_first_page: bool
    """

    def __init__(self, localsync_plugin: LocalSyncPlugin, c_manager: ConfigurationManager, p_manager: ProjectManager, s_eng: SyncEngine,
                 s_listener: SyncListener, photo_configuration: PhotoLayersConfiguration):

        """
        Constructor.
        :param localsync_plugin: reference of the plugin main class.
        :param c_manager: reference to the configuration manager used by the application to read, save and change the configuration of the plugin.
        :param p_manager: reference to the project manager used by the application to read the Cartodruid projects in the device.
        :param s_eng: reference to the synchronization engine used by the application to download/upload files from/to the device.
        :param s_listener: reference to the synchronization listener used by the application to create messageBars on the main thread.
        """

        super().__init__()
        self.setupUi(self)
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

        self.plugin = localsync_plugin
        self.c_manager = c_manager
        self.p_manager = p_manager
        self.current_options = ProjectWizardData()
        self.photo_configuration = photo_configuration
        self.device = None
        self.s_eng = s_eng
        self.s_listener = s_listener
        self.start_second_page = False

        ids = self.pageIds()

        layouts = []
        titles = []
        subtitles = []
        for page_id in ids:
            page = self.page(page_id)
            layouts.append(page.layout())
            titles.append(page.title())
            subtitles.append(page.subTitle())

        for page_id in ids:
            self.removePage(page_id)

        p1 = ProjectFinder(self.project_view)
        p1.setLayout(layouts[0])
        p1.setTitle(titles[0])
        p1.setSubTitle(subtitles[0])
        self.progress1 = self.create_progress_bar()
        p1.layout().addWidget(self.progress1)
        self.page1_id = self.addPage(p1)

        p2 = FileSelector(self.config_box,self.image_box,self.data_box, self.data_view)
        p2.setLayout(layouts[1])
        p2.setTitle(titles[1])
        p2.setSubTitle(subtitles[1])
        self.progress2 = self.create_progress_bar()
        p2.layout().addWidget(self.progress2)
        self.page2_id = self.addPage(p2)

        p3 = AddLayers()
        self.addPage(p3)

        p4 = PhotoLayer()
        self.addPage(p4)
        self.save_photo_layers = False

        self.new_project = False

        self.initialize_first_page = True


    def exec(self):
        """
            Starts the wizard on the second page or on the first page.
        """

        if self.start_second_page:
            self.start_second_page = False
            self.setStartId(self.page1_id)
        else:
            self.restart()
        super().exec()

    def reselect_last_selection(self, view:QListView, items_to_search: list):
        """
            Select on the QListView the items that match between the view model and the items_to_search list.
            :param view: QListView where the items will be selected.
            :param items_to_search: list of items that will be searched in the QListView
        """
        model = view.model()
        if self.new_project:
            for row in range(model.rowCount()):
                item = model.item(row)
                view.selectionModel().select(model.indexFromItem(item),
                                             QItemSelectionModel.SelectionFlag.Select)
        else:
            for row in range(model.rowCount()):
                item = model.item(row)
                if item.data(Qt.UserRole) in items_to_search:
                    view.selectionModel().select(model.indexFromItem(item),
                                                           QItemSelectionModel.SelectionFlag.Select)


    def create_progress_bar(self) -> QProgressBar:
        """
            Creates an infinite progress bar and return it.
            :return: progress bar hidden by default.
        """
        progress = QProgressBar(None)
        progress.setMinimum(0)
        progress.setMaximum(0)
        progress.setTextVisible(False)
        progress.hide()
        return progress



    def initialise(self, device: DeviceManager, second_page: bool):
        """
            Initialise the wizard with the device that will be used for the operations. It also can set the start page to be
            the second page.
            :param device: reference to the device that will be used for the operations of the wizard.
            :param second_page: boolean that indicates if the wizard should start on the second page or not.
        """

        project = QgsProject.instance()
        value, ok = project.readEntry(
            QGIS_SCOPE_NAME,
            QGIS_PROJECT_CONFIG_KEY
        )

        try:
            if ok:
                self.logger.info("ProjectWizardData loaded successfully.")
                config = json.loads(value)
                self.current_options = ProjectWizardData.from_dict(config)
            else:
                self.logger.info("ProjectWizardData not found.")
        except json.JSONDecodeError:
            self.logger.warning("Json malformed")
            QMessageBox.warning(None, "Json malformed",
                                tr("The project connect configuration couldn't be retrieved."))

        self.device = device
        self.start_second_page = second_page
        if second_page:
            self.initialize_first_page = False
            self.setStartId(self.page2_id)
            self.restart()

        self.save_photo_layers = self.photo_configuration.get_save_layers_bool()



    def save_carto_project_selections(self):
        """
            Save the state of the wizard on an entry in the current QGIS project.
        """
        project = QgsProject.instance()
        if self.current_options and self.current_options.can_convert_to_dict():
            project.writeEntry(
                QGIS_SCOPE_NAME,
                QGIS_PROJECT_CONFIG_KEY,
                json.dumps(self.current_options.to_dict())
            )
        self.photo_configuration.set_save_layers_bool(self.save_photo_layers)
        self.new_project = False

    def reject(self):
        """
            Cancel button overwrite. Executes the on_cancel method on the current wizard page.
        """
        self.new_project = False
        current_page = self.currentPage()
        if hasattr(current_page, 'on_cancel'):
            current_page.on_cancel()
        super().reject()
