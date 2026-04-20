from dataclasses import field, dataclass
from typing import List
from ...i18n import tr

@dataclass
class DeviceManager:

    """
        Class to storage all the information about a connected device. Not all the fields will be filled, since the information
        gathered via ADB or MTP is different.
        :ivar device_id: identifier of the device.
        :ivar no_data: indicates if there is no more data than the device_id for this device.
        :ivar virtual_path: used for MTP to storage the name of the virtual folder of the connected device. Needed to use MTP.
        :ivar connection_type: Type of the connection used to gather the information.
        :ivar storages: list of found storages in the device.
        :ivar model: string model of the device.
        :ivar brand: string brand of the device.
        :ivar name: string name of the device.
        :ivar manufacturer: string manufacturer of the device.
        :ivar cpu: string cpu of the device.
        :ivar supported_archs: string supported architectures of the device.
        :ivar native_abi: string native architecture of the device.
        :ivar path_to_project: string path of the project location.
        :ivar device_type: string type of the device.
    """

    device_id: str = ""
    model: str = ""
    brand: str = ""
    name: str = ""
    manufacturer: str = ""
    cpu: str = ""
    supported_archs: str = ""
    native_abi: str = ""
    storages: List[str] = field(default_factory=list)
    path_to_project: str = ""
    device_type: str = ""
    virtual_path: str = ""
    connection_type: str = ""
    no_data: bool = False


    def __str__(self) -> str:
        content_string = ""
        storages_string = ""

        if len(self.storages) == 1:
            storages_string += "Internal memory: {storage}".format(storage=self.storages[0])
        else:
            for idx, storage in enumerate(self.storages):
                if ("emulated" in storage or "sdcard" in storage or
                        "self" in storage or "Tablet" in storage or "Phone" in storage):
                    storages_string += "Internal memory: {storage}".format(storage=storage)
                else:
                    storages_string += "SdCard: {storage}".format(storage=storage)
                if idx != len(self.storages) - 1:
                    storages_string += ", "
        storages_string += "\n"

        content_string = ("Connection Type: {con_type}\nDevice ID: {id}\nModel: {model}\n"
                "Brand: {brand}\nName: {name}\nManufacturer: {manufacturer}\nCPU: {cpu}\n"
                "Supported Archs: {supported_archs}\nNative ABI: {native_abi}\nType: {device_type}\n"
                "Virtual Path: {virtual_path}\nStorages: {storages}").format(con_type=self.connection_type,id=self.device_id,
                                                                        model=self.model,brand=self.brand,name=self.name,
                                                                        manufacturer=self.manufacturer,cpu=self.cpu,
                                                                        supported_archs=self.supported_archs,native_abi=self.native_abi,
                                                                        device_type=self.device_type,virtual_path=self.virtual_path,
                                                                        storages=storages_string)


        return content_string

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other) -> bool:
        if not isinstance(other, DeviceManager):
            return False
        return self.device_id == other.device_id

    def set_project_path(self, full_path: str):
        """
            Assign the path_to_project string path.
            :param full_path: full path of the folder projects.
        """
        self.path_to_project = full_path

    def get_project_path(self) -> str:
        """
        Return the path_to_project string path.
        :return: full path of the folder projects.
        """
        return self.path_to_project

    def get_device_id(self) -> str:
        """
        Return the device identifier.
        :return: device identifier.
        """
        return self.device_id

