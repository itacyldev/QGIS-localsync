import unittest
from unittest.mock import MagicMock, patch


def _make_project_data_mock(name="TestProject"):
    project = MagicMock()
    project.project_name = name
    project.to_dict.return_value = {"name": name}
    return project


class TestProjectWizardData(unittest.TestCase):

    def setUp(self):
        self.mock_project_data_class = MagicMock()
        patcher = patch("qgis_plugin.dialog.project_wizard.project_wizard_data.ProjectData", self.mock_project_data_class)
        self.addCleanup(patcher.stop)
        patcher.start()

        from qgis_plugin.dialog.project_wizard.project_wizard_data import ProjectWizardData
        self.PWD = ProjectWizardData

    # --- to_dict / from_dict ---

    def test_to_dict_and_from_dict_roundtrip(self):
        project_mock = _make_project_data_mock("MyProject")
        self.mock_project_data_class.from_dict.return_value = project_mock

        original = self.PWD(
            _project_selected=project_mock,
            config_box_selected=True,
            image_box_selected=False,
            data_box_selected=True,
            data_list_selected_files=["db1.sqlite", "db2.sqlite"],
            data_list_full=["db1.sqlite", "db2.sqlite", "db3.sqlite"],
            data_selected_layers={"db1.sqlite": ["layer1"]},
        )

        d = original.to_dict()
        restored = self.PWD.from_dict(d)

        self.assertEqual(restored.config_box_selected, True)
        self.assertEqual(restored.data_list_selected_files, ["db1.sqlite", "db2.sqlite"])
        self.assertEqual(restored.data_selected_layers, {"db1.sqlite": ["layer1"]})

    def test_from_dict_with_empty_dict_returns_empty_instance(self):
        # Dict vacio no contiene las claves requeridas: devuelve ProjectWizardData()
        result = self.PWD.from_dict({})
        self.assertIsInstance(result, self.PWD)
        self.assertIsNone(result.get_project_selected())
        self.assertFalse(result.config_box_selected)

    # --- change_project ---

    def test_change_project_resets_selections_when_project_changes(self):
        old_project = _make_project_data_mock("OldProject")
        new_project = _make_project_data_mock("NewProject")

        pwd = self.PWD(
            _project_selected=old_project,
            config_box_selected=True,
            data_list_selected_files=["db.sqlite"],
        )
        pwd.change_project(new_project)

        self.assertFalse(pwd.config_box_selected)
        self.assertEqual(pwd.data_list_selected_files, [])
        self.assertEqual(pwd.get_project_selected(), new_project)

    def test_change_project_keeps_selections_when_same_project(self):
        project = _make_project_data_mock("SameProject")

        pwd = self.PWD(
            _project_selected=project,
            config_box_selected=True,
            data_list_selected_files=["db.sqlite"],
        )
        pwd.change_project(project)

        self.assertTrue(pwd.config_box_selected)
        self.assertEqual(pwd.data_list_selected_files, ["db.sqlite"])


if __name__ == "__main__":
    unittest.main()