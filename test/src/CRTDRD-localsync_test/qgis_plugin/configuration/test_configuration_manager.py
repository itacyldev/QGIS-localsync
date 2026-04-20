import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from qgis_plugin.configuration.configuration_manager import ConfigurationManager


class TestConfigurationManager(unittest.TestCase):

    def setUp(self):
        self.s_eng = MagicMock()
        with patch('qgis_plugin.configuration.configuration_manager.QgsProject') as mock_proj, \
             patch('qgis_plugin.configuration.configuration_manager.QgsSettings'), \
             patch('qgis_plugin.configuration.configuration_manager.FindAdb') as mock_find, \
             patch('qgis_plugin.configuration.configuration_manager.AdbChannel'):
            mock_proj.instance.return_value.readEntry.return_value = ('[]', True)
            mock_find.find_adb.return_value = ""
            self.manager = ConfigurationManager(self.s_eng)
            self.manager.logger = MagicMock()

    def test_convert_relative_path_to_absolute(self):
        config = [{"source": "./data/layers", "destination": "/device/path", "includes": [], "excludes": []}]
        with patch('qgis_plugin.configuration.configuration_manager.QgsProject') as mock_proj:
            mock_proj.instance.return_value.fileName.return_value = "/home/user/project/project.qgz"
            result = self.manager.convert_config_relative_path_to_absolute(config)
        self.assertFalse(result[0]["source"].startswith("."))

    def test_convert_absolute_path_unchanged(self):
        config = [{"source": "/absolute/path", "destination": "/device/path", "includes": [], "excludes": []}]
        result = self.manager.convert_config_relative_path_to_absolute(config)
        self.assertEqual(result[0]["source"], "/absolute/path")

    def test_search_for_projects_in_config_found(self):
        self.manager.config = [{"destination": "/Internal/projects/my_project/layers"}]
        with patch('qgis_plugin.configuration.configuration_manager.CARTODRUID_PROJECT_SPLITTERS', ["projects"]):
            result = self.manager.search_for_projects_in_config()
        self.assertIn("my_project", result)

    def test_search_for_projects_in_config_empty(self):
        self.manager.config = []
        self.assertEqual(self.manager.search_for_projects_in_config(), [])

    def test_check_if_config_path_no_device(self):
        self.assertTrue(self.manager.check_if_config_path_exists([], False, None))

    def test_change_protocol_used_to_mtp(self):
        self.manager.change_protocol_used(False)
        self.assertFalse(self.manager.adb_activated)
        self.s_eng.activate_mtp_or_adb.assert_called_with(False)