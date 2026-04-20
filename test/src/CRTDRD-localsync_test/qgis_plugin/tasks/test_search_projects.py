# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock

from qgis_plugin.tasks.search_projects import SearchProjects


class TestSearchProjects(unittest.TestCase):

    def setUp(self):
        """Initial configuration for every test"""
        self.mock_p_manager = Mock()
        self.mock_s_listener = Mock()
        self.device_id = "device_123"
        self.task = SearchProjects(
            self.mock_p_manager,
            self.device_id,
            self.mock_s_listener
        )

    def test_initialization(self):
        """Testing the correct initialisation of the task"""
        self.assertEqual(self.task.p_manager, self.mock_p_manager)
        self.assertEqual(self.task.device_id, self.device_id)
        self.assertTrue(self.task.canCancel())

    def test_run_success(self):
        """Testing the successful execution"""
        self.mock_p_manager.list_projects.return_value = None

        result = self.task.run()

        self.assertTrue(result)
        self.mock_p_manager.list_projects.assert_called_once_with(self.device_id)

    def test_run_calls_list_projects_with_correct_device(self):
        """Testing list_projects is called with the correct device_id"""
        different_device_id = "device_456"
        task = SearchProjects(self.mock_p_manager, different_device_id, self.mock_s_listener)

        task.run()

        self.mock_p_manager.list_projects.assert_called_once_with(different_device_id)

    def test_run_exception_handling(self):
        """Testing the handling of exceptions"""
        error_message = "Failed to list projects"
        self.mock_p_manager.list_projects.side_effect = Exception(error_message)

        result = self.task.run()

        self.assertFalse(result)

    def test_run_different_exception_types(self):
        """Testing different types of exceptions"""
        # Test con IOError
        self.mock_p_manager.list_projects.side_effect = IOError("IO error")
        result = self.task.run()
        self.assertFalse(result)

        # Reset para siguiente test
        self.task.error = None

        # Test con RuntimeError
        self.mock_p_manager.list_projects.side_effect = RuntimeError("Runtime error")
        result = self.task.run()
        self.assertFalse(result)

    def test_run_preserves_result_on_success(self):
        """Testing that result keeps None value if list_projects doesn't modify it"""
        self.mock_p_manager.list_projects.return_value = None

        result = self.task.run()

        self.assertTrue(result)

    def test_finished_success(self):
        """Testing that the finished method works"""
        self.task.finished(True)

    def test_finished_failure(self):
        """Testing finished method failure"""
        self.task.finished(False)

    def test_multiple_runs_with_different_devices(self):
        """Testing multiple executions with different devices"""
        # Primera ejecución
        result1 = self.task.run()
        self.assertTrue(result1)
        self.mock_p_manager.list_projects.assert_called_with(self.device_id)

        new_device_id = "device_789"
        task2 = SearchProjects(self.mock_p_manager, new_device_id, self.mock_s_listener)
        result2 = task2.run()
        self.assertTrue(result2)

        self.assertEqual(self.mock_p_manager.list_projects.call_count, 2)
        calls = self.mock_p_manager.list_projects.call_args_list
        self.assertEqual(calls[0][0][0], self.device_id)
        self.assertEqual(calls[1][0][0], new_device_id)


    '''
        def test_searching_projects_flag_initialization(self):
            """Testing that the searching_projects flag is initialised with False"""
            task = SearchProjects(self.mock_p_manager, "device_001", self.mock_s_listener)
            self.assertFalse(task.searching_projects)
    '''


if __name__ == '__main__':
    unittest.main()