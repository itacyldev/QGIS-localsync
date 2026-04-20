import unittest
from unittest.mock import Mock, patch, call
from pathlib import Path

from qgis_plugin.localsync.transporter.mtp_transporter import MtpTransporter


class TestMtpTransporter(unittest.TestCase):

    def setUp(self):
        self.transporter = MtpTransporter()

    def test_get_subfolder_basic(self):
        """Testing the extraction of basic subfolder"""
        source = "/storage/cartodroid"
        directory_path = Path("/storage/cartodroid/projects/proyecto1/file1.txt")

        result = self.transporter.get_subfolder(source, directory_path)

        self.assertEqual(result, "/projects/proyecto1")

    def test_get_subfolder_with_trailing_slashes(self):
        """Testing that the end slashes are managed correctly"""
        source = "/storage/cartodroid/"
        directory_path = Path("/storage/cartodroid/projects/file1.txt")

        result = self.transporter.get_subfolder(source, directory_path)

        self.assertEqual(result, "/projects")

    def test_get_subfolder_same_path(self):
        """Testing when source y directory_path are the same"""
        source = "/storage/cartodroid"
        directory_path = Path("/storage/cartodroid")

        result = self.transporter.get_subfolder(source, directory_path)

        self.assertEqual(result, "")

    def test_get_subfolder_directory_shorter_than_source(self):
        """Testing when directory is shorter than source"""
        source = "/storage/cartodroid/projects"
        directory_path = Path("/storage/cartodroid")

        result = self.transporter.get_subfolder(source, directory_path)

        self.assertEqual(result, "")

    @patch('qgis_plugin.localsync.transporter.mtp_transporter.MtpChannel')
    def test_push_creates_folders_and_transfers_files(self, mock_mtp_channel):
        """Test that push create folders and transfer files"""
        file_list = [Path("/local/source/dir1/file1.txt"), Path("/local/source/dir1/file2.txt"),
                     Path("/local/source/dir2/file3.txt")]
        source = "/local/source"
        destination = "/device/destination"

        self.transporter.push(file_list, source, destination)

        # Verificar creación de carpeta base
        mock_mtp_channel.create_path_folder.assert_any_call("/device/destination")

        # Verificar creación de subcarpetas
        mock_mtp_channel.create_path_folder.assert_any_call("/device/destination/dir1")
        mock_mtp_channel.create_path_folder.assert_any_call("/device/destination/dir2")

        # Verificar transferencia de archivos
        self.assertEqual(mock_mtp_channel.push_file.call_count, 3)

    @patch('qgis_plugin.localsync.transporter.mtp_transporter.MtpChannel')
    def test_push_with_trailing_slash_in_destination(self, mock_mtp_channel):
        """Test that push remove the end slash"""
        file_list = [Path("/local/source/file.txt")]
        source = "/local/source"
        destination = "/device/destination/"

        self.transporter.push(file_list, source, destination)

        mock_mtp_channel.create_path_folder.assert_called_with("/device/destination")

    @patch('qgis_plugin.localsync.transporter.mtp_transporter.HostChannel')
    @patch('qgis_plugin.localsync.transporter.mtp_transporter.MtpChannel')
    def test_pull_creates_directories_and_transfers_files(self, mock_mtp_channel, mock_host_channel):
        """Test if pull create directories and transfer files"""

        file_list = [Path("/device/source/dir1/file1.txt"), Path("/device/source/dir1/file2.txt"),
                     Path("/device/source/dir2/file3.txt")]
        source = "/device/source"
        destination = "/local/destination"

        self.transporter.pull(file_list, source, destination)

        # Verificar creación de directorio base
        mock_host_channel.create_directory_in_host.assert_any_call("/local/destination")

        # Verificar creación de subdirectorios
        mock_host_channel.create_directory_in_host.assert_any_call("/local/destination/dir1")
        mock_host_channel.create_directory_in_host.assert_any_call("/local/destination/dir2")

        # Verificar transferencia de archivos
        self.assertEqual(mock_mtp_channel.pull_file.call_count, 3)

    @patch('qgis_plugin.localsync.transporter.mtp_transporter.FileScanner')
    @patch('qgis_plugin.localsync.transporter.mtp_transporter.MtpChannel')
    def test_get_file_list_without_filters(self, mock_mtp_channel, mock_file_scanner):
        """Test obtaining the list of files without filters"""
        input_path = "/device/path"
        expected_files = [Path("/device/path/file1.txt"), Path("/device/path/file2.txt")]
        mock_mtp_channel.get_file_list.return_value = expected_files
        mock_file_scanner.filter_files_list.return_value = expected_files

        result = self.transporter.get_file_list(input_path, [],[], False)

        mock_mtp_channel.get_file_list.assert_called_once_with("/device/path")
        self.assertEqual(result, expected_files)

    @patch('qgis_plugin.localsync.transporter.mtp_transporter.FileScanner')
    @patch('qgis_plugin.localsync.transporter.mtp_transporter.MtpChannel')
    def test_get_file_list_with_filters(self, mock_mtp_channel, mock_file_scanner):
        """Test obtaining the list of files filtered"""
        input_path = "/device/path/"
        mock_filter = Mock()
        mock_filter.directories = False

        mock_mtp_channel.get_file_list.return_value = [Path("/device/path/file.txt")]
        mock_file_scanner.filter_files_list.return_value = [Path("/device/path/file.txt")]

        result = self.transporter.get_file_list(input_path, [mock_filter], [mock_filter], False)

        mock_mtp_channel.get_file_list.assert_called_once_with("/device/path")
        mock_file_scanner.filter_files_list.assert_called()


    @patch('qgis_plugin.localsync.transporter.mtp_transporter.FileScanner')
    @patch('qgis_plugin.localsync.transporter.mtp_transporter.MtpChannel')
    def test_get_directory_list_applies_filters(self, mock_mtp_channel, mock_file_scanner):
        """Test obtaining the list of directories filtered"""
        input_path = "/device/path"
        mock_filter = Mock()

        mock_mtp_channel.get_directories_list.return_value = [Path("/device/path/dir1"), Path("/device/path/dir2")]
        mock_file_scanner.filter_files_list.return_value = [Path("/device/path/dir1")]

        result = self.transporter.get_file_list(input_path, [mock_filter],[mock_filter], True)

        mock_mtp_channel.get_directories_list.assert_called_once_with("/device/path")
        mock_file_scanner.filter_files_list.assert_called_with([Path("/device/path/dir1")], [mock_filter], False)
        self.assertEqual(result, [Path("/device/path/dir1")])


if __name__ == '__main__':
    unittest.main()