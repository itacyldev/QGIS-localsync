# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, patch

from qgis.core import QgsTask

from qgis_plugin.tasks.read_devices import ReadDevices


class TestReadDevices(unittest.TestCase):

    def setUp(self):
        """Initial configuration for every test"""
        self.mock_s_eng = Mock()
        self.task = ReadDevices(self.mock_s_eng)

    def test_initialization(self):
        """Testing the correct initialisation of the task"""
        self.assertEqual(self.task.s_eng, self.mock_s_eng)
        self.assertIsNone(self.task.result)

    def test_run_success(self):
        """Test de ejecución exitosa"""
        expected_devices = [Mock(), Mock(), Mock()]
        self.mock_s_eng.discover_devices.return_value = expected_devices, True

        result = self.task.run()

        self.assertTrue(result)
        self.assertEqual(self.task.result, expected_devices)
        self.mock_s_eng.discover_devices.assert_called_once()

    def test_run_success_empty_list(self):
        """Testing successful execution with an empty list"""
        self.mock_s_eng.discover_devices.return_value = [], True

        result = self.task.run()

        self.assertTrue(result)
        self.assertEqual(self.task.result, [])

    def test_run_exception_handling(self):
        """Testing exception handling"""
        error_message = "Connection error"
        self.mock_s_eng.discover_devices.side_effect = Exception(error_message)

        result = self.task.run()

        self.assertFalse(result)
        self.assertIsNone(self.task.result)

    def test_run_different_exception_types(self):
        """Testing with different types of exceptions"""
        self.mock_s_eng.discover_devices.side_effect = RuntimeError("Runtime error")
        result = self.task.run()
        self.assertFalse(result)

        self.task.error = None

        self.mock_s_eng.discover_devices.side_effect = ValueError("Value error")
        result = self.task.run()
        self.assertFalse(result)

    def test_finished_success(self):
        """Testing finished method successful ending"""
        self.task.finished(True)

    def test_finished_failure(self):
        """Testing the finished method with failure"""
        self.task.finished(False)

    def test_multiple_runs(self):
        """Testing multiple executions with the task"""
        devices1 = [Mock()]
        devices2 = [Mock(), Mock()]

        self.mock_s_eng.discover_devices.return_value = devices1, True
        result1 = self.task.run()
        self.assertTrue(result1)
        self.assertEqual(self.task.result, devices1)

        self.mock_s_eng.discover_devices.return_value = devices2, True
        result2 = self.task.run()
        self.assertTrue(result2)
        self.assertEqual(self.task.result, devices2)


if __name__ == '__main__':
    unittest.main()