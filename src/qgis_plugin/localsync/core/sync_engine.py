import logging
import traceback

from ..channels.host_channel import HostChannel
from ..channels.mtp_channel import MtpChannel
from ..device.device_manager import DeviceManager
from ..host import host_manager
from ..host.host_manager import HostManager
from ...constants import QGIS_PLUGIN_NAME
from ..device.adb_device_locator import AdbDeviceLocator

from ..channels.adb_channel import AdbChannel
from ..device.mtp_device_locator import MtpDeviceLocator
from ..transporter.adb_transporter import AdbTransporter
from pathlib import Path
from ...i18n import tr

from ..transporter.mtp_transporter import MtpTransporter
from ...logger.qgis_logger_handler import QgisLoggerHandler


class SyncEngine:


    """
        This class manages the interaction between devices and pc.
        :ivar adb_available: True if we are using adb.
        :vartype adb_available: bool
        :ivar mtp_available: True if we are using mtp.
        :vartype mtp_available: bool
        :ivar locator: reference to the current DeviceLocator that is going to be used.
        :vartype locator: DeviceLocator
        :ivar transport: reference to the current Transport class that is going to be used.
        :vartype transport: Transport
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
    """

    adb_active = True
    mtp_active = False


    def activate_mtp_or_adb(self,adb_activate: bool):
        """
            Select between MTP or ADB mode.
            :param adb_activate: bool True when you want to activate ADB mode, False to activate MTP mode.
        """

        if adb_activate:
            SyncEngine.adb_active = True
            SyncEngine.mtp_active = False
            self.locator = AdbDeviceLocator()
            self.transport = AdbTransporter()
        else:
            SyncEngine.adb_active = False
            SyncEngine.mtp_active = True
            self.locator = MtpDeviceLocator()
            self.transport = MtpTransporter()

    def __init__(self):
        #self.activate_mtp_or_adb(True)

        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()


    def check_if_directory_exists(self, directory: str, device: DeviceManager = None, pc_path: bool = True) -> bool:
        """
            Check if a directory exists on the given path
            :param directory: string directory path that will be checked.
            :param device: DeviceManager object where the directory is located, in case that it is in the device.
            :param pc_path: bool True if the directory is located in the pc, False in case that it is in the device.
            :return: bool True if directory exists, False if it does not exist.
        """

        try:
            if SyncEngine.mtp_active:
                MtpChannel.set_selected_device_id_path(device.virtual_path)
            if SyncEngine.adb_active:
                AdbChannel.set_default_device_id(device.device_id)
            return self.transport.check_if_directory_exists(directory, pc_path, device.storages)

        except Exception:
            self.logger.error(traceback.format_exc())
            return False

    def discover_devices(self):
        """
        Get the list of phone devices connected to the pc.
        :return: list of phone devices connected to the pc.
        """
        try:
            connected_devices = []
            self.locator.search_for_connected_devices()
            devices = self.locator.get_connected_devices()
            for device_id in devices:
                new_device = self.locator.about_device(device_id)
                connected_devices.append(new_device)
            return connected_devices, True
        except Exception:
            self.logger.error(traceback.format_exc())
            return [], False


    def cancel_load_process(self):
        """
            Cancel load process on transport.
        """
        self.transport.cancel_file_load()


    def file_transport(self, device: DeviceManager, host: HostManager, includes_filters: list[str],
                       excludes_filters: list[str], pull: bool) -> bool:
        """
        Copy files from the PC to a Device or from the Device to the PC, filtering the content with file_filters
        :param device: the device where the files will be read/copied.
        :param host: the host with the path where the files will be read/copied.
        :param includes_filters: list of string filters glob style. Those paths that fulfill one of the patterns will be transported
        :param excludes_filters: list of string filters glob style. Those paths that fulfill one of the patterns will not be transported.
        :param pull: bool True to download files from the device to the pc, False to upload from the pc to the device.
        """

        if host.path and device.path_to_project:
            try:
                if SyncEngine.mtp_active:
                    MtpChannel.set_selected_device_id_path(device.virtual_path)
                if SyncEngine.adb_active:
                    AdbChannel.set_default_device_id(device.device_id)
                device.path_to_project = Path(device.path_to_project).as_posix()
                host.path = Path(host.path).as_posix()
                if pull:
                    file_list = self.transport.get_file_list(device.path_to_project, includes_filters, excludes_filters)
                    self.transport.pull(file_list, device.path_to_project, host.path)
                else:
                    file_list = HostChannel.get_file_list(host.path, includes_filters, excludes_filters)
                    self.transport.push(file_list, host.path, device.path_to_project)
                return True

            except Exception:
                self.logger.error(traceback.format_exc())
                return False
        else:
            if not host.path:
                self.logger.error("No source path provided.")
            else:
                self.logger.error("No destination path provided.")
            return False


    def recreate_device_structure(self, device: DeviceManager, host: HostManager) -> bool:
        """
            Tries to recreate the folder structure on the given device and path_to_project in the host.
            :param device: connected device where the folder structure will be consulted.
            :param host: host folder where the folder structure will be recreated.
        """
        try:
            if SyncEngine.mtp_active:
                MtpChannel.set_selected_device_id_path(device.virtual_path)
            if SyncEngine.adb_active:
                AdbChannel.set_default_device_id(device.device_id)
            device_path = Path(device.path_to_project)
            device.path_to_project = device_path.as_posix()
            host_path = Path(host.path)
            host.path = host_path.as_posix()
            folders_list = self.list_files(True,device.path_to_project,[],[],device,
                                           True)
            for folder in folders_list:
                new_path = host_path / folder.relative_to(device_path)
                self.transport.create_directory_in_host(new_path)
            return True
        except Exception as e:
            self.logger.error("Error while recreating the folder structure: " + str(e))
            self.logger.error(traceback.format_exc())
            return False


    def list_files(self, search_in_device: bool, path: str, includes_filter: list[str], excludes_filter: list[str],
                   device: DeviceManager = None, only_directories: bool = False) -> list:
        """
        List all the files found on the path on the provided device, filtering the results by file_filer.
        :param search_in_device: To decide if the search will be performed on the device or in the host.
        :param path: path with base folder where the search will be performed.
        :param includes_filter: list of string filters glob style. Those paths that fulfill one of the patterns will be included in the final list, rest will be excluded.
        :param excludes_filter: list of string filters glob style. Those paths that fulfill one of the patterns will be excluded in the final list, rest will be included.
        :param device: the device where the files will be read.
        :param only_directories: If True only directories will be returned.
        :return: list of Path with the files/directories found on the given path and filtered.
        """
        try:
            if search_in_device and device:
                if SyncEngine.mtp_active:
                    MtpChannel.set_selected_device_id_path(device.virtual_path)
                if SyncEngine.adb_active:
                    AdbChannel.set_default_device_id(device.device_id)
                file_list = self.transport.get_file_list(path, includes_filter, excludes_filter, only_directories)
            else:
                file_list = HostChannel.get_file_list(path, includes_filter, excludes_filter, only_directories)
            return file_list
        except Exception:
            self.logger.error(traceback.format_exc())
            return []


    def supports(self, check_adb = True, check_mtp = True) -> dict:
        """
            Check if the system supports MTP or ADB.
            :param check_adb: If True will check if the systems supports ADB.
            :param check_mtp: If True will check if the systems supports MTP.
            :return: dictionary with keys adb and mtp and values true or false depending on if the system supports ADB or MTP.
        """
        supported = {}
        if check_mtp:
            try:
                mtp_availability = MtpChannel.is_available()
                self.logger.info(f"MTP available: {mtp_availability.available}")
                if not mtp_availability.available:
                    self.logger.info(f"Error type: {mtp_availability.error_type.value}")
                    self.logger.info(f"Message: {mtp_availability.error_message}")
                    self.logger.info(f"Details: {mtp_availability.details}")
                supported["mtp"] = mtp_availability
            except Exception as e:
                self.logger.error("Error while checking MTP availability: " + str(e))
        if check_adb:
            try:
                adb_availability = AdbChannel.is_available()
                self.logger.info(f"ADB available: {adb_availability.available}")
                if not adb_availability.available:
                    self.logger.info(f"Error type: {adb_availability.error_type.value}")
                    self.logger.info(f"Message: {adb_availability.error_message}")
                    self.logger.info(f"Details: {adb_availability.details}")
                else:
                    self.logger.info(f"ADB path: {adb_availability.details.get('adb_path')}")
                    self.logger.info(f"Version: {adb_availability.details.get('version')}")
                supported["adb"] = adb_availability
            except Exception as e:
                self.logger.error("Error while checking ADB availability: " + str(e))
        return supported