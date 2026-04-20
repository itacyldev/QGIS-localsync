import unittest
from pathlib import Path

from qgis_plugin.localsync.data_actions.file_scanner import FileScanner


class TestFileScanner(unittest.TestCase):


    def test_filter_file_list_include(self):
        '''Testing include filter'''
        file_list = [Path("/sdcard/file1.txt"),Path("/sdcard/file2.txt"),Path("/sdcard/file3.txt"),
                     Path("/sdcard/script.txt"),Path("/sdcard/doc.txt"),Path("/sdcard/file1.py")]
        glob_filters = ["*.txt"]
        include = True

        new_file_list = FileScanner.filter_files_list(file_list,glob_filters,include)

        self.assertNotIn("/sdcard/file1.py", new_file_list)


    def test_filter_file_list_exclude(self):
        '''Testing exclude filter'''
        file_list = [Path("/sdcard/file1.txt"),Path("/sdcard/file2.txt"),Path("/sdcard/file3.txt"),
                     Path("/sdcard/script.txt"),Path("/sdcard/doc.txt"),Path("/sdcard/file1.py")]
        glob_filters = ["*.txt"]
        include = False

        new_file_list = FileScanner.filter_files_list(file_list,glob_filters,include)

        self.assertIn(Path("/sdcard/file1.py"), new_file_list)

    def test_filter_file_list_more_include(self):
        '''Testing exclude filter'''
        file_list = [Path("/sdcard/file1.txt"), Path("/sdcard/file2.txt"), Path("/sdcard/file3.txt"),
                     Path("/sdcard/script.txt"), Path("/sdcard/doc.txt"), Path("/sdcard/file1.py")]
        glob_filters = ["file1*","script*"]
        include = True

        new_file_list = FileScanner.filter_files_list(file_list, glob_filters, include)

        self.assertIn(Path("/sdcard/file1.txt"), new_file_list)
        self.assertIn(Path("/sdcard/script.txt"), new_file_list)
        self.assertIn(Path("/sdcard/file1.py"), new_file_list)



if __name__ == '__main__':
    unittest.main()