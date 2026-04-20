import sys
import unittest
from unittest.mock import MagicMock

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)


class TestProjectFinder(unittest.TestCase):

    def setUp(self):
        from qgis_plugin.dialog.project_wizard.wizard_pages.project_finder import ProjectFinder
        self.page = ProjectFinder.__new__(ProjectFinder)
        self.page.project_view = MagicMock()
        self.page.project_view.selectionModel.return_value = MagicMock(
            hasSelection=MagicMock(return_value=False)
        )
        self.page.s_task = None
        self.page.model = None

    def test_isComplete_false_when_no_selection(self):
        sel = MagicMock()
        sel.hasSelection.return_value = False
        self.page.project_view.selectionModel.return_value = sel
        self.assertFalse(self.page.isComplete())

    def test_isComplete_true_when_selection_exists(self):
        sel = MagicMock()
        sel.hasSelection.return_value = True
        self.page.project_view.selectionModel.return_value = sel
        self.assertTrue(self.page.isComplete())

    def test_reselect_calls_select_for_matching_project(self):
        model = QStandardItemModel()

        project_a = MagicMock()
        project_a.project_name = "ProjectA"
        project_b = MagicMock()
        project_b.project_name = "ProjectB"

        item_a = QStandardItem("ProjectA")
        item_a.setData(project_a, Qt.UserRole)
        item_b = QStandardItem("ProjectB")
        item_b.setData(project_b, Qt.UserRole)
        model.appendRow(item_a)
        model.appendRow(item_b)

        view = MagicMock()
        sel_model = MagicMock()
        view.selectionModel.return_value = sel_model
        view.model.return_value = model

        self.page.reselect_last_selection_project_name(view, [project_a])

        sel_model.select.assert_called_once()

    def test_search_projects_terminated_without_exception_clears_task(self):
        self.page.s_task = MagicMock()
        self.page.s_task.exception = None
        self.page.wizard = MagicMock(return_value=MagicMock())

        self.page._search_projects_terminated()

        self.assertIsNone(self.page.s_task)


if __name__ == "__main__":
    unittest.main()