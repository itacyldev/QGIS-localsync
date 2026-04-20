import traceback

from PyQt5.QtCore import QTimer, QItemSelectionModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from qgis.PyQt.QtWidgets import QWizardPage, QMessageBox, QListView

from qgis.PyQt.Qt import Qt
from qgis._core import QgsApplication, Qgis
from ....i18n import tr
from ....localsync.device.device_manager import DeviceManager
from ....tasks.search_projects import SearchProjects


class ProjectFinder(QWizardPage):

    """
        Manages the 1st page of the Cartodruid Project Wizard. Look for projects inside the device and presents them to the user.
        The user must select one of them to go to the next step.
        :ivar s_task: stores the task that manages the reading of the projects from the device.
        :vartype s_task: QTask
    """


    def __init__(self, project_view: QListView):
        """
        Constructor.
        :param project_view: reference to the list view of the 1st page in the wizard.
        """
        super().__init__()
        self.project_view = project_view

        self.s_task = None


    def initializePage(self):
        """
            Launches the search of project on the selected device.
            Managed by QGIS, it is launched when the page is loaded.
        """
        if self.wizard().initialize_first_page:
            self.project_view.setModel(None)
            QTimer.singleShot(0, self.completeChanged.emit)
            device = self.wizard().device
            if not self.s_task:
                self.s_task = SearchProjects(self.wizard().p_manager, device.device_id, self.wizard().s_listener)
                self.wizard().logger.info("Starting search projects task...")
                self.s_task.taskCompleted.connect(self._search_projects_completed)
                self.s_task.taskTerminated.connect(self._search_projects_terminated)
                QgsApplication.taskManager().addTask(self.s_task)
                self.wizard().progress1.show()
        else:
            self.wizard().logger.info("initialize_first_page")
            self.wizard().initialize_first_page = True



    def _search_projects_completed(self):
        """
            Method called when the result of the project search task is successful.
            Populates the list view in the dialog with the result of the task.
        """
        if self.s_task:
            projects = self.s_task.result
            model = QStandardItemModel()
            self.project_view.setModel(model)
            self.project_view.selectionModel().selectionChanged.disconnect()
            self.project_view.selectionModel().selectionChanged.connect(self.completeChanged.emit)

            for project in projects:
                item = QStandardItem(project.project_name)
                item.setData(project, Qt.UserRole)
                model.appendRow(item)
            if self.wizard().current_options.get_project_selected():
                self.reselect_last_selection_project_name(self.project_view, [self.wizard().current_options.get_project_selected()])

            self.wizard().logger.info("Search projects task ended.")
            self.wizard().s_listener.create_or_update_message_bar(tr("Search projects completed!"), Qgis.MessageLevel.Success,
                                                         time = 5000, clear_messages = False)
        self.wizard().progress1.hide()
        self.s_task = None

    def reselect_last_selection_project_name(self, view: QListView, items_to_search: list):
        """
            Select a project previously selected by the user in another execution of the wizard.
            :param view: reference to the QListView of this page on the gui.
            :param items_to_search: list of items to select.
        """
        model = view.model()
        for row in range(model.rowCount()):
            item = model.item(row)
            if items_to_search:
                if any(item_s.project_name == item.data(Qt.UserRole).project_name for item_s in items_to_search):
                    view.selectionModel().select(model.indexFromItem(item),
                                                           QItemSelectionModel.SelectionFlag.Select)


    def _search_projects_terminated(self):
        """
            Method called when the result of the project search task is not successful.
            Show the errors and create a message bar accordingly.
        """
        if self.s_task and self.s_task.exception:
            self.wizard().logger.error("Search projects task ended with errors: " + str(self.s_task.exception))
            self.wizard().logger.error(traceback.format_exc())
            self.wizard().s_listener.create_or_update_message_bar(tr("Something went wrong with the project search. Check the log."),
                                                         Qgis.MessageLevel.Critical, time = 5000, clear_messages = False)
        self.wizard().progress1.hide()
        self.s_task = None

    def validatePage(self):
        """
            Save the selected project and starts the next page.
        """
        indexes = self.project_view.selectionModel().selectedIndexes()
        if indexes:
            index = indexes[0]
            model = self.project_view.model()
            project = model.itemFromIndex(index).data(Qt.UserRole)
            self.wizard().new_project = self.wizard().current_options.change_project(project)
            return True
        else:
            QMessageBox.warning(self, tr("Select a project"), tr("You must select a project from the list before going to the next page."))
            return False


    def isComplete(self):
        """
            Determines if is possible to pass to the next page of the wizard.
            When a project is selected from the list view, then you can pass to the next page.
        """
        if self.project_view.selectionModel():
            return self.project_view.selectionModel().hasSelection()
        else:
            return False


