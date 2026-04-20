
from abc import ABC, abstractmethod
from pathlib import Path

from ...localsync.channels.host_channel import HostChannel


class Transporter(ABC):

    @abstractmethod
    def push(self, file_list, source, destination):
        pass

    @abstractmethod
    def pull(self, file_list, source, destination):
        pass

    @abstractmethod
    def get_file_list(self, input_path, include_filters, exclude_filters) -> list:
        pass

    @abstractmethod
    def check_if_directory_exists(self, directory, pc_path, storages) -> list:
        pass

    @abstractmethod
    def cancel_file_load(self):
        pass

    def create_directory_in_host(self, folder: Path):
        HostChannel.create_directory_in_host(folder.as_posix())