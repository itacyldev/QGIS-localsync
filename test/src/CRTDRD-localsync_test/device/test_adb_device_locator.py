import unittest
from unittest.mock import patch, MagicMock, Mock
import logging

from qgis_plugin.localsync.channels.adb_channel import AdbChannel
from qgis_plugin.localsync.device.adb_device_locator import AdbDeviceLocator
from qgis_plugin.localsync.device.device_manager import DeviceManager


class TestAdbDeviceLocator(unittest.TestCase):

    def setUp(self):
        self.locator = AdbDeviceLocator()
        # Clean the static state of the tests
        AdbDeviceLocator._devices = []
        AdbDeviceLocator._about_devices = {}

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel')
    def test_filter_with_sdcard_pattern_match(self, mock_adb):
        # Arrange
        output = "ABCD-1234\n\nEF01-5678\n"
        self.locator._get_main_storage_path = Mock(return_value="/storage/main")

        # Act
        result = self.locator._filter_storages_to_locate_cards(output)

        # Assert
        expected_storages = ["/storage/ABCD-1234/", "/storage/EF01-5678/"]
        self.locator._get_main_storage_path.assert_called_once_with(
            False, expected_storages, False
        )
        self.assertEqual(result, "/storage/main")

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel')
    def test_filter_with_self_containing_primary(self, mock_adb):
        # Arrange
        output = "self\nemulated\n"
        mock_adb.no_recursive_ls.return_value = ["primary", "other_folder"]
        self.locator._get_main_storage_path = Mock(return_value="/storage/emulated/0")

        # Act
        result = self.locator._filter_storages_to_locate_cards(output)

        # Assert
        mock_adb.no_recursive_ls.assert_called_once_with("/storage/self")
        self.locator._get_main_storage_path.assert_called_once_with(
            True, [], True
        )

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel')
    def test_filter_combined_storages(self, mock_adb):
        # Arrange
        output = "ABCD-1234\nself\nemulated\n1234-ABCD\n"
        mock_adb.no_recursive_ls.return_value = ["data", "media"]
        self.locator._get_main_storage_path = Mock(return_value="/storage/result")

        # Act
        result = self.locator._filter_storages_to_locate_cards(output)

        # Assert
        expected_storages = ["/storage/ABCD-1234/", "/storage/1234-ABCD/"]
        self.locator._get_main_storage_path.assert_called_once_with(
            False, expected_storages, True
        )

    def test_primary_found_adds_self_primary_path(self):
        # Arrange
        storages = ["/storage/ABCD-1234/"]

        # Act
        result = self.locator._get_main_storage_path(True, storages, False)

        # Assert
        expected = ["/storage/self/primary/", "/storage/ABCD-1234/"]
        self.assertEqual(result, expected)

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel')
    def test_emulated_found_adds_emulated_with_user_id(self, mock_adb):
        # Arrange
        mock_adb.get_current_used_id.return_value = "0\n"
        storages = []

        # Act
        result = self.locator._get_main_storage_path(False, storages, True)

        # Assert
        expected = ["/storage/emulated/0/"]
        self.assertEqual(result, expected)
        mock_adb.get_current_used_id.assert_called_once()

    def test_no_primary_no_emulated_adds_sdcard(self):
        # Arrange
        storages = ["/storage/1234-5678/"]

        # Act
        result = self.locator._get_main_storage_path(False, storages, False)

        # Assert
        expected = ["/sdcard/", "/storage/1234-5678/"]
        self.assertEqual(result, expected)

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_devices')
    def test_search_for_connected_devices_single_device(self, mock_get_devices):
        """Verify the search of a connected device"""
        mock_get_devices.return_value = "List of devices attached\ndevice123\tdevice\n"

        self.locator.search_for_connected_devices()

        self.assertEqual(self.locator._devices, ["device123"])

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_devices')
    def test_search_for_connected_devices_multiple_devices(self, mock_get_devices):
        """Verify the search of muliple connected devices"""
        mock_get_devices.return_value = """List of devices attached
device123\tdevice
device456\tdevice
device789\tdevice
"""

        self.locator.search_for_connected_devices()

        self.assertEqual(self.locator._devices, ["device123", "device456", "device789"])

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_devices')
    def test_search_for_connected_devices_ignores_unauthorized(self, mock_get_devices):
        """Verify that devices not authorized are treated as no_data"""
        mock_get_devices.return_value = """List of devices attached
device123\tdevice
device456\tunauthorized
device789\tdevice
"""

        self.locator.search_for_connected_devices()

        self.assertEqual(self.locator._devices, ["device123", "device456", "device789"])
        self.assertTrue(self.locator._about_devices["device456"].no_data)

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_devices')
    def test_search_for_connected_devices_ignores_offline(self, mock_get_devices):
        """Verify that offline devices are treated as no_data"""
        mock_get_devices.return_value = """List of devices attached
device123\tdevice
device456\toffline
"""

        self.locator.search_for_connected_devices()

        self.assertEqual(self.locator._devices, ["device123","device456"])
        self.assertTrue(self.locator._about_devices["device456"].no_data)

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_devices')
    def test_search_for_connected_devices_no_devices(self, mock_get_devices):
        """Verify the search without devices attached"""
        mock_get_devices.return_value = "List of devices attached\n"

        self.locator.search_for_connected_devices()

        self.assertEqual(self.locator._devices, [])

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_devices')
    def test_search_for_connected_devices_with_empty_lines(self, mock_get_devices):
        """Verify that empty lines are ignored"""
        mock_get_devices.return_value = """List of devices attached
device123\tdevice

device456\tdevice

"""

        self.locator.search_for_connected_devices()

        self.assertEqual(self.locator._devices, ["device123", "device456"])

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_devices')
    def test_search_for_connected_devices_clears_previous_list(self, mock_get_devices):
        """Verify that the last list is cleaned before searching again"""
        # Firest search
        mock_get_devices.return_value = "List of devices attached\ndevice123\tdevice\n"
        self.locator.search_for_connected_devices()
        self.assertEqual(len(self.locator._devices), 1)

        # Second search with different devices
        mock_get_devices.return_value = "List of devices attached\ndevice456\tdevice\ndevice789\tdevice\n"
        self.locator.search_for_connected_devices()

        self.assertEqual(self.locator._devices, ["device456", "device789"])

    def test_get_connected_devices_returns_list(self):
        """Verify that returns the list of devices"""
        self.locator._devices = ["device123", "device456"]

        result = self.locator.get_connected_devices()

        self.assertEqual(result, ["device123", "device456"])

    def test_get_connected_devices_empty_list(self):
        """Verifica que devuelve lista vacía si no hay dispositivos"""
        result = self.locator.get_connected_devices()

        self.assertEqual(result, [])

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbDeviceLocator._filter_storages_to_locate_cards')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.no_recursive_ls')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_information_about_device')
    def test_get_devices_information_single_device(self, mock_get_info, mock_no_recursive_ls,
                                                   mock_filter_storages_to_locate_cards):
        """Verify the gathering of information of a device"""
        self.locator._devices = ["device123"]

        mock_get_info.side_effect = lambda prop: {
            "ro.product.model": "Pixel 6",
            "ro.product.name": "oriole",
            "ro.product.brand": "google",
            "ro.product.manufacturer": "Google",
            "ro.product.cpu.abi": "arm64-v8a",
            "ro.product.cpu.abilist": "arm64-v8a,armeabi-v7a,armeabi",
            "ro.product.cpu.abi64": "arm64-v8a"
        }.get(prop, "")

        self.locator._get_devices_information()

        self.assertIn("device123", self.locator._about_devices)
        device_info = self.locator._about_devices["device123"]
        self.assertEqual(device_info.model, "Pixel 6")
        self.assertEqual(device_info.brand, "google")

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbDeviceLocator._filter_storages_to_locate_cards')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.no_recursive_ls')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_information_about_device')
    def test_get_devices_information_multiple_devices(self, mock_get_info, mock_no_recursive_ls,
                                                      mock_filter_storages_to_locate_cards):
        """Verify the gathering of information on multiple devices"""
        self.locator._devices = ["device123", "device456"]

        def side_effect(prop):
            current = AdbChannel._selected_device_id  # obtén el device actual
            if current == "device123":
                return {"ro.product.model": "Pixel 6"}.get(prop, "Device1")
            else:
                return {"ro.product.model": "Galaxy S21"}.get(prop, "Device2")

        mock_get_info.side_effect = side_effect

        self.locator._get_devices_information()

        self.assertEqual(len(self.locator._about_devices), 2)
        self.assertIn("device123", self.locator._about_devices)
        self.assertIn("device456", self.locator._about_devices)

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbDeviceLocator._filter_storages_to_locate_cards')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.no_recursive_ls')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_devices')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_information_about_device')
    def test_get_devices_information_searches_if_no_devices(self, mock_get_info, mock_get_devices, mock_no_recursive_ls,
                                                            mock_filter_storages_to_locate_cards):
        """Verify the search of devices if the list is empty"""
        mock_get_devices.return_value = "List of devices attached\ndevice123\tdevice\n"
        mock_get_info.return_value = "test_value"

        self.locator._get_devices_information()

        mock_get_devices.assert_called_once()
        self.assertIn("device123", self.locator._about_devices)


    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbDeviceLocator._filter_storages_to_locate_cards')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.no_recursive_ls')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_information_about_device')
    def test_about_device_returns_device_info(self, mock_get_info, mock_no_recursive_ls,
                                              mock_filter_storages):
        """Verify that returns the information of the selected device"""
        self.locator._devices = ["device123"]
        mock_get_info.return_value = "test_value"

        self.locator._get_devices_information()
        result = self.locator.about_device("device123")

        self.assertIsNotNone(result)
        self.assertIsInstance(result, DeviceManager)

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_information_about_device')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbDeviceLocator._filter_storages_to_locate_cards')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.no_recursive_ls')
    def test_about_device_calls_get_devices_information_if_empty(self, mock_no_recursive_ls,
                                                                 mock_filter_storages,mock_get_info ):
        """Verify that the information is gathered if the dictionary is empty"""
        self.locator._devices = ["device123"]
        mock_get_info.return_value = "test_value"

        result = self.locator.about_device("device123")

        self.assertIsNotNone(result)
        self.assertTrue(mock_get_info.called)

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbDeviceLocator._filter_storages_to_locate_cards')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.no_recursive_ls')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_information_about_device')
    def test_about_device_returns_none_for_nonexistent_device(self, mock_get_info, mock_no_recursive_ls, mock_filter_storages):
        """Verify that None is returned when there are no devices"""
        self.locator._devices = ["device123"]
        mock_get_info.return_value = "test_value"

        self.locator._get_devices_information()
        result = self.locator.about_device("nonexistent_device")

        self.assertIsNone(result)
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbDeviceLocator._filter_storages_to_locate_cards')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.no_recursive_ls')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_information_about_device')
    def test_about_device_uses_cached_information(self, mock_get_info, mock_no_recursive_ls, mock_filter_storages):
        """Verify that cached information is returned in subsequent calls"""
        self.locator._devices = ["device123"]
        mock_get_info.return_value = "test_value"

        # First call
        self.locator.about_device("device123")
        first_call_count = mock_get_info.call_count

        # Second call (it should use the cache)
        self.locator.about_device("device123")

        # No debe hacer más llamadas a get_information_about_device
        self.assertEqual(mock_get_info.call_count, first_call_count)

    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbDeviceLocator._filter_storages_to_locate_cards')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.no_recursive_ls')
    @patch('qgis_plugin.localsync.device.adb_device_locator.AdbChannel.get_information_about_device')
    def test_get_devices_information_all_properties(self, mock_get_info, mock_no_recursive_ls, mock_filter_storages):
        """Verify that gather all the awaited properties"""
        self.locator._devices = ["device123"]
        mock_get_info.return_value = "test_value"

        self.locator._get_devices_information()
        device_info = self.locator._about_devices["device123"]

        self.assertIsInstance(device_info, DeviceManager)


if __name__ == '__main__':
    unittest.main()