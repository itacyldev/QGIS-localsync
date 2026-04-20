import sys
import unittest
from unittest.mock import MagicMock

from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)


class TestFileSelector(unittest.TestCase):

    def setUp(self):
        from qgis_plugin.dialog.project_wizard.wizard_pages.file_selector import FileSelector

        config_box = MagicMock()
        image_box = MagicMock()
        data_box = MagicMock()
        data_view = MagicMock()

        config_box.stateChanged.connect = MagicMock()
        image_box.stateChanged.connect = MagicMock()
        data_box.stateChanged.connect = MagicMock()

        self.page = FileSelector.__new__(FileSelector)
        self.page.config_box = config_box
        self.page.image_box = image_box
        self.page.data_box = data_box
        self.page.data_view = data_view
        self.page.s_task = None
        self.page.d_task = None
        self.page.carto_conf_pc_dir = ""
        self.page._download_process_finished = False
        self.page.data_list_full = []

    def test_change_data_view_state_enables_when_data_box_checked(self):
        self.page.data_box.isChecked.return_value = True
        self.page.change_data_view_state()
        self.page.data_view.setEnabled.assert_called_with(True)

    def test_change_data_view_state_disables_when_data_box_unchecked(self):
        self.page.data_box.isChecked.return_value = False
        self.page.change_data_view_state()
        self.page.data_view.setEnabled.assert_called_with(False)

    def test_isComplete_true_when_config_checked_without_data(self):
        self.page.config_box.isChecked.return_value = True
        self.page.image_box.isChecked.return_value = False
        self.page.data_box.isChecked.return_value = False
        self.assertTrue(self.page.isComplete())

    def test_isComplete_false_when_nothing_checked(self):
        self.page.config_box.isChecked.return_value = False
        self.page.image_box.isChecked.return_value = False
        self.page.data_box.isChecked.return_value = False
        self.assertFalse(self.page.isComplete())

    def test_isComplete_true_when_data_checked_and_selection_exists(self):
        self.page.config_box.isChecked.return_value = False
        self.page.image_box.isChecked.return_value = False
        self.page.data_box.isChecked.return_value = True
        sel_model = MagicMock()
        sel_model.hasSelection.return_value = True
        self.page.data_view.selectionModel.return_value = sel_model
        self.assertTrue(self.page.isComplete())

    def test_set_enable_interactuables_propagates_flag_to_all_controls(self):
        wiz = MagicMock()
        self.page.wizard = MagicMock(return_value=wiz)
        self.page.set_enable_interactuables(False)
        self.page.config_box.setEnabled.assert_called_with(False)
        self.page.data_box.setEnabled.assert_called_with(False)


if __name__ == "__main__":
    unittest.main()