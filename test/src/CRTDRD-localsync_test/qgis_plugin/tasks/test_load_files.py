# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, MagicMock, patch

from qgis.core import QgsTask

from qgis_plugin.tasks.load_files import LoadFiles


class TestLoadFiles(unittest.TestCase):

    def setUp(self):
        """Initial configuration for every test"""
        self.mock_s_eng = Mock()
        self.mock_device = Mock()
        self.mock_device.path_to_project = "/device/project"
        self.mock_s_listener = Mock()

        self.config = [
            {
                "source": "/local/source1",
                "destination": "/device/destination1",
                "includes": ["*.gpkg"],
                "excludes": ["*.bak"]
            },
            {
                "source": "/local/source2",
                "destination": "/device/destination2",
                "includes": ["*.shp"],
                "excludes": []
            }
        ]

        self.task = LoadFiles(
            self.mock_s_eng,
            self.config,
            self.mock_device,
            False,
            self.mock_s_listener
        )

    def test_initialization(self):
        """Verify that the initialisation was correct"""
        self.assertEqual(self.task.s_eng, self.mock_s_eng)
        self.assertEqual(self.task.config, self.config)
        self.assertEqual(self.task.device, self.mock_device)
        self.assertFalse(self.task.pull)

    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_success_push(self, mock_mapper_class, mock_host_class):
        """Test of successful execution in push mode"""
        mock_mapper = Mock()
        mock_mapper.source = "/local/source"
        mock_mapper.convert_mapper_reader_regex_list_to_regex_filter_list.return_value = []
        mock_mapper_class.return_value = mock_mapper

        mock_host = Mock()
        mock_host_class.return_value = mock_host

        result = self.task.run()

        self.assertTrue(result)

        # Verifica que se procesa cada configuración
        self.assertEqual(mock_mapper_class.call_count, 2)
        self.assertEqual(mock_host_class.call_count, 2)
        self.assertEqual(self.mock_s_eng.file_transport.call_count, 2)

    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_success_pull(self, mock_mapper_class, mock_host_class):
        """Test of successful execution in pull mode"""
        mock_mapper = Mock()
        mock_mapper.source = "/device/source"
        mock_mapper.convert_mapper_reader_regex_list_to_regex_filter_list.return_value = []
        mock_mapper_class.return_value = mock_mapper

        mock_host = Mock()
        mock_host_class.return_value = mock_host

        self.task.pull = True

        result = self.task.run()

        self.assertTrue(result)

        # Verifica que se llama a file_transport con pull=True
        for call_args in self.mock_s_eng.file_transport.call_args_list:
            self.assertTrue(call_args[0][3])  # pull=True

    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_creates_mapper_with_correct_params(self, mock_mapper_class, mock_host_class):
        """Test that the mapper is created with the correct parameters"""
        mock_mapper = Mock()
        mock_mapper.source = "/source"
        mock_mapper.convert_mapper_reader_regex_list_to_regex_filter_list.return_value = []
        mock_mapper_class.return_value = mock_mapper

        mock_host_class.return_value = Mock()

        self.task.run()

        # Verifica las llamadas al mapper para cada config
        calls = mock_mapper_class.call_args_list

        # Primera configuración
        self.assertEqual(calls[0][0][0], "/local/source1")
        self.assertEqual(calls[0][0][1], "/device/destination1")
        self.assertEqual(calls[0][0][2], ["*.gpkg"])
        self.assertEqual(calls[0][0][3], ["*.bak"])

        # Segunda configuración
        self.assertEqual(calls[1][0][0], "/local/source2")
        self.assertEqual(calls[1][0][1], "/device/destination2")
        self.assertEqual(calls[1][0][2], ["*.shp"])
        self.assertEqual(calls[1][0][3], [])

    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_creates_host_with_mapper_source(self, mock_mapper_class, mock_host_class):
        """Test that the host is created with the mapper source"""
        mock_mapper = Mock()
        mock_mapper.source = "/test/mapper/source"
        mock_mapper.convert_mapper_reader_regex_list_to_regex_filter_list.return_value = []
        mock_mapper_class.return_value = mock_mapper

        self.task.run()

        # Verifica que HostManager se crea con el source del mapper
        for call_args in mock_host_class.call_args_list:
            self.assertEqual(call_args[0][0], "")
            self.assertEqual(call_args[0][1], "/test/mapper/source")

    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_updates_device_path_for_each_config(self, mock_mapper_class, mock_host_class):
        """Test that the device path is updated for every configuration"""
        mock_mapper = Mock()
        mock_mapper.source = "/source"
        mock_mapper.convert_mapper_reader_regex_list_to_regex_filter_list.return_value = []
        mock_mapper_class.return_value = mock_mapper

        mock_host_class.return_value = Mock()

        self.task.run()

        # El path final debe ser el de la última configuración
        self.assertEqual(self.task.device.path_to_project, "/device/destination2")


    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_single_config(self, mock_mapper_class, mock_host_class):
        """Test with a single configuration"""
        mock_mapper = Mock()
        mock_mapper.source = "/source"
        mock_mapper.convert_mapper_reader_regex_list_to_regex_filter_list.return_value = []
        mock_mapper_class.return_value = mock_mapper

        mock_host_class.return_value = Mock()

        single_config = [{
            "source": "/single/source",
            "destination": "/single/dest",
            "includes": [],
            "excludes": []
        }]

        task = LoadFiles(self.mock_s_eng, single_config, self.mock_device, False, self.mock_s_listener)
        result = task.run()

        self.assertTrue(result)
        self.assertEqual(self.mock_s_eng.file_transport.call_count, 1)

    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_empty_config_list(self, mock_mapper_class, mock_host_class):
        """Test with an empty configuration list"""
        task = LoadFiles(self.mock_s_eng, [], self.mock_device, False, self.mock_s_listener)

        result = task.run()

        self.assertFalse(result)
        self.mock_s_eng.file_transport.assert_not_called()

    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_exception_handling(self, mock_mapper_class, mock_host_class):
        """Test of exception handling"""
        mock_mapper_class.side_effect = Exception("Test error")

        result = self.task.run()

        self.assertFalse(result)

    @patch('qgis_plugin.tasks.load_files.HostManager')
    @patch('qgis_plugin.tasks.load_files.SyncMapperData')
    def test_run_exception_in_second_config(self, mock_mapper_class, mock_host_class):
        """Test of exception in the second configuration"""
        mock_mapper = Mock()
        mock_mapper.source = "/source"
        mock_mapper.convert_mapper_reader_regex_list_to_regex_filter_list.return_value = []

        # Primera llamada exitosa, segunda lanza excepción
        mock_mapper_class.side_effect = [mock_mapper, Exception("Second config error")]
        mock_host_class.return_value = Mock()

        result = self.task.run()

        self.assertFalse(result)
        # Solo se debe haber procesado la primera configuración
        self.assertEqual(self.mock_s_eng.file_transport.call_count, 1)


    @patch('qgis_plugin.tasks.load_files.HostManager')
    def test_run_file_transport_called_with_correct_args(self, mock_host_class):
        """Test file_transport called with correct args"""


        mock_host = Mock()
        mock_host_class.return_value = mock_host

        self.task.run()

        i = 0
        # Verifica los argumentos de cada llamada
        for call_args in self.mock_s_eng.file_transport.call_args_list:
            if i == 0:
                self.assertEqual(call_args[0][0], self.mock_device)
                self.assertEqual(call_args[0][1], mock_host)
                self.assertEqual(call_args[0][2], ["*.gpkg"])
                self.assertEqual(call_args[0][3], ["*.bak"])
                self.assertFalse(call_args[0][4])  # pull=False
            else:
                self.assertEqual(call_args[0][0], self.mock_device)
                self.assertEqual(call_args[0][1], mock_host)
                self.assertEqual(call_args[0][2], ["*.shp"])
                self.assertEqual(call_args[0][3], [])
                self.assertFalse(call_args[0][4])  # pull=False
            i += 1


if __name__ == '__main__':
    unittest.main()