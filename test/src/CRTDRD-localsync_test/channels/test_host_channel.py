import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from qgis_plugin.localsync.channels.host_channel import HostChannel


class TestHostChannel(unittest.TestCase):

    def setUp(self):
        """Create temporal directory for tests"""
        self.test_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.test_dir)

    def test_create_directory_in_host(self):
        """Test directory creation"""
        new_dir = Path(self.test_dir) / "test_folder"
        HostChannel.create_directory_in_host(str(new_dir))
        self.assertTrue(new_dir.exists())

    def test_create_directory_in_host_nested(self):
        """Test nested directories creation"""
        nested_dir = Path(self.test_dir) / "level1" / "level2" / "level3"
        HostChannel.create_directory_in_host(str(nested_dir))
        self.assertTrue(nested_dir.exists())

    def test_create_dict_from_pc_path_with_files(self):
        """Test creation of dictionary from path with files"""
        # Crear estructura de prueba
        test_file1 = Path(self.test_dir) / "file1.txt"
        test_file2 = Path(self.test_dir) / "file2.py"
        test_file1.touch()
        test_file2.touch()

        result = HostChannel._create_list_from_pc_path(self.test_dir)

        expected_key = Path(self.test_dir).as_posix()
        self.assertIn(Path(expected_key+"/file1.txt"), result)
        self.assertIn(Path(expected_key+"/file2.py"), result)



    def test_create_dict_from_pc_path_single_file(self):
        """Test with a single file"""
        test_file = Path(self.test_dir) / "single.txt"
        test_file.touch()

        result = HostChannel._create_list_from_pc_path(test_file.as_posix())

        expected_key = Path(self.test_dir).as_posix()
        self.assertEqual(result, [Path(expected_key + "/single.txt")])

    def test_create_dict_from_pc_path_nested_structure(self):
        """Test with nested structure"""
        subdir = Path(self.test_dir) / "subdir"
        subdir.mkdir()
        (subdir / "nested.txt").touch()
        (Path(self.test_dir) / "root.txt").touch()

        result = HostChannel._create_list_from_pc_path(self.test_dir)

        self.assertEqual(len(result), 2)
        self.assertIn(Path(Path(self.test_dir).as_posix()+ "/root.txt"), result)
        self.assertIn(Path(subdir.as_posix()+"/nested.txt"), result)

    def test_create_dict_from_pc_path_empty_dir(self):
        """Test with empty directory"""
        empty_dir = Path(self.test_dir) / "empty"
        empty_dir.mkdir()

        result = HostChannel._create_list_from_pc_path(str(empty_dir))

        self.assertEqual(result, [])

    def test_create_dict_from_pc_path_nonexistent(self):
        """Test with nonexistent path"""
        result = HostChannel._create_list_from_pc_path("/nonexistent/path")
        self.assertEqual(result, [])



    def test_get_file_list_with_file_filters(self):
        """Test get_file_list with file filters"""
        test_file = Path(self.test_dir) / "test.txt"
        test_file.touch()

        result = HostChannel.get_file_list(self.test_dir, ["*.txt"], [])

        self.assertIn(Path(self.test_dir+"/test.txt"), result)

    def test_get_file_list_with_directory_filters(self):
        """Test get_file_list with directory filters"""
        subdir = Path(self.test_dir) / "subdir"
        subdir.mkdir()
        (subdir / "file.txt").touch()

        result = HostChannel.get_file_list(self.test_dir, ["*/subdir/*"],[])

        self.assertEqual(result, [Path(subdir.as_posix() + "/file.txt")])


    def test_get_directory_list(self):
        """Test get_directory_list"""
        subdir = Path(self.test_dir) / "subdir"
        subdir.mkdir()


        result = HostChannel.get_file_list(self.test_dir, ["*/subdir/*"], [])

        self.assertIsInstance(result, list)


if __name__ == '__main__':
    unittest.main()