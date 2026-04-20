import unittest
from unittest.mock import Mock, patch, call
from pathlib import Path
from qgis_plugin.localsync.transporter.adb_transporter import AdbTransporter


class TestAdbTransporter(unittest.TestCase):

    def setUp(self):
        self.transporter = AdbTransporter()

    @patch('qgis_plugin.localsync.transporter.adb_transporter.HostChannel')
    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    def test_pull_creates_destination_directory(self, mock_adb, mock_host):
        file_list = [Path('/source/dir/file1.txt'), Path('/source/dir/file2.txt')]
        source = '/source'
        destination = '/dest'

        self.transporter.pull(file_list, source, destination)

        mock_host.create_directory_in_host.assert_called()

    @patch('qgis_plugin.localsync.transporter.adb_transporter.HostChannel')
    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    def test_pull_files_from_device(self, mock_adb, mock_host):
        file_list = [Path('/source/dir/file1.txt')]
        source = '/source'
        destination = '/dest'

        self.transporter.pull(file_list, source, destination)

        mock_adb.pull_file.assert_called_once()

    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    def test_push_creates_base_directory(self, mock_adb):
        mock_adb.check_directory_exists.return_value = True
        mock_adb.check_create_directory_device.return_value = '/subdir'

        file_list = [Path('/source/dir/file1.txt')]
        source = '/source'
        destination = '/dest'

        self.transporter.push(file_list, source, destination)

        self.transporter.create_base_output_directory_in_device = Mock()
        self.transporter.push(file_list, source, destination)

    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    def test_push_files_to_device(self, mock_adb):
        mock_adb.check_directory_exists.return_value = True
        mock_adb.check_create_directory_device.return_value = ''

        file_list = [Path('/source/dir/file1.txt'), Path('/source/dir/file2.txt')]
        source = '/source'
        destination = '/dest'

        self.transporter.push(file_list, source, destination)

        assert mock_adb.push_file.call_count == 2

    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    def test_create_base_output_directory_already_exists(self, mock_adb):
        mock_adb.check_directory_exists.return_value = True

        result = self.transporter.create_base_output_directory_in_device('/existing/path')

        self.assertTrue(result)
        mock_adb.create_directory_in_device.assert_not_called()

    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    def test_create_base_output_directory_creates_new(self, mock_adb):
        mock_adb.check_directory_exists.return_value = False
        mock_adb.create_directory_in_device.return_value = True

        result = self.transporter.create_base_output_directory_in_device('/new/path')

        self.assertTrue(result)
        mock_adb.create_directory_in_device.assert_called_once()

    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    @patch('qgis_plugin.localsync.transporter.adb_transporter.FileScanner')
    def test_get_file_list_directory_exists(self, mock_scanner, mock_adb):
        mock_adb.check_directory_exists.return_value = True
        mock_adb.get_file_list.return_value = ['/path/file1.txt']
        mock_scanner.filter_files_list.return_value = ['/path/file1.txt']

        result = self.transporter.get_file_list('/input/path', [], [], False)

        self.assertEqual(result, ['/path/file1.txt'])
        mock_adb.get_file_list.assert_called_once()

    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    def test_get_file_list_path_not_exists(self, mock_adb):
        mock_adb.check_directory_exists.return_value = False
        mock_adb.check_file_exists.return_value = False

        result = self.transporter.get_file_list('/nonexistent', [], [], False)

        self.assertEqual(result, [])

    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    @patch('qgis_plugin.localsync.transporter.adb_transporter.FileScanner')
    def test_get_directory_list(self, mock_scanner, mock_adb):
        mock_adb.check_directory_exists.return_value = True
        mock_adb.get_directories_list.return_value = ['/dir1', '/dir2']
        mock_scanner.filter_files_list.return_value = ['/dir1', '/dir2']

        result = self.transporter.get_file_list('/input/path', [],[], True)

        self.assertEqual(result, ['/dir1', '/dir2'])
        mock_adb.get_directories_list.assert_called_once()

    @patch('qgis_plugin.localsync.transporter.adb_transporter.AdbChannel')
    @patch('qgis_plugin.localsync.transporter.adb_transporter.FileScanner')
    def test_get_directory_list_path_not_exists(self, mock_scanner, mock_adb):
        mock_adb.check_directory_exists.return_value = False
        mock_adb.get_directories_list.return_value = []
        mock_scanner.filter_files_list.return_value = []

        result = self.transporter.get_file_list('/nonexistent', [], [], True)

        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()