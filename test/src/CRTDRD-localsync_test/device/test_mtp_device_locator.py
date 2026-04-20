import unittest
from unittest.mock import Mock, patch, call
from qgis_plugin.localsync.device.mtp_device_locator import MtpDeviceLocator


class TestMtpDeviceLocator(unittest.TestCase):

    def setUp(self):
        self.locator = MtpDeviceLocator()

    def test_init_empty_state(self):
        """Test of empty structures while initialisating"""
        self.assertEqual(self.locator._devices, [])
        self.assertEqual(self.locator._devices_information, {})
        self.assertEqual(self.locator._devices_information_dict, {})

    def test_get_connected_devices_empty(self):
        """Testing the obtaining of devices when there is none"""
        result = self.locator.get_connected_devices()
        self.assertEqual(result, [])

    @patch('qgis_plugin.localsync.device.mtp_device_locator.MtpChannel')
    def test_search_for_connected_devices_with_valid_path(self, mock_mtp_channel):
        """Testing device searching with valid path"""
        mock_mtp_channel.get_devices.return_value = [
            {
                "path": "USB#VID_1234#PID_5678#SERIAL123",
                "name": "Device1",
                "type": "Phone"
            }
        ]

        self.locator.search_for_connected_devices()

        self.assertEqual(len(self.locator._devices), 1)
        self.assertEqual(self.locator._devices[0], "PID_5678")
        self.assertIn("pid_5678", self.locator._devices_information_dict)

    @patch('qgis_plugin.localsync.device.mtp_device_locator.MtpChannel')
    def test_search_for_connected_devices_with_invalid_path(self, mock_mtp_channel):
        """Testing the search of devices when the path does not have a valid format"""
        mock_mtp_channel.get_devices.return_value = [
            {
                "path": "InvalidPath",
                "name": "Device1",
                "type": "Phone"
            }
        ]

        self.locator.search_for_connected_devices()

        self.assertEqual(len(self.locator._devices), 1)
        self.assertEqual(self.locator._devices[0], "Device1")

    @patch('qgis_plugin.localsync.device.mtp_device_locator.MtpChannel')
    def test_search_for_connected_devices_stores_information(self, mock_mtp_channel):
        """Testng that the device information is stored correctly"""
        mock_mtp_channel.get_devices.return_value = [
            {
                "path": "USB#VID#DEV123#SERIAL",
                "name": "MyPhone",
                "type": "Phone"
            }
        ]

        self.locator.search_for_connected_devices()

        device_info = self.locator._devices_information_dict["dev123"]
        self.assertEqual(device_info["name"], "MyPhone")
        self.assertEqual(device_info["type"], "Phone")

    @patch('qgis_plugin.localsync.device.mtp_device_locator.MtpChannel')
    @patch('qgis_plugin.localsync.device.mtp_device_locator.DeviceManager')
    def test_get_devices_information_creates_device_managers(self, mock_device_manager, mock_mtp_channel):
        """Test that _get_devices_information created a DeviceManager correctly"""
        self.locator._devices = ["device123"]
        self.locator._devices_information_dict = {
            "device123": {
                "name": "TestDevice",
                "path": "/test/path",
                "type": "Phone"
            }
        }

        mock_mtp_channel.get_information_about_device.return_value = {
            "description": "Test Model",
            "manufacturer": "TestBrand"
        }
        mock_mtp_channel.get_storages.return_value = ["/storage1", "/storage2"]

        self.locator._get_devices_information()

        mock_device_manager.assert_called_once()
        call_kwargs = mock_device_manager.call_args[1]
        self.assertEqual(call_kwargs["device_id"], "device123")
        self.assertEqual(call_kwargs["name"], "TestDevice")
        self.assertEqual(call_kwargs["connection_type"], "mtp")


    @patch('qgis_plugin.localsync.device.mtp_device_locator.MtpChannel')
    @patch('qgis_plugin.localsync.device.mtp_device_locator.DeviceManager')
    def test_about_device_returns_device_info(self, mock_device_manager, mock_mtp_channel):
        """Test that about_device returns information about the device"""
        mock_device = Mock()
        self.locator._devices = ["device123"]
        self.locator._devices_information = {"device123": mock_device}
        self.locator._devices_information_dict = {"device123": {"name": "Test", "path": "/path"}}

        result = self.locator.about_device("device123")

        self.assertEqual(result, mock_device)

    @patch('qgis_plugin.localsync.device.mtp_device_locator.MtpChannel')
    @patch('qgis_plugin.localsync.device.mtp_device_locator.DeviceManager')
    def test_about_device_with_force_search(self, mock_device_manager, mock_mtp_channel):
        """Test that force_search reloads the device information"""
        self.locator._devices = ["device123"]
        self.locator._devices_information_dict = {
            "device123": {"name": "Test", "path": "/path", "type": "Phone"}
        }

        mock_mtp_channel.get_information_about_device.return_value = {
            "description": "Model",
            "manufacturer": "Brand"
        }
        mock_mtp_channel.get_storages.return_value = []

        self.locator.about_device("device123", force_search=True)

        mock_mtp_channel.get_information_about_device.assert_called()

    @patch('qgis_plugin.localsync.device.mtp_device_locator.MtpChannel')
    def test_about_device_returns_none_for_unknown_device(self, mock_mtp_channel):
        """Test that return None for unknown device"""

        result = self.locator.about_device("unknown_device")

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()