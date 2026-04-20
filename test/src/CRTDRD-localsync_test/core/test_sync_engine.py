import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from qgis_plugin.localsync.core.sync_engine import SyncEngine


class TestSyncEngine(unittest.TestCase):

    def setUp(self):
        self.engine = SyncEngine()
        self.engine.logger = MagicMock()
        self.engine.locator = MagicMock()
        self.engine.transport = MagicMock()

    def test_activate_adb(self):
        with patch('qgis_plugin.localsync.core.sync_engine.AdbDeviceLocator'), \
             patch('qgis_plugin.localsync.core.sync_engine.AdbTransporter'):
            self.engine.activate_mtp_or_adb(True)
        self.assertTrue(SyncEngine.adb_active)
        self.assertFalse(SyncEngine.mtp_active)

    def test_activate_mtp(self):
        with patch('qgis_plugin.localsync.core.sync_engine.MtpDeviceLocator'), \
             patch('qgis_plugin.localsync.core.sync_engine.MtpTransporter'):
            self.engine.activate_mtp_or_adb(False)
        self.assertFalse(SyncEngine.adb_active)
        self.assertTrue(SyncEngine.mtp_active)

    def test_discover_devices_success(self):
        device = MagicMock()
        self.engine.locator.get_connected_devices.return_value = ["dev1"]
        self.engine.locator.about_device.return_value = device

        result, ok = self.engine.discover_devices()

        self.assertTrue(ok)
        self.assertEqual(result, [device])

    def test_discover_devices_exception(self):
        self.engine.locator.search_for_connected_devices.side_effect = RuntimeError("fail")
        result, ok = self.engine.discover_devices()
        self.assertFalse(ok)
        self.assertEqual(result, [])

    def test_list_files_in_device(self):
        SyncEngine.adb_active = True
        SyncEngine.mtp_active = False
        device = MagicMock()
        device.device_id = "dev1"
        expected = [Path("/dev/folder/file.gpkg")]
        self.engine.transport.get_file_list.return_value = expected

        with patch('qgis_plugin.localsync.core.sync_engine.AdbChannel'):
            result = self.engine.list_files(True, "/dev/folder", [], [], device)

        self.assertEqual(result, expected)

    def test_list_files_exception_returns_empty(self):
        device = MagicMock()
        self.engine.transport.get_file_list.side_effect = RuntimeError("error")
        with patch('qgis_plugin.localsync.core.sync_engine.AdbChannel'):
            result = self.engine.list_files(True, "/dev/folder", [], [], device)
        self.assertEqual(result, [])

    def test_file_transport_no_host_path(self):
        device = MagicMock()
        device.path_to_project = "/dev/path"
        host = MagicMock()
        host.path = ""
        self.assertFalse(self.engine.file_transport(device, host, [], [], True))

    def test_file_transport_pull_success(self):
        SyncEngine.adb_active = True
        SyncEngine.mtp_active = False
        device = MagicMock()
        device.path_to_project = "/dev/path"
        device.device_id = "dev1"
        host = MagicMock()
        host.path = "/pc/path"
        self.engine.transport.get_file_list.return_value = [Path("/dev/path/file.gpkg")]

        with patch('qgis_plugin.localsync.core.sync_engine.AdbChannel'), \
             patch('qgis_plugin.localsync.core.sync_engine.HostChannel'):
            result = self.engine.file_transport(device, host, [], [], True)

        self.assertTrue(result)
        self.engine.transport.pull.assert_called_once()