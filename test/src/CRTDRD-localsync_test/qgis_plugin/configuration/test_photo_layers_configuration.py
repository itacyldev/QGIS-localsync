import json
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from qgis_plugin.constants import QGIS_SCOPE_NAME, CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS, \
    WIZARD_PHOTO_LAYERS_GROUP_NAME, WIZARD_LAYERS_GROUP_NAME


def _make_project_mock(entry_map=None):
    """Crea un mock de QgsProject.instance() con estado propio."""
    entry_map = entry_map or {}
    project = MagicMock()

    def read_entry(scope, key, default=""):
        val = entry_map.get((scope, key), default)
        return val, bool(val)

    def write_entry(scope, key, value):
        entry_map[(scope, key)] = value

    project.readEntry.side_effect = read_entry
    project.writeEntry.side_effect = write_entry
    project.layerWillBeRemoved = MagicMock()
    project.layerWillBeRemoved.connect = MagicMock()
    return project


class TestPhotoLayersConfiguration(unittest.TestCase):

    def _make_config(self, entry_map=None):
        """Instancia PhotoLayersConfiguration con mocks aislados."""
        project_mock = _make_project_mock(entry_map)
        with patch("qgis_plugin.configuration.photo_layers_configuration.QgsProject") as qgs_project_cls, \
             patch("qgis_plugin.configuration.photo_layers_configuration.QgisLoggerHandler") as logger_cls, \
             patch("qgis_plugin.configuration.photo_layers_configuration.QMessageBox"):
            qgs_project_cls.instance.return_value = project_mock
            logger_cls.return_value.get_logger.return_value = MagicMock()
            from qgis_plugin.configuration.photo_layers_configuration import PhotoLayersConfiguration
            cfg = PhotoLayersConfiguration()
            cfg._project_mock = project_mock
            return cfg


    def test_add_to_config_happy_path(self):
        cfg = self._make_config()
        cfg.add_to_config("folder1", "layer1")
        self.assertEqual(cfg.config, {"folder1": "layer1"})

    def test_add_to_config_reemplaza_capa_duplicada(self):
        cfg = self._make_config()
        cfg.add_to_config("folderA", "layer1")
        cfg.add_to_config("folderB", "layer1")  # misma capa, distinta carpeta
        # Solo debe quedar la nueva entrada
        self.assertNotIn("folderA", cfg.config)
        self.assertEqual(cfg.config.get("folderB"), "layer1")

    def test_add_to_config_ignora_valores_vacios(self):
        cfg = self._make_config()
        cfg.restart_config()
        cfg.add_to_config("", "layer1")
        cfg.add_to_config("folder1", "")
        self.assertEqual(cfg.config, {})


    def test_restart_config_limpia_estado(self):
        cfg = self._make_config()
        cfg.add_to_config("folder1", "layer1")
        cfg.restart_config()
        self.assertEqual(cfg.config, {})

    def test_read_config_carga_json_valido(self):
        scope = QGIS_SCOPE_NAME
        key = CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS
        entry_map = {(scope, key): json.dumps({"f1": "l1"})}
        cfg = self._make_config(entry_map)
        self.assertEqual(cfg.config.get("f1"), "l1")

    def test_read_config_malformed_json_no_exception(self):
        scope = QGIS_SCOPE_NAME
        key = CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS
        entry_map = {(scope, key): "this_is_not_a_json"}
        try:
            cfg = self._make_config(entry_map)
        except Exception as e:
            self.fail(f"unexcepted read_config exception: {e}")

    # --- removed_layer_from_config ---