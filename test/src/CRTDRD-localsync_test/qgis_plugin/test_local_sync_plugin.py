# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, MagicMock, patch, call
import json
import os

from qgis_plugin.configuration.configuration_manager import ConfigurationManager
from qgis_plugin.local_sync_plugin import LocalSyncPlugin
from qgis_plugin.localsync.device.device_manager import DeviceManager


import unittest
from unittest.mock import MagicMock, patch
from qgis_plugin.local_sync_plugin import SyncListener


class TestSyncListener(unittest.TestCase):

    def _make_listener(self):
        listener = SyncListener.__new__(SyncListener)
        listener.iface = MagicMock()
        listener.dlg = MagicMock()
        listener.message_bar = None
        listener.start_signal = MagicMock()
        return listener

    def test_create_or_update_message_bar_emits_signal(self):
        listener = self._make_listener()
        listener.create_or_update_message_bar("test msg", 0, 500, True)
        listener.start_signal.emit.assert_called_once_with("test msg", 0, 500, True)

    def test_remove_message_clears_if_current(self):
        listener = self._make_listener()
        bar = MagicMock()
        listener.message_bar = bar
        listener._remove_message(bar)
        listener.iface.messageBar.return_value.clearWidgets.assert_called_once()
        self.assertIsNone(listener.message_bar)

    def test_remove_message_ignores_if_not_current(self):
        listener = self._make_listener()
        listener.message_bar = MagicMock()
        listener._remove_message(MagicMock())  # diferente instancia
        listener.iface.messageBar.return_value.clearWidgets.assert_not_called()


class TestLocalSyncPlugin(unittest.TestCase):

    def setUp(self):
        """Initial configuration for every test"""
        self.mock_iface = Mock()
        self.mock_iface.addToolBar.return_value = Mock()
        self.mock_iface.mainWindow.return_value = Mock()

        # Patch QgsProject
        self.qgs_project_patcher = patch('qgis_plugin.local_sync_plugin.QgsProject')
        self.mock_qgs_project = self.qgs_project_patcher.start()

        # Patch QSettings
        self.qgs_setings_patcher = patch('qgis_plugin.local_sync_plugin.QSettings')
        self.mock_qgs_settings = self.qgs_setings_patcher.start()
        self.mock_qgs_settings.value.return_value = 'es'

        # Configure project mock
        self.mock_project_instance = Mock()
        self.mock_project_instance.readEntry.return_value = ("", False)
        self.mock_project_instance.writeEntry.return_value = None
        self.mock_project_instance.fileName.return_value = ""

        # Configure signals as Mocks
        self.mock_project_instance.readProject = Mock()
        self.mock_project_instance.projectSaved = Mock()
        self.mock_project_instance.cleared = Mock()

        self.mock_qgs_project.instance.return_value = self.mock_project_instance

        # Patch logger handler to prevent set_dialog calls
        self.logger_patcher = patch('qgis_plugin.local_sync_plugin.QgisLoggerHandler')
        self.mock_logger_handler = self.logger_patcher.start()
        mock_logger_instance = Mock()
        mock_handler = Mock()
        mock_handler._handler_id = "other"  # Not "qgis" to avoid set_dialog
        mock_logger_instance.handlers = [mock_handler]
        mock_logger_instance.get_logger.return_value = mock_logger_instance
        self.mock_logger_handler.return_value = mock_logger_instance

        # Patch other components
        with patch('qgis_plugin.local_sync_plugin.SyncEngine'), \
                patch('qgis_plugin.local_sync_plugin.ProjectManager'), \
                patch('qgis_plugin.local_sync_plugin.MessagesDialog'), \
                patch('qgis_plugin.local_sync_plugin.SyncListener'):
            self.plugin = LocalSyncPlugin(self.mock_iface)

    def tearDown(self):
        """Clean patches"""
        self.qgs_project_patcher.stop()
        self.logger_patcher.stop()

    def test_initialization(self):
        """Verify that the initialisation of the plugin is correct"""
        self.assertFalse(self.plugin.block_buttons)
        self.assertEqual(self.plugin.project_name, "")
        self.assertFalse(self.plugin.searching_projects)

    @patch("qgis_plugin.local_sync_plugin.QIcon")
    def test_new_project_without_carto_project(self, mock_icon):
        """Test new_project method without projects"""
        self.plugin.c_manager = MagicMock()

        self.plugin.clear_devices_combo = MagicMock()
        self.plugin.c_manager.search_for_projects_in_config.return_value = []

        self.plugin.projects_button = MagicMock()

        self.plugin.selected_project = MagicMock()

        self.plugin.new_project()

        self.assertEqual( self.plugin.c_manager.config, [])
        self.plugin.clear_devices_combo.assert_called_once()
        self.plugin.c_manager.change_protocol_used.assert_called_once_with(True)
        self.plugin.selected_project.setText.assert_called_once_with("")


    @patch("qgis_plugin.local_sync_plugin.QIcon")
    def test_new_project_with_carto_project(self, mock_icon):
        """Test new_project method with projects"""
        self.plugin.c_manager = MagicMock()

        self.plugin.clear_devices_combo = MagicMock()
        self.plugin.c_manager.search_for_projects_in_config.return_value = ["Project"]

        self.plugin.projects_button = MagicMock()

        self.plugin.selected_project = MagicMock()

        self.plugin.new_project()

        self.assertEqual( self.plugin.c_manager.config, [])
        self.plugin.clear_devices_combo.assert_called_once()
        self.plugin.c_manager.change_protocol_used.assert_called_once_with(True)
        self.plugin.selected_project.setText.assert_called_once_with('Current project: <b>Project</b>')


    def test_get_layers_in_edit_mode(self):
        """Test get_layers_in_edit_mode method"""
        mock_layer1 = Mock()
        mock_layer1.isEditable.return_value = True

        mock_layer2 = Mock()
        mock_layer2.isEditable.return_value = False

        mock_layer3 = Mock()
        mock_layer3.isEditable.return_value = True

        with patch('qgis_plugin.local_sync_plugin.QgsProject') as mock_qgs:
            mock_instance = Mock()
            mock_instance.mapLayers.return_value.values.return_value = [
                mock_layer1, mock_layer2, mock_layer3
            ]
            mock_qgs.instance.return_value = mock_instance

            result = self.plugin.get_layers_in_edit_mode()

        self.assertEqual(len(result), 2)
        self.assertIn(mock_layer1, result)
        self.assertIn(mock_layer3, result)
        self.assertNotIn(mock_layer2, result)

    def test_get_layers_in_edit_mode_no_layers(self):
        """Test get_layers_in_edit_mode with no layers"""
        with patch('qgis_plugin.local_sync_plugin.QgsProject') as mock_qgs:
            mock_instance = Mock()
            mock_instance.mapLayers.return_value.values.return_value = []
            mock_qgs.instance.return_value = mock_instance

            result = self.plugin.get_layers_in_edit_mode()

        self.assertEqual(len(result), 0)

    def test_upload_no_editable_layers(self):
        """Test upload without editable layers"""
        self.plugin.devices_combo = Mock()
        mock_device = Mock()
        self.plugin.devices_combo.currentData.return_value = mock_device

        with patch.object(self.plugin, 'get_layers_in_edit_mode', return_value=[]), \
                patch.object(self.plugin, 'load_files') as mock_load:
            self.plugin.upload()

            mock_load.assert_called_once_with(False)

    def test_upload_with_editable_layers(self):
        """Test upload with editable layers"""
        mock_layer = Mock()
        self.plugin.devices_combo = Mock()

        with patch.object(self.plugin, 'get_layers_in_edit_mode', return_value=[mock_layer]), \
                patch.object(self.plugin, 'launch_save_modal') as mock_save:
            self.plugin.upload()

            mock_save.assert_called_once_with([mock_layer], False)

    def test_upload_no_device(self):
        """Test upload without selected device"""
        self.plugin.devices_combo = Mock()
        self.plugin.devices_combo.currentData.return_value = None

        with patch.object(self.plugin, 'get_layers_in_edit_mode', return_value=[]), \
                patch.object(self.plugin, 'load_files') as mock_load:
            self.plugin.upload()

            mock_load.assert_not_called()

    def test_download_no_editable_layers(self):
        """Test download without editable layers"""
        self.plugin.devices_combo = Mock()
        mock_device = Mock()
        self.plugin.devices_combo.currentData.return_value = mock_device

        with patch.object(self.plugin, 'get_layers_in_edit_mode', return_value=[]), \
                patch.object(self.plugin, 'load_files') as mock_load:
            self.plugin.download()

            mock_load.assert_called_once_with(True)

    def test_download_with_editable_layers(self):
        """Test download with editable layers"""
        mock_layer = Mock()
        self.plugin.devices_combo = Mock()

        with patch.object(self.plugin, 'get_layers_in_edit_mode', return_value=[mock_layer]), \
                patch.object(self.plugin, 'launch_save_modal') as mock_save:
            self.plugin.download()

            mock_save.assert_called_once_with([mock_layer], True)


    @patch('qgis_plugin.local_sync_plugin.LoadFiles')
    @patch('qgis_plugin.local_sync_plugin.QgsApplication')
    def test_load_files_success(self, mock_qgs_app, mock_load_files):
        """Test load_files successful execution"""
        self.mock_project_instance.fileName.return_value = "/project/test.qgs"

        mock_device = Mock()
        mock_device.no_data = False
        self.plugin.devices_combo = Mock()
        self.plugin.devices_combo.currentData.return_value = mock_device

        self.plugin.config = [{"source": "/test"}]
        self.plugin.searching_projects = False
        self.plugin.block_buttons = False

        with patch.object(ConfigurationManager, 'check_if_config_path_exists', return_value=True), \
             patch.object(self.plugin, 'block_plugin_actions') as mock_block:
            self.plugin.load_files(True)

        mock_load_files.assert_called_once()
        mock_block.assert_called_once_with(True)
        call_args = mock_load_files.call_args[0]
        self.assertTrue(call_args[4])  # pull=True

    def test_load_files_no_project(self):
        """Test load_files without an opened project"""
        self.mock_project_instance.fileName.return_value = ""

        mock_device = Mock()
        mock_device.no_data = False
        self.plugin.devices_combo = Mock()
        self.plugin.devices_combo.currentData.return_value = mock_device

        with patch.object(ConfigurationManager, 'check_if_config_path_exists', return_value=True), \
                patch('qgis_plugin.local_sync_plugin.LoadFiles') as mock_load:
            self.plugin.load_files(False)

            mock_load.assert_not_called()

    def test_load_files_invalid_paths(self):
        """Test load_files with invalid paths"""

        mock_combo = MagicMock()
        mock_combo.currentData.return_value = DeviceManager()
        self.plugin.devices_combo = mock_combo

        self.mock_project_instance.fileName.return_value = "/project/test.qgs"

        with patch.object(ConfigurationManager, 'check_if_config_path_exists', return_value=False), \
                patch('qgis_plugin.local_sync_plugin.LoadFiles') as mock_load:
            self.plugin.load_files(False)

            mock_load.assert_not_called()

    def test_load_files_searching_projects(self):
        """Test load_files while searching for projects"""
        mock_combo = MagicMock()
        mock_combo.currentData.return_value = DeviceManager()
        self.plugin.devices_combo = mock_combo

        self.plugin.searching_projects = True

        with patch('qgis_plugin.local_sync_plugin.LoadFiles') as mock_load:
            self.plugin.load_files(False)

            mock_load.assert_not_called()

    def test_load_files_buttons_blocked(self):
        """Test load_files when buttons are blocked"""
        mock_combo = MagicMock()
        mock_combo.currentData.return_value = DeviceManager()
        self.plugin.devices_combo = mock_combo
        self.plugin.block_buttons = True

        with patch('qgis_plugin.local_sync_plugin.LoadFiles') as mock_load:
            self.plugin.load_files(False)

            mock_load.assert_not_called()

    def test_load_files_device_no_data(self):
        """Test load_files when device has no data"""
        mock_device = Mock()
        mock_device.no_data = True
        self.plugin.devices_combo = Mock()
        self.plugin.devices_combo.currentData.return_value = mock_device

        with patch('qgis_plugin.local_sync_plugin.LoadFiles') as mock_load:
            self.plugin.load_files(False)

            mock_load.assert_not_called()

    def test_block_plugin_actions(self):
        """Test block_plugin_actions method"""
        self.plugin.devices_combo = Mock()

        self.plugin.block_plugin_actions(True)

        self.plugin.devices_combo.blockSignals.assert_called_once_with(True)
        self.assertTrue(self.plugin.block_buttons)

        self.plugin.block_plugin_actions(False)
        self.plugin.devices_combo.blockSignals.assert_called_with(False)
        self.assertFalse(self.plugin.block_buttons)

    def test_load_ended(self):
        """Test load_ended method"""
        mock_layer1 = Mock()
        mock_layer2 = Mock()

        with patch.object(self.plugin, 'block_plugin_actions') as mock_block, \
                patch('qgis_plugin.local_sync_plugin.QgsProject') as mock_qgs:
            mock_instance = Mock()
            mock_instance.mapLayers.return_value.values.return_value = [mock_layer1, mock_layer2]
            mock_qgs.instance.return_value = mock_instance

            self.plugin.load_ended()

            mock_block.assert_called_once_with(False)
            mock_layer1.reload.assert_called_once()
            mock_layer2.reload.assert_called_once()


    @patch('qgis_plugin.local_sync_plugin.LocalsyncConfPanel')
    def test_open_config_window_first_time(self, mock_panel):
        """Test open_config_window first time"""
        self.plugin.config = [{"source": "/test"}]

        mock_conf_dlg = Mock()
        mock_panel.return_value = mock_conf_dlg

        self.plugin.open_config_window()

        mock_panel.assert_called_once_with(self.plugin, self.plugin.c_manager, self.plugin.photo_configuration)
        mock_conf_dlg.show.assert_called_once()
        mock_conf_dlg.open.assert_called_once()

    def test_open_config_window_subsequent_calls(self):
        """Test open_config_window subsequent calls"""
        self.plugin.first_start_config = False
        self.plugin.conf_dlg = Mock()
        self.plugin.c_manager.config = [{"source": "/test", "destination": "/dest"}]

        self.plugin.open_config_window()

        self.plugin.conf_dlg.show.assert_called_once()
        self.plugin.conf_dlg.open.assert_called_once()
        # Verify formatted JSON is set
        expected_json = json.dumps(self.plugin.c_manager.config, indent=4, ensure_ascii=False)
        self.plugin.conf_dlg.conf_text_edit.setText.assert_called_once_with(expected_json)

    @patch('qgis_plugin.local_sync_plugin.LocalsyncSaveLayers')
    @patch('qgis_plugin.local_sync_plugin.QStringListModel')
    def test_launch_save_modal_first_time_accepted(self, mock_model, mock_save_layers):
        """Test launch_save_modal first time with accepted dialog"""

        mock_layer1 = Mock()
        mock_layer1.name.return_value = "Layer1"
        mock_layer2 = Mock()
        mock_layer2.name.return_value = "Layer2"
        layers = [mock_layer1, mock_layer2]

        mock_dlg = Mock()
        mock_dlg.exec_.return_value = True
        mock_save_layers.return_value = mock_dlg

        with patch.object(self.plugin, 'download') as mock_download:
            self.plugin.launch_save_modal(layers, True)

            mock_save_layers.assert_called_once()
            mock_layer1.commitChanges.assert_called_once()
            mock_layer2.commitChanges.assert_called_once()
            mock_download.assert_called_once()

    @patch('qgis_plugin.local_sync_plugin.LocalsyncSaveLayers')
    def test_launch_save_modal_rejected(self, mock_save_layers):
        """Test launch_save_modal with rejected dialog"""
        self.plugin.first_start_save = False
        self.plugin.save_dlg = Mock()
        self.plugin.save_dlg.exec_.return_value = False

        mock_layer = Mock()
        mock_layer.name.return_value = "layer_test"
        layers = [mock_layer]

        with patch.object(self.plugin, 'upload') as mock_upload:
            self.plugin.launch_save_modal(layers, False)

            mock_layer.commitChanges.assert_not_called()
            mock_upload.assert_not_called()

if __name__ == '__main__':
    unittest.main()