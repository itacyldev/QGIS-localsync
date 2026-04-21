import json
import os
import traceback
from pathlib import Path
from xml.etree.ElementTree import Element

from PyQt5.QtCore import QItemSelectionModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QWizardPage, QCheckBox, QListView, QMessageBox, QWizard
import xml.etree.ElementTree as ET

from qgis.PyQt.Qt import Qt
from qgis._core import QgsApplication, Qgis, QgsProject
from ....configuration.xml_reader import XMLReader
from ....constants import QGIS_PLUGIN_NAME, CARTODRUID_CONFIG_NAME, QGIS_SCOPE_NAME, QGIS_CONFIG_KEY, \
    QGIS_PROJECT_CONFIG_KEY
from ....i18n import tr
from ....localsync.project.sync_mapper_reader import SyncMapperData
from ....tasks.copy_folders_from_device import CopyFoldersFromDevice
from ....tasks.load_files import LoadFiles
from ....tasks.read_config_file_carto import ReadConfigFileCarto


class FileSelector(QWizardPage):

    """
    Manages the 2rd page of the Cartodruid Project Wizard. Let the user select what files will be added to the synchronization, changing the configuration of the
    plugin and making a download of the files before going to the next page.
    :ivar s_task: stores the download Cartodruid configuration task.
    :vartype s_task: QTask
    :ivar d_task: stores the download files from device task.
    :vartype s_task: QTask
    :ivar carto_conf_pc_dir: path where the Cartodruid configuration will be stored in the pc.
    :vartype carto_conf_pc_dir: str
    :ivar _download_process_finished: indicates whether the download process has finished.
    :vartype _download_process_finished: bool
    :ivar data_list_full:
    """


    def __init__(self, config_box: QCheckBox, image_box: QCheckBox, data_box: QCheckBox, data_view: QListView):

        """
        Constructor.
        :param config_box: reference to the checkbox used to select the configuration files.
        :param image_box: reference to the checkbox used to select the image files.
        :param data_box: reference to the checkbox used to select the data files.
        :param data_view: reference to the list view where the data files will be listed to select them.
        """

        super().__init__()
        self.config_box = config_box
        self.image_box = image_box
        self.data_box = data_box
        self.data_view = data_view
        self.config_box.stateChanged.connect(self.completeChanged.emit)
        self.image_box.stateChanged.connect(self.completeChanged.emit)
        self.data_box.stateChanged.connect(self.completeChanged.emit)
        self.data_box.stateChanged.connect(self.change_data_view_state)
        self.s_task = None
        self.d_task = None
        self.c_task = None
        self.carto_conf_pc_dir = ""
        self.data_view.setEnabled(False)
        self._download_process_finished = False
        self.data_list_full = []


    def change_data_view_state(self):
        """
        Changes the enable state of the data_view depending on data_box.
        """
        self.data_view.setEnabled(self.data_box.isChecked())


    def initial_configuration(self):
        """
        Set the initial state for the checkBoxes.
        """
        self.config_box.setEnabled(True)
        self.image_box.setEnabled(True)
        self.data_box.setEnabled(True)

        if self.wizard().new_project:
            self.config_box.setChecked(True)
            self.image_box.setChecked(True)
            self.data_box.setChecked(True)
        else:
            self.config_box.setChecked(self.wizard().current_options.config_box_selected)
            self.image_box.setChecked(self.wizard().current_options.image_box_selected)
            self.data_box.setChecked(self.wizard().current_options.data_box_selected)



    def initializePage(self):

        """
            Initialize the state of the checkboxes and launches the download cartodruid configuration task.
            Managed by QGIS, it is launched when the page is loaded.
        """
        self.initial_configuration()
        self.carto_conf_pc_dir = os.path.join(
            QgsApplication.qgisSettingsDirPath(),
            QGIS_PLUGIN_NAME,
            "conf",
            self.wizard().current_options.get_project_selected().project_name
        )
        os.makedirs(self.carto_conf_pc_dir, exist_ok=True)
        if not self.s_task:
            self.s_task = ReadConfigFileCarto(self.wizard().s_eng, self.wizard().current_options.get_project_selected(),
                                              self.wizard().device, self.carto_conf_pc_dir, self.wizard().s_listener)
            self.wizard().logger.info("Looking for data files in cartodruid project...")
            self.s_task.taskCompleted.connect(self._downloaded_conf_completed)
            self.s_task.taskTerminated.connect(self._downloaded_conf_terminated)
            QgsApplication.taskManager().addTask(self.s_task)
            self.wizard().progress2.show()


    def _downloaded_conf_completed(self):

        """
            This method is executed after a successful end of the download cartodruid configuration task.
            Populates the data_view list and select the files selected on a previous execution of the wizard for this Cartodruid project.
        """

        if self.s_task:
            self.data_list_full = []
            model = QStandardItemModel()
            root = XMLReader.safe_parse_xml((Path(self.carto_conf_pc_dir)/CARTODRUID_CONFIG_NAME).as_posix(), self.wizard().logger)
            for source in root.iter("es.jcyl.ita.crtcyl.client.dao.source.SpatiaLiteServiceDescriptor"):
                dburl = source.find("dbURL")
                if dburl is not None and dburl.text not in self.data_list_full:
                    self.data_list_full.append(dburl.text)
                    item = QStandardItem(dburl.text)
                    item.setData(dburl.text,Qt.UserRole)
                    model.appendRow(item)

            self.data_view.setModel(model)
            self.wizard().reselect_last_selection(self.data_view, self.wizard().current_options.data_list_selected_files)
            self.completeChanged.emit()
            self.data_view.selectionModel().selectionChanged.disconnect()
            self.data_view.selectionModel().selectionChanged.connect(self.completeChanged.emit)
            self.wizard().logger.info("Data files found!")
            self.wizard().s_listener.create_or_update_message_bar(tr("Read CartoDruid configuration finished."), Qgis.MessageLevel.Success,
                                                         time = 5000, clear_messages = False)
        self.wizard().progress2.hide()
        self.s_task = None


    def _downloaded_conf_terminated(self):
        """
            This method is executed after a bad end of the download cartodruid configuration task.
            Shows the error on the logger.
        """
        self.wizard().logger.error("Something went wrong while downloading CartoDruid config file...")
        self.wizard().logger.error(traceback.format_exc())
        self.s_task = None
        self.wizard().progress2.hide()


    def validatePage(self):
        """
            Create the new plugin configuration using the selected checkboxes and data from the data_view. Launch a task
            to do the first download of the files from the device. Also saves the current state of the checkboxes and the selected files
            in the ProjectWizardData for future interactions.
        """
        if self._download_process_finished:
            self.wizard().current_options.config_box_selected = self.config_box.isChecked()
            self.wizard().current_options.image_box_selected = self.image_box.isChecked()
            self.wizard().current_options.data_box_selected = self.data_box.isChecked()
            if self.data_box.isChecked():
                model = self.data_view.model()
                self.wizard().current_options.data_list_selected_files = [
                    model.itemFromIndex(index).text()
                    for index in self.data_view.selectionModel().selectedIndexes()
                ]
            else:
                self.wizard().current_options.data_list_selected_files = []
            self.wizard().current_options.data_list_full = self.data_list_full
            self.wizard().save_carto_project_selections()
            self._download_process_finished = False
            return True
        if self.wizard().current_options and (self.config_box.isChecked() or self.image_box.isChecked() or self.data_box.isChecked()):
            includes = []
            selected_indexes = self.data_view.selectionModel().selectedIndexes()
            if self.data_box.isChecked():
                if selected_indexes != []:
                    if len(self.data_view.selectionModel().selectedIndexes()) == self.data_view.model().rowCount():
                        includes.append("*/data/*")
                    else:
                        for index in selected_indexes:
                            item = self.data_view.model().itemFromIndex(index)
                            includes.append("*/data/" + item.text())
                else:
                    QMessageBox.warning(self.wizard(), tr("No data selected"), tr("Need to select what data files you want to copy from the list to continue."))
                    return False

            if self.config_box.isChecked():
                includes.append("*/config/*")
                includes.append("*/values/*")
            if self.image_box.isChecked():
                includes.append("*/pictures/*/*")

            qgis_p_instance = QgsProject.instance()
            path_to_project = qgis_p_instance.fileName()
            if path_to_project:
                source = Path(qgis_p_instance.fileName()).parent
                source = source / "cartodruid"
                source = source.as_posix()
                os.makedirs(source, exist_ok=True)
                source = "./cartodruid"
                new_sync_data = SyncMapperData(source, self.wizard().current_options.get_project_selected().path.as_posix(), includes, [])
                json = new_sync_data.to_dict()
                self.wizard().c_manager.save_config([json])
                self.wizard().logger.info("New configuration created!")
                self.launch_first_copy_process()
                return False
            else:
                QMessageBox.critical(self.wizard(), tr("Configuration not created"),
                                     tr("An active project must exist to be able to create the configuration. Open a project or create a new one to complete this step."))
                return True
        return False


    def set_enable_interactuables(self, enable):
        self.wizard().button(QWizard.WizardButton.FinishButton).setEnabled(enable)
        self.wizard().button(QWizard.WizardButton.BackButton).setEnabled(enable)
        self.config_box.setEnabled(enable)
        self.image_box.setEnabled(enable)
        self.data_box.setEnabled(enable)
        self.data_box.setEnabled(enable)


    def launch_first_copy_process(self):
        if not self.c_task:
            transformed_config = self.wizard().c_manager.convert_config_relative_path_to_absolute(self.wizard().c_manager.config)
            self.c_task = CopyFoldersFromDevice(self.wizard().s_eng, transformed_config, self.wizard().device, self.wizard().s_listener)
            self.set_enable_interactuables(False)
            self.c_task.taskCompleted.connect(self._copy_directories_completed)
            self.c_task.taskTerminated.connect(self._copy_directories_finished)
            self.wizard().logger.info("Starting project copy.")
            self.wizard().progress2.show()
            QgsApplication.taskManager().addTask(self.c_task)

    def _copy_directories_finished(self):
        self.wizard().logger.error("There was an error copying the directories or it was terminated by the user.")
        self.c_task = None
        self.wizard().progress2.hide()
        self.set_enable_interactuables(True)

    def _copy_directories_completed(self):
        self.wizard().logger.info("Project copy ended.")
        self.c_task = None
        self.wizard().progress2.hide()
        self._download_process_finished = True
        self.launch_first_download_process()

    def launch_first_download_process(self):
        if not self.d_task:
            transformed_config = self.wizard().c_manager.convert_config_relative_path_to_absolute(self.wizard().c_manager.config)
            self.d_task = LoadFiles(self.wizard().s_eng, transformed_config, self.wizard().device, True, self.wizard().s_listener)
            self.set_enable_interactuables(False)
            self.d_task.taskCompleted.connect(self._download_files_completed)
            self.d_task.taskTerminated.connect(self._download_files_finished)
            self.wizard().logger.info("Starting project download.")
            self.wizard().progress2.show()
            QgsApplication.taskManager().addTask(self.d_task)

    def _download_files_finished(self):
        self.wizard().logger.error("There was an error downloading the files or it was terminated by the user.")
        self.d_task = None
        self.wizard().progress2.hide()
        self.set_enable_interactuables(True)
        self.wizard().next()

    def _download_files_completed(self):
        self.wizard().logger.info("Project download ended.")
        self.d_task = None
        self.wizard().progress2.hide()
        self._download_process_finished = True
        self.set_enable_interactuables(True)
        self.wizard().next()


    def on_cancel(self):
        if self.d_task:
            self.d_task.cancel()
            self.d_task = None


    def isComplete(self):
        if (self.config_box.isChecked() or self.image_box.isChecked()) and not self.data_box.isChecked():
            return True
        else:
            if self.data_box.isChecked():
                if self.data_view.selectionModel():
                    return self.data_view.selectionModel().hasSelection()
                else:
                    return False
            else:
                return False
