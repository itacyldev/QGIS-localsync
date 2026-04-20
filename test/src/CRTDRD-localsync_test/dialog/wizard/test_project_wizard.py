import sys
import unittest
from unittest.mock import MagicMock, patch

from PyQt5.QtWidgets import QApplication, QWizard

from qgis_plugin.dialog.project_wizard.project_wizard_data import ProjectWizardData
from qgis_plugin.localsync.project.project_manager import ProjectData

app = QApplication.instance() or QApplication(sys.argv)


class TestProjectWizard(unittest.TestCase):

    def setUp(self):
        from qgis_plugin.dialog.project_wizard.project_wizard import ProjectWizard
        from qgis_plugin.dialog.project_wizard.project_wizard_data import ProjectWizardData
        from PyQt5.QtWidgets import QWizardPage

        real_page = QWizardPage()

        with patch("qgis_plugin.dialog.project_wizard.project_wizard.uic.loadUiType", return_value=(QWizard, None)), \
             patch("qgis_plugin.dialog.project_wizard.project_wizard.ProjectFinder", return_value=real_page), \
             patch("qgis_plugin.dialog.project_wizard.project_wizard.FileSelector", return_value=real_page), \
             patch("qgis_plugin.dialog.project_wizard.project_wizard.AddLayers", return_value=real_page):
            self.wiz = ProjectWizard(
                MagicMock(),  # localsync_plugin
                MagicMock(),  # c_manager
                MagicMock(),  # p_manager
                MagicMock(),  # s_eng
                MagicMock(),  # s_listener
                MagicMock()
            )
        self.wiz.current_options = ProjectWizardData()

    def test_save_carto_project_selections_calls_writeEntry(self):
        mock_project = MagicMock()
        with patch("qgis_plugin.dialog.project_wizard.project_wizard.QgsProject") as mock_qgs:
            mock_qgs.instance.return_value = mock_project
            self.wiz.current_options = ProjectWizardData(ProjectData())
            self.wiz.save_carto_project_selections()
            mock_project.writeEntry.assert_called_once()

    def test_initialise_sets_device_and_second_page_flag(self):
        device = MagicMock()
        with patch("qgis_plugin.dialog.project_wizard.project_wizard.QgsProject") as mock_qgs:
            mock_qgs.instance.return_value.readEntry.return_value = ("{}", False)
            self.wiz.initialise(device, second_page=False)
        self.assertEqual(self.wiz.device, device)
        self.assertFalse(self.wiz.start_second_page)

    def test_initialise_with_malformed_json_shows_warning(self):
        with patch("qgis_plugin.dialog.project_wizard.project_wizard.QgsProject") as mock_qgs, \
             patch("qgis_plugin.dialog.project_wizard.project_wizard.QMessageBox") as mock_mb:
            mock_qgs.instance.return_value.readEntry.return_value = ("NOT_JSON", True)
            self.wiz.initialise(MagicMock(), second_page=False)
            mock_mb.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()