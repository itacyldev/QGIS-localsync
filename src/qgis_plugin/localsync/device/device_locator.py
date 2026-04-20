from abc import ABC, abstractmethod

from ..device.device_manager import DeviceManager


class DeviceLocator(ABC):


    @abstractmethod
    def get_connected_devices(self) -> list:
        pass

    @abstractmethod
    def search_for_connected_devices(self):
        pass

    @abstractmethod
    def about_device(self, device_id, force_search) -> DeviceManager:
        pass

    @abstractmethod
    def _get_devices_information(self):
        pass