import logging
import subprocess

from ...constants import QGIS_PLUGIN_NAME
from ..device.device_locator import DeviceLocator
from ..channels.mtp_channel import MtpChannel
from ..device.device_manager import DeviceManager
from ...i18n import tr
from ... import constants
from ...logger.qgis_logger_handler import QgisLoggerHandler


class MtpDeviceLocator(DeviceLocator):

    """
        Class that manages to locate the connected devices and to get the data related to them, using MTP connection type.
        :ivar logger: logger of the application.
        :vartype logger: QgisLoggerHandler
        :ivar _devices: list of string with the device_id of the connected devices.
        :vartype _devices: list[str]
        :ivar _devices_information: list of DeviceManager with information about the connected devices.
        :vartype _devices_information: list[DeviceManager]
        :ivar _devices_information_dict: temporal data that will be merged in _devices_information. Stored when consulting
        for the connected devices.
        :vartype _devices_information_dict: dict
    """


    def __init__(self):
        self._devices = []
        self._devices_information = {}
        self._devices_information_dict = {}
        self.logger = QgisLoggerHandler(
                    QGIS_PLUGIN_NAME,
                    level=logging.INFO
                ).get_logger()

    def get_connected_devices(self) -> list:
        """
            Returns list of connected devices.
            :return: list of connected devices.
        """
        return self._devices

    def search_for_connected_devices(self):
        """
            Search for connected devices and get some information about them.
        """
        self._devices = []
        dict_output = MtpChannel.get_devices()
        for device in dict_output:
            device = {k.lower(): v for k, v in device.items()}
            device_id = device[constants.ABOUT_DEVICE_VIRTUAL_PATH_KEY].split("#")
            if device_id and len(device_id) == 4:
                device_id = device_id[2]
            else:
                device_id = device[constants.ABOUT_DEVICE_NAME_KEY]

            self._devices.append(device_id)
            self._devices_information_dict[device_id.lower()] = {
                constants.ABOUT_DEVICE_NAME_KEY: device[constants.ABOUT_DEVICE_NAME_KEY],
                constants.ABOUT_DEVICE_VIRTUAL_PATH_KEY: device[constants.ABOUT_DEVICE_VIRTUAL_PATH_KEY],
                constants.ABOUT_DEVICE_TYPE_KEY: device[constants.ABOUT_DEVICE_TYPE_KEY]}



    def _get_devices_information(self):
        """
        Get extra information about connected devices and stores it in the current list of devices.
        """
        try:
            if not self._devices:
                self.search_for_connected_devices()
                if not self._devices:
                    self.logger.info("No devices found")
            for device_id in self._devices:
                device_id = device_id.lower()
                device_info = MtpChannel.get_information_about_device(device_id)
                if device_info:
                    device_info = {k.lower(): v for k, v in device_info.items()}
                    if device_id.lower() in self._devices_information_dict:
                        self._devices_information_dict[device_id].update(device_info)
                    else:
                        self._devices_information_dict[device_id] = device_info
                    new_device = DeviceManager(
                        device_id = device_id, name = self._devices_information_dict[device_id][
                            constants.ABOUT_DEVICE_NAME_KEY],
                        connection_type = constants.ABOUT_DEVICE_CONNECTION_TYPE_MTP,
                        virtual_path = self._devices_information_dict[device_id][
                            constants.ABOUT_DEVICE_VIRTUAL_PATH_KEY],
                        model = self._devices_information_dict[device_id][constants.ABOUT_DEVICE_DESCRIPTION_KEY],
                        brand = self._devices_information_dict[device_id][constants.ABOUT_DEVICE_MANUFACTURER_KEY],
                        manufacturer = self._devices_information_dict[device_id][
                            constants.ABOUT_DEVICE_MANUFACTURER_KEY],
                        device_type = self._devices_information_dict[device_id][constants.ABOUT_DEVICE_TYPE_KEY],
                        storages = MtpChannel.get_storages(self._devices_information_dict[device_id][
                                                               constants.ABOUT_DEVICE_VIRTUAL_PATH_KEY])
                    )
                    self._devices_information[device_id] = new_device
        except subprocess.CalledProcessError as e:
            raise subprocess.CalledProcessError(
                e.returncode,
                e.args,
                output="Error when getting information about phone:" + e.stdout,
                stderr="Error when getting information about phone: " + e.stderr
            )


    def about_device(self, device_id: str, force_search: bool=False) -> DeviceManager:
        '''
        Search for connected devices and get information about them.
        :param device_id: id of the connected device that will be searched for more information.
        :param force_search: if you want to force de search of devices again, use it as true.
        :return: information about the connected device.
        '''
        if not self._devices_information.get(device_id) or force_search:
            self._get_devices_information()
        return self._devices_information.get(device_id)