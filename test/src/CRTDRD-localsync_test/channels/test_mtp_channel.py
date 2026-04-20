import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from qgis_plugin.localsync.channels.mtp_channel import MtpChannel, MtpErrorType


class TestMtpChecker(unittest.TestCase):

    def setUp(self):
        self.checker = MtpChannel.MtpChecker()

    def test_check_os_windows(self):
        with patch('platform.system', return_value='Windows'):
            self.assertTrue(self.checker._check_os())

    def test_check_os_linux(self):
        with patch('platform.system', return_value='Linux'):
            self.assertFalse(self.checker._check_os())

    @patch('platform.system', return_value='Linux')
    def test_check_availability_non_windows(self, _):
        status = self.checker.check_availability()
        self.assertFalse(status.available)
        self.assertEqual(status.error_type, MtpErrorType.SO_NOT_SUPPORTED)

    @patch('platform.system', return_value='Windows')
    def test_check_availability_ok(self, _):
        self.checker._check_powershell = MagicMock(return_value={"available": True, "version": "5.1"})
        self.checker._check_shell_application = MagicMock(return_value={"available": True})
        self.assertTrue(self.checker.check_availability().available)

    @patch('platform.system', return_value='Windows')
    def test_check_availability_ps_not_found(self, _):
        self.checker._check_powershell = MagicMock(return_value={
            "available": False,
            "error_type": MtpErrorType.POWERSHELL_NOT_FOUND,
            "message": "not found"
        })
        status = self.checker.check_availability()
        self.assertFalse(status.available)
        self.assertEqual(status.error_type, MtpErrorType.POWERSHELL_NOT_FOUND)


class TestMtpChannelStatics(unittest.TestCase):

    def setUp(self):
        MtpChannel._selected_device_id_path = ""

    def test_set_and_get_selected_device_id_path(self):
        MtpChannel.set_selected_device_id_path("::some-guid")
        self.assertEqual(MtpChannel.get_selected_device_id_path(), "::some-guid")

    def test_check_directory_exists_true(self):
        with patch.object(MtpChannel, 'get_result_script', return_value="false"):
            self.assertTrue(MtpChannel.check_directory_exists("Internal/folder"))

    def test_check_directory_exists_false(self):
        with patch.object(MtpChannel, 'get_result_script', return_value="true"):
            self.assertFalse(MtpChannel.check_directory_exists("Internal/nonexistent"))

    def test_check_directory_exists_empty(self):
        with patch.object(MtpChannel, 'get_result_script', return_value=""):
            self.assertFalse(MtpChannel.check_directory_exists("Internal/folder"))

    def test_get_storages_single(self):
        with patch.object(MtpChannel, 'get_result_script', return_value='{"Name": "Internal shared storage"}'):
            self.assertEqual(MtpChannel.get_storages("::guid"), ["/Internal shared storage"])

    def test_get_storages_multiple(self):
        with patch.object(MtpChannel, 'get_result_script', return_value='[{"Name": "Internal"}, {"Name": "SD Card"}]'):
            self.assertEqual(MtpChannel.get_storages("::guid"), ["/Internal", "/SD Card"])

    def test_get_storages_empty(self):
        with patch.object(MtpChannel, 'get_result_script', return_value=""):
            self.assertEqual(MtpChannel.get_storages("::guid"), [])

    def test_get_file_list_empty(self):
        with patch.object(MtpChannel, 'get_result_script', return_value=""):
            self.assertEqual(MtpChannel.get_file_list("/Internal/folder"), [])

    def test_get_file_list_returns_paths(self):
        with patch.object(MtpChannel, 'get_result_script',
                          return_value="/Internal/folder/file1.gpkg\n/Internal/folder/file2.gpkg\n"):
            result = MtpChannel.get_file_list("/Internal/folder")
        self.assertEqual(result, [Path("/Internal/folder/file1.gpkg"), Path("/Internal/folder/file2.gpkg")])

    def test_get_devices_empty(self):
        with patch.object(MtpChannel, 'get_result_script', return_value=""):
            self.assertEqual(MtpChannel.get_devices(), [])

    def test_get_devices_single(self):
        with patch.object(MtpChannel, 'get_result_script', return_value='{"Name": "My Phone", "Path": "::guid"}'):
            result = MtpChannel.get_devices()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["Name"], "My Phone")