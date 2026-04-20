import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from qgis_plugin.localsync.project.project_manager import ProjectManager


class TestGetProjectNameFromPath(unittest.TestCase):

    def test_happy_path(self):
        path = Path("/Internal/cartodroid/projects/my_project/layers")
        self.assertEqual(ProjectManager.get_project_name_from_path(path, "projects"), "my_project")

    def test_no_match(self):
        path = Path("/Internal/other/folder")
        self.assertIsNone(ProjectManager.get_project_name_from_path(path, "projects"))

    def test_at_root_of_splitter(self):
        path = Path("/Internal/cartodroid/projects")
        self.assertIsNone(ProjectManager.get_project_name_from_path(path, "projects"))


class TestListProjects(unittest.TestCase):

    def setUp(self):
        self.sync_engine = MagicMock()
        self.manager = ProjectManager(self.sync_engine)
        self.manager.logger = MagicMock()

    def test_no_devices(self):
        self.sync_engine.discover_devices.return_value = ([], False)
        self.assertEqual(self.manager.list_projects(), [])

    def test_finds_project(self):
        device = MagicMock()
        device.device_id = "dev1"
        device.storages = ["/Internal"]
        self.sync_engine.discover_devices.return_value = ([device], True)
        self.sync_engine.list_files.return_value = [
            Path("/Internal/projects/my_project/layers/layer.gpkg")
        ]
        with patch('qgis_plugin.localsync.project.project_manager.CARTODRUID_PROJECT_SPLITTERS', ["projects"]):
            result = self.manager.list_projects()
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].project_name, "my_project")

    def test_no_duplicates(self):
        device = MagicMock()
        device.device_id = "dev1"
        device.storages = ["/Internal"]
        self.sync_engine.discover_devices.return_value = ([device], True)
        self.sync_engine.list_files.return_value = [
            Path("/Internal/projects/proj_a/file1.gpkg"),
            Path("/Internal/projects/proj_a/file2.gpkg"),
        ]
        with patch('qgis_plugin.localsync.project.project_manager.CARTODRUID_PROJECT_SPLITTERS', ["projects"]):
            result = self.manager.list_projects()
        self.assertEqual(len(result), 1)