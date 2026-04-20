# -*- coding: utf-8 -*-
import unittest
from unittest.mock import Mock, MagicMock, patch, call

import qgis_plugin.ui_controllers.devices_combo
from PyQt5.QtWidgets import QComboBox, QMessageBox

from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsApplication
from qgis_plugin.localsync.channels.adb_channel import AdbStatus
from qgis_plugin.localsync.channels.mtp_channel import MtpStatus

from qgis_plugin.ui_controllers.devices_combo import DevicesCombo


class TestDevicesCombo(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """QAplication configuration needed for Qt widgets"""
        if not QApplication.instance():
            cls.app = QApplication([])

    def setUp(self):
        """Initial configuration for every test"""
        self.mock_s_eng = Mock()
        self.mock_s_listener = Mock()
        self.combo = DevicesCombo(self.mock_s_eng, self.mock_s_listener)

    def test_initialization(self):
        """Verify the correct initialisation of the combo box"""
        self.assertIsNone(self.combo.task)
        self.assertEqual(self.combo.s_eng, self.mock_s_eng)

    @patch('qgis_plugin.ui_controllers.devices_combo.ReadDevices')
    @patch('qgis_plugin.ui_controllers.devices_combo.QgsApplication')
    def test_show_popup_creates_task(self, mock_qgs_app, mock_read_devices):
        """Test that showPopup create the task correctly"""
        mock_task_manager = Mock()
        mock_qgs_app.taskManager.return_value = mock_task_manager
        mock_task = Mock()
        mock_read_devices.return_value = mock_task

        self.mock_s_eng.supports.return_value = {
            "adb": AdbStatus(
                available=True,
                error_type=None,
                error_message="",
                details={
                    "adb_path": "/path",
                    "version": "1.0",
                }
            ),
            "mtp": MtpStatus(
                available=True,
                error_type=None,
                error_message="MTP available",
                details={}
            )
        }

        self.combo.showPopup()

        # Verify that the combo is cleaned
        self.assertEqual(self.combo.count(), 0)

        # Verify that the task is created
        mock_read_devices.assert_called_once_with(self.mock_s_eng)

        # Verify that the signal is connected
        mock_task.taskCompleted.connect.assert_called_once_with(self.combo.get_devices_response)

        # Verify that the task is added to the task manager
        mock_task_manager.addTask.assert_called_once_with(mock_task)

        # Verify that the task is assigned
        self.assertEqual(self.combo.task, mock_task)

    @patch('qgis_plugin.ui_controllers.devices_combo.QgsApplication')
    def test_show_popup_no_task_when_already_exists(self, mock_qgs_app):
        """Test that a task is not created if already exists one"""
        self.combo.task = Mock()
        initial_task = self.combo.task

        self.combo.showPopup()

        # La tarea no debe cambiar
        self.assertEqual(self.combo.task, initial_task)

    @patch.object(QComboBox, 'showPopup')
    @patch('PyQt5.QtWidgets.QMessageBox.warning', return_value=QMessageBox.Ok)
    def test_get_devices_response_empty_list(self, mock_qmessage, mock_super_show_popup):
        """Test get_devices_response with an empty list"""
        mock_task = Mock()
        mock_task.result = []
        self.combo.task = mock_task

        self.combo.get_devices_response()

        self.assertIsNone(self.combo.task)

        self.assertEqual(self.combo.count(), 1)
        self.assertEqual(self.combo.itemText(0), "No devices found!")
        self.assertIsNone(self.combo.itemData(0))

    @patch.object(QComboBox, 'showPopup')
    def test_get_devices_response_with_devices(self, mock_super_show_popup):
        """Test gt_devices_response with devices"""
        # Crear dispositivos mock
        device1 = Mock()
        device1.name = "Phone1"
        device1.brand = "Samsung"
        device1.model = "Galaxy S21"
        device1.no_data = False

        device2 = Mock()
        device2.name = "Phone2"
        device2.brand = "Xiaomi"
        device2.model = "Mi 11"
        device2.no_data = False

        mock_task = Mock()
        mock_task.result = [device1, device2]
        self.combo.task = mock_task

        self.combo.get_devices_response()

        # Verifica que la tarea se resetea
        self.assertIsNone(self.combo.task)

        # Verifica que se añaden los items correctamente (1 vacío + 2 dispositivos)
        self.assertEqual(self.combo.count(), 3)

        # Verifica el item vacío
        self.assertEqual(self.combo.itemText(0), "")
        self.assertIsNone(self.combo.itemData(0))

        # Verifica el primer dispositivo
        self.assertEqual(self.combo.itemText(1), "Phone1 - Samsung - Galaxy S21")
        self.assertEqual(self.combo.itemData(1), device1)

        # Verifica el segundo dispositivo
        self.assertEqual(self.combo.itemText(2), "Phone2 - Xiaomi - Mi 11")
        self.assertEqual(self.combo.itemData(2), device2)

        # Verifica que se llama al showPopup del padre
        mock_super_show_popup.assert_called_once()

    @patch.object(QComboBox, 'showPopup')
    def test_get_devices_response_with_none_devices(self, mock_super_show_popup):
        """Test get_devices_respose with None values in the list"""
        device1 = Mock()
        device1.name = "Phone1"
        device1.brand = "Samsung"
        device1.model = "Galaxy"
        device1.no_data = False

        mock_task = Mock()
        mock_task.result = [device1, None, None]
        self.combo.task = mock_task

        self.combo.get_devices_response()

        # Solo debe añadir el item vacío y el dispositivo válido (ignora None)
        self.assertEqual(self.combo.count(), 2)
        self.assertEqual(self.combo.itemText(1), "Phone1 - Samsung - Galaxy")

    @patch.object(QComboBox, 'showPopup')
    @patch('PyQt5.QtWidgets.QMessageBox.warning', return_value=QMessageBox.Ok)
    def test_get_devices_response_blocks_signals(self , mock_message_box, mock_super_show_popup):
        """Test that signals are blocked when updating"""
        mock_task = Mock()
        mock_task.result = []
        self.combo.task = mock_task

        # Spy en blockSignals
        with patch.object(self.combo, 'blockSignals', wraps=self.combo.blockSignals) as mock_block:
            self.combo.get_devices_response()

            # Verifica que se llamó blockSignals dos veces (True y False)
            self.assertEqual(mock_block.call_count, 2)
            mock_block.assert_any_call(True)
            mock_block.assert_any_call(False)


if __name__ == '__main__':
    unittest.main()