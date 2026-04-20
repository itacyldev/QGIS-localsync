import sys
import unittest
from unittest.mock import MagicMock

from PyQt5.QtWidgets import QApplication

app = QApplication.instance() or QApplication(sys.argv)


class TestAddLayers(unittest.TestCase):

    def setUp(self):
        from qgis_plugin.dialog.project_wizard.wizard_pages.add_layers import AddLayers
        self.page = AddLayers.__new__(AddLayers)
        self.page.tree_layers = MagicMock()
        self.page.tree_layers.invisibleRootItem.return_value = MagicMock(
            childCount=MagicMock(return_value=0)
        )


    def test_get_layer_icon_known_type_returns_icon(self):
        icon = self.page.get_layer_icon("Point")
        self.assertIsNotNone(icon)

    def test_get_layer_icon_unknown_type_returns_default_icon(self):
        icon = self.page.get_layer_icon("Unknown")
        self.assertIsNotNone(icon)

    def test_add_new_layer_creates_key_if_missing(self):
        wiz = MagicMock()
        wiz.current_options.data_selected_layers = {}
        self.page.wizard = MagicMock(return_value=wiz)

        self.page.add_new_layer_to_save_state("file.sqlite", "layer1")

        self.assertIn("file.sqlite", wiz.current_options.data_selected_layers)
        self.assertIn("layer1", wiz.current_options.data_selected_layers["file.sqlite"])

    def test_remove_layer_deletes_key_when_list_becomes_empty(self):
        wiz = MagicMock()
        wiz.current_options.data_selected_layers = {"file.sqlite": ["layer1"]}
        self.page.wizard = MagicMock(return_value=wiz)

        self.page.look_and_remove_value_and_key("file.sqlite", "layer1")

        self.assertNotIn("file.sqlite", wiz.current_options.data_selected_layers)

    def test_remove_layer_ignores_missing_key(self):
        wiz = MagicMock()
        wiz.current_options.data_selected_layers = {}
        self.page.wizard = MagicMock(return_value=wiz)

        try:
            self.page.look_and_remove_value_and_key("nonexistent.sqlite", "layer1")
        except Exception as exc:
            self.fail(f"look_and_remove_value_and_key raised an unexpected exception: {exc}")


if __name__ == "__main__":
    unittest.main()