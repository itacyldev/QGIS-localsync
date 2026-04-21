import unittest
from unittest.mock import MagicMock
from qgis_plugin.tasks.copy_folders_from_device import CopyFoldersFromDevice


class TestCopyFoldersFromDevice(unittest.TestCase):

    def _make_task(self, config=None):
        if config is None:
            config = [{"source": "/pc/path", "destination": "/device/path", "includes": [], "excludes": []}]
        task = CopyFoldersFromDevice.__new__(CopyFoldersFromDevice)
        task.s_eng = MagicMock()
        task.config = config
        task.device = MagicMock()
        task.s_listener = MagicMock()
        task.exception = None
        task.result = False
        task.canceled = False
        task.logger = MagicMock()
        task.key_filter_word = ["pictures", "values"]
        return task

    def test_run_happy_path(self):
        task = self._make_task()
        task.s_eng.recreate_device_structure.return_value = True

        self.assertTrue(task.run())
        self.assertTrue(task.result)
        self.assertIsNone(task.exception)

    def test_run_multiple_configs_all_ok(self):
        config = [
            {"source": "/pc/a", "destination": "/dev/a", "includes": [], "excludes": []},
            {"source": "/pc/b", "destination": "/dev/b", "includes": [], "excludes": []},
        ]
        task = self._make_task(config)
        task.s_eng.recreate_device_structure.return_value = True

        self.assertTrue(task.run())
        self.assertEqual(task.s_eng.recreate_device_structure.call_count, 2)

    def test_run_exception(self):
        task = self._make_task()
        task.s_eng.recreate_device_structure.side_effect = RuntimeError("device error")

        self.assertFalse(task.run())
        self.assertIsInstance(task.exception, RuntimeError)