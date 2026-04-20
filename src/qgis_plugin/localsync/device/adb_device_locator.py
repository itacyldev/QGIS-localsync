import logging
import subprocess

from .device_locator import DeviceLocator
from ..channels.adb_channel import AdbChannel
from ... import constants, logger
import re
from ...i18n import tr

from .device_manager import DeviceManager
from ...constants import QGIS_PLUGIN_NAME
from ...logger.qgis_logger_handler import QgisLoggerHandler


class AdbDeviceLocator(DeviceLocator):


    """
        Class that manages to locate the connected devices and to get the data related to them, using ADB connection type.
        :ivar logger: logger of the application.
        :vartype logger: logging.Logger
        :ivar _devices: list of string with the device_id of the connected devices.
        :vartype _devices: list[str]
        :ivar _about_devices: list of DeviceManager with information about the connected devices.
        :vartype _about_devices: list[DeviceManager]
        :ivar _sdcard_pattern: string pattern usted to search for sdcard in the storage of the devices.
        :vartype _sdcard_pattern: str
    """

    def __init__(self):
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self._devices = []
        self._about_devices = {}
        self._sdcard_pattern = r'^[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}$'

    def search_for_connected_devices(self):
        """
            Filter the output of adb devices to save the ids of the connected devices.
        """
        self._devices = []
        output = AdbChannel.get_devices()

        output_strip = output.strip()
        # First line is a head, we ignore it
        for line in output_strip.splitlines()[1:]:
            if line.strip():  # Ignore empty line
                device_id, status = line.split('\t')
                if status == "device":
                    self._devices.append(device_id.strip())
                    if device_id.strip() in self._about_devices:
                        self._about_devices.pop(device_id.strip())
                else:
                    device_id = device_id.strip()
                    self._devices.append(device_id)
                    self._about_devices[device_id] = DeviceManager(device_id = device_id, no_data=True)


    def get_connected_devices(self) -> list:
        """
            Returns the list of connected devices found.
            :return: list of connected devices.
        """
        return self._devices


    def _get_devices_information(self):
        """
            Get extra information of all connected devices and stores it internally in the class.
        """
        if not self._devices:
            self.search_for_connected_devices()
            if not self._devices:
                self.logger.info("No devices found")

        try:
            for d_id in self._devices:
                if d_id not in self._about_devices or not self._about_devices[d_id].no_data:

                    AdbChannel.set_default_device_id(d_id)
                    new_device = DeviceManager(
                        device_id=d_id,
                        model=AdbChannel.get_information_about_device(constants.GETPROP_MODEL),
                        brand=AdbChannel.get_information_about_device(constants.GETPROP_BRAND),
                        name=AdbChannel.get_information_about_device(constants.GETPROP_NAME),
                        manufacturer=AdbChannel.get_information_about_device(constants.GETPROP_MANUFACTURER),
                        cpu=AdbChannel.get_information_about_device(constants.GETPROP_CPU),
                        supported_archs=AdbChannel.get_information_about_device(constants.GETPROP_SUPPORTED_ARCHS),
                        native_abi=AdbChannel.get_information_about_device(constants.GETPROP_NATIVE_ABI),
                        storages=self._filter_storages_to_locate_cards(AdbChannel.no_recursive_ls("/storage")),
                        connection_type = constants.ABOUT_DEVICE_CONNECTION_TYPE_ADB
                    )
                    self._about_devices[d_id] = new_device
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode,
                e.args,
                output="Error when getting information about phone: {error}".format(error = e.stdout),
                stderr="Error when getting information about phone: {error}".format(error = e.stderr)
            )

    def _filter_storages_to_locate_cards(self, output: str) -> list:
        """
            Filters the output of the folder /storage/ on the device to look for the different
            storages available.
            :param output: output of ls /storage/ on the device.
            :return: list of storages found on the device
        """

        storages_found = []
        storage_lines = output.splitlines()
        primary_found = False
        emulated_found = False
        for storage in storage_lines:
            storage_checking = storage.strip()
            if storage_checking != "":
                if re.match(self._sdcard_pattern, storage_checking):
                    storages_found.append("/storage/" + storage_checking + "/")
                elif storage_checking == "self":
                    file_list = self._try_get_self_storage_from_device(storage_checking)
                    if "primary" in file_list:
                        primary_found = True
                elif storage_checking == "emulated":
                    emulated_found = True


        return self._get_main_storage_path(primary_found, storages_found, emulated_found)


    def _try_get_self_storage_from_device(self, storage_checking: str) -> list:
        """
            Try to search inside the folder /storage/$storage_checking on the current selected device and returns
            what it finds.
            :param storage_checking: string containing the path folder inside storage in which we will perform the search.
            :return: list of folders found on the given path.
        """
        try:
            file_list = AdbChannel.no_recursive_ls("/storage/" + storage_checking)
        except Exception as e:
            self.logger.error("Error trying to retrieve storage list: {error}".format(error = str(e)))
            file_list = []
        return file_list


    def _get_main_storage_path(self, primary_found: bool, storages_found: list, emulated_found: bool) -> list:
        """
        Get the paths to the main storages possibles on the device.
        :param primary_found: True if primary was found, false otherwise.
        :param storages_found: list of other storages found in the device (mainly sd cards)
        :param emulated_found: True if emulated was found, false otherwise.
        :return: the list of storages found on the device with the new main storage in it.
        """
        if primary_found:
            storages_found.insert(0,"/storage/self/primary/")
        else:
            if emulated_found:
                try:
                    storages_found.insert(0,"/storage/emulated/"+AdbChannel.get_current_used_id().replace("\n","")+"/")
                except Exception as e:
                    self.logger.error("Error trying to retrieve current user on device: {error}".format(error = str(e)))
            else:
                storages_found.insert(0,"/sdcard/")
        return storages_found


    def about_device(self, device_id: str, force_search: bool = False) -> DeviceManager:
        """
            Get the list of connected devices.
            :return: the information about the device with id $device_id.
        """
        if not self._about_devices.get(device_id) or force_search:
            self._get_devices_information()
        return self._about_devices.get(device_id)