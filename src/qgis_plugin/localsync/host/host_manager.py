import os


class HostManager:

    """
        Keep information about the host.
    """


    def __init__(self, base_folder: str, path: str):
        """
            Constructor.
            :param base_folder: string with the path to the base_folder in the host.
            :param path: string with a subpath from base_folder
        """
        self.base_folder = base_folder
        self.path = path


    def get_full_path(self) -> str:
        """
            Get the full path of the host.
        """
        return self.path

    def set_full_path(self, full_path: str):
        """
            Set the full path of the host.
        """
        self.path = full_path