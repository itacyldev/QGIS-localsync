import unittest
from unittest.mock import patch, MagicMock, mock_open
import subprocess
import os
from pathlib import Path

from qgis_plugin.localsync.channels.adb_channel import (
    AdbChannel,
    AdbErrorType,
    AdbStatus,
    FindAdb
)


class TestFindAdb(unittest.TestCase):

    @patch('qgis_plugin.localsync.channels.adb_channel.WINDOWS', True)
    @patch('qgis_plugin.localsync.channels.adb_channel.FindAdb.get_full_windows_path')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_find_adb_in_path_windows(self, mock_access, mock_isfile, mock_get_path):
        """ADB found on Windows PATH"""
        mock_get_path.return_value = r"C:\Windows\System32;C:\platform-tools"
        mock_isfile.return_value = True
        mock_access.return_value = True

        result = FindAdb.find_adb()

        self.assertEqual(result, r"C:\Windows\System32\adb.exe")

    @patch('qgis_plugin.localsync.channels.adb_channel.WINDOWS', False)
    @patch('os.environ.get')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_find_adb_in_path_linux(self, mock_access, mock_isfile, mock_env_get):
        """ADB found on Linux PATH"""
        mock_env_get.return_value = "/usr/bin:/usr/local/bin"
        mock_isfile.return_value = True
        mock_access.return_value = True

        result = FindAdb.find_adb()

        self.assertEqual(result, "/usr/bin/adb")

    @patch('qgis_plugin.localsync.channels.adb_channel.WINDOWS', True)
    @patch('qgis_plugin.localsync.channels.adb_channel.FindAdb.get_full_windows_path')
    @patch('qgis_plugin.localsync.channels.adb_channel.os.path.join')
    @patch('qgis_plugin.localsync.channels.adb_channel.os.path.isfile')
    @patch('qgis_plugin.localsync.channels.adb_channel.os.access')
    def test_find_adb_in_common_location_windows(self, mock_access, mock_isfile, mock_join, mock_get_path):
        """ADB found in common location of Windows"""
        mock_get_path.return_value = ""

        expected_path = r"C:\Users\Test\AppData\Local\Android\Sdk\platform-tools\adb.exe"

        # Mock os.path.join to behave like Windows
        def join_side_effect(*args):
            return '\\'.join(args)

        mock_join.side_effect = join_side_effect

        with patch.dict('os.environ', {
            'LOCALAPPDATA': r'C:\Users\Test\AppData\Local',
            'USERPROFILE': r'C:\Users\Test'
        }):
            def isfile_side_effect(path):
                return path == expected_path

            mock_isfile.side_effect = isfile_side_effect
            mock_access.return_value = True

            result = FindAdb.find_adb()

            self.assertEqual(result, expected_path)

    @patch('qgis_plugin.localsync.channels.adb_channel.WINDOWS', False)
    @patch('os.environ.get')
    @patch('os.path.isfile')
    @patch('os.access')
    def test_find_adb_not_found(self, mock_access, mock_isfile, mock_env_get):
        """ADB not found"""
        mock_env_get.return_value = ""
        mock_isfile.return_value = False

        result = FindAdb.find_adb()

        self.assertEqual(result, "")


class TestAdbChecker(unittest.TestCase):

    def setUp(self):
        AdbChannel._initialised = False
        AdbChannel._adb_path = ""
        self.checker = AdbChannel.AdbChecker()

    @patch('qgis_plugin.localsync.channels.adb_channel.AdbChannel')
    def test_check_adb_binary_not_found(self, mock_adb_channel):
        """ADB binary not found"""
        mock_adb_channel._adb_path = ""
        result = self.checker._check_adb_binary()

        self.assertFalse(result["available"])
        self.assertEqual(result["error_type"], AdbErrorType.ADB_NOT_FOUND)


    @patch('os.path.exists')
    @patch('os.access')
    @patch('qgis_plugin.localsync.channels.adb_channel.AdbChannel')
    def test_check_adb_binary_not_executable(self, mock_adb_channel, mock_access, mock_exists):
        """ADB binary found but not executable"""
        mock_adb_channel._adb_path = "/usr/bin/adb"
        mock_access.return_value = False
        mock_exists.return_value = True

        result = self.checker._check_adb_binary()

        self.assertFalse(result["available"])
        self.assertEqual(result["error_type"], AdbErrorType.ADB_NOT_EXECUTABLE)

    @patch('os.access')
    @patch('qgis_plugin.localsync.channels.adb_channel.AdbChannel')
    def test_check_adb_binary_success(self, mock_adb_channel, mock_access):
        """ADB binary not found in path"""
        mock_adb_channel._adb_path = "/usr/bin/adb"
        mock_access.return_value = True

        result = self.checker._check_adb_binary()

        self.assertFalse(result["available"])
        self.assertEqual(result["error_type"], AdbErrorType.ADB_NOT_FOUND)

    @patch('os.path.exists')
    @patch('os.access')
    @patch('qgis_plugin.localsync.channels.adb_channel.AdbChannel')
    def test_check_adb_binary_success(self, mock_adb_channel,  mock_access, mock_exists):
        """ADB binary found and executable"""
        mock_adb_channel._adb_path = "/usr/bin/adb"
        mock_access.return_value = True
        mock_exists.return_value = True

        result = self.checker._check_adb_binary()

        self.assertTrue(result["available"])
        self.assertEqual(result["path"], "/usr/bin/adb")

    @patch('subprocess.run')
    def test_check_adb_version_success(self, mock_run):
        """ADB version obtained correctly"""
        self.checker.adb_path = "/usr/bin/adb"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Android Debug Bridge version 1.0.41"
        )

        result = self.checker._check_adb_version()

        self.assertTrue(result["available"])
        self.assertIn("version", result)

    @patch('subprocess.run')
    def test_check_adb_version_timeout(self, mock_run):
        """Timeout when obtaining ADB version"""
        self.checker.adb_path = "/usr/bin/adb"
        mock_run.side_effect = subprocess.TimeoutExpired("adb", 5)

        result = self.checker._check_adb_version()

        self.assertFalse(result["available"])
        self.assertEqual(result["error_type"], AdbErrorType.SUBPROCESS_ERROR)

    @patch('subprocess.run')
    def test_check_adb_version_permission_error(self, mock_run):
        """Permission error when trying to verify ADB version"""
        self.checker.adb_path = "/usr/bin/adb"
        mock_run.side_effect = PermissionError()

        result = self.checker._check_adb_version()

        self.assertFalse(result["available"])
        self.assertEqual(result["error_type"], AdbErrorType.PERMISSIONS_ERROR)

    @patch('subprocess.run')
    def test_check_adb_server_success(self, mock_run):
        """ADB server not initialised correctly"""
        self.checker.adb_path = "/usr/bin/adb"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="daemon started successfully"
        )

        result = self.checker._check_adb_server()

        self.assertTrue(result["available"])

    @patch('subprocess.run')
    def test_check_adb_server_error(self, mock_run):
        """Error when initialising ADB server"""
        self.checker.adb_path = "/usr/bin/adb"
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="error: could not install *smartsocket* listener"
        )

        result = self.checker._check_adb_server()

        self.assertFalse(result["available"])
        self.assertEqual(result["error_type"], AdbErrorType.ADB_SERVER_ERROR)


class TestAdbChannelStaticMethods(unittest.TestCase):

    def setUp(self):
        AdbChannel._initialised = False
        AdbChannel._adb_path = ""
        AdbChannel._selected_device_id = ""

    @patch.object(AdbChannel.AdbChecker, 'check_availability')
    def test_is_available_success(self, mock_check):
        """ADB available"""
        mock_check.return_value = AdbStatus(
            available=True,
            error_type=None,
            error_message="ADB available",
            details={"adb_path": "/usr/bin/adb", "version": "1.0.41"}
        )

        result = AdbChannel.is_available()

        self.assertTrue(result.available)
        self.assertTrue(AdbChannel._initialised)
        self.assertEqual(AdbChannel._adb_path, "/usr/bin/adb")

    @patch.object(AdbChannel.AdbChecker, 'check_availability')
    def test_is_available_not_found(self, mock_check):
        """ADB not available"""
        mock_check.return_value = AdbStatus(
            available=False,
            error_type=AdbErrorType.ADB_NOT_FOUND,
            error_message="ADB not found",
            details={}
        )

        result = AdbChannel.is_available()

        self.assertFalse(result.available)
        self.assertFalse(AdbChannel._initialised)

    def test_set_and_get_default_device_id(self):
        """Set and obtain device ID"""
        test_id = "emulator-5554"

        AdbChannel.set_default_device_id(test_id)
        result = AdbChannel.get_default_device_id()

        self.assertEqual(result, test_id)

    @patch('subprocess.check_output')
    def test_get_devices(self, mock_check_output):
        """Obtain list of devices"""
        AdbChannel._initialised = True
        AdbChannel._adb_path = "/usr/bin/adb"
        mock_check_output.return_value = "List of devices attached\nemulator-5554\tdevice\n"

        result = AdbChannel.get_devices()

        self.assertIn("emulator-5554", result)
        mock_check_output.assert_called_once()


class TestAdbChannelFileOperations(unittest.TestCase):

    def setUp(self):
        AdbChannel._initialised = True
        AdbChannel._adb_path = "/usr/bin/adb"
        AdbChannel._selected_device_id = "emulator-5554"

    @patch('subprocess.check_output')
    def test_pull_file(self, mock_check_output):
        """Pull file from device"""
        mock_check_output.return_value = ""

        AdbChannel.pull_file("/sdcard/test.txt", "/output")

        mock_check_output.assert_called_once()
        call_args = mock_check_output.call_args[0][0]
        self.assertIn("pull", call_args)
        self.assertIn("/sdcard/test.txt", call_args)

    @patch('subprocess.check_output')
    def test_push_file(self, mock_check_output):
        """Push file to device"""
        mock_check_output.return_value = ""

        AdbChannel.push_file("/input/test.txt", "/sdcard")

        mock_check_output.assert_called_once()
        call_args = mock_check_output.call_args[0][0]
        self.assertIn("push", call_args)
        self.assertIn("/input/test.txt", call_args)

    @patch('subprocess.check_output')
    def test_no_recursive_ls(self, mock_check_output):
        """File list without recursion"""
        mock_check_output.return_value = "file1.txt\nfile2.txt\n"

        result = AdbChannel.no_recursive_ls("/sdcard")

        self.assertIn("file1.txt", result)
        mock_check_output.assert_called_once()

    @patch('subprocess.run')
    def test_check_directory_exists_true(self, mock_run):
        """Verify that the directory exists"""
        mock_run.return_value = MagicMock(stdout="0")

        result = AdbChannel.check_directory_exists("/sdcard/test")

        self.assertTrue(result)

    @patch('subprocess.run')
    def test_check_directory_exists_false(self, mock_run):
        """Verify that the directory does not exists"""
        mock_run.return_value = MagicMock(stdout="1")

        result = AdbChannel.check_directory_exists("/sdcard/test")

        self.assertFalse(result)

    @patch('subprocess.run')
    def test_check_file_exists_true(self, mock_run):
        """Verify that the file exists"""
        mock_run.return_value = MagicMock(stdout="0")

        result = AdbChannel.check_file_exists("/sdcard/test.txt")

        self.assertTrue(result)


class TestAdbChannelUtilities(unittest.TestCase):

    def test_convert_to_list_adb_search_directories_output(self):
        """Convert directories search output"""
        output = "/sdcard\n/sdcard/Download\n/sdcard/DCIM\n"

        result = AdbChannel._convert_to_list_adb_search_directories_output(output)

        self.assertEqual(len(result), 3)
        self.assertIn("/sdcard", result)
        self.assertIn("/sdcard/Download", result)

    @patch.object(AdbChannel, 'extract_file_type')
    def test_convert_to_dict_adb_ls_output(self, mock_extract):
        """Convert output of find path -type f to dictionary"""
        mock_extract.return_value = "file"
        output = "/sdcard/file1.txt\n/sdcard/file2.txt\n/sdcard/Download/image.jpg\n"

        result = AdbChannel._convert_to_path_list(output)

        self.assertIn(Path("/sdcard/file1.txt"), result)
        self.assertIn(Path("/sdcard/file2.txt"), result)
        self.assertIn(Path("/sdcard/Download/image.jpg"), result)

    def test_check_create_directory_device(self):
        """Verify the creation of the structure of the dictionaries"""
        AdbChannel._initialised = True
        AdbChannel._adb_path = "/usr/bin/adb"
        AdbChannel._selected_device_id = "emulator-5554"

        with patch.object(AdbChannel, 'create_directory_in_device') as mock_create:
            result = AdbChannel.check_create_directory_device(
                "/input/path/subdir",
                "/input/path",
                "/sdcard/output"
            )

            self.assertEqual(result, "subdir")


if __name__ == '__main__':
    unittest.main()