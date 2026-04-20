import logging
import traceback
from pathlib import Path
from ...i18n import tr

from ..core.sync_engine import SyncEngine
from ...constants import QGIS_PLUGIN_NAME, CARTODRUID_PROJECT_SPLITTERS, PROJECT_DATA_DEVICE_ID_KEY, \
    PROJECT_DATA_PROJECT_NAME_KEY, PROJECT_DATA_PATH_KEY, PROJECT_DATA_STORAGE_ID_KEY
from ...logger.qgis_logger_handler import QgisLoggerHandler


#------------------------------------------------------------------------
# Revisar bien este fichero cuando se vuelva a incluir en el proyecto.
#------------------------------------------------------------------------

class ProjectData:

    """
        Keep the information about a project.
    """

    def __init__(self, device_id: str="", project_name: str="", path: Path="", storage_id:str = ""):
        self.device_id = device_id
        self.project_name = project_name
        self.path = path
        self.storage_id = storage_id

    def __eq__(self, other):
        if not isinstance(other, ProjectData):
            return False
        return (self.device_id == other.device_id and self.project_name == other.project_name and self.path.as_posix() ==
                other.path.as_posix() and self.storage_id == other.storage_id)


    def to_dict(self):
        return {
            PROJECT_DATA_DEVICE_ID_KEY: self.device_id,
            PROJECT_DATA_PROJECT_NAME_KEY: self.project_name,
            PROJECT_DATA_PATH_KEY: self.path.as_posix() if self.path else "",
            PROJECT_DATA_STORAGE_ID_KEY: self.storage_id,
        }

    @classmethod
    def from_dict(cls, data_dict):
        if (PROJECT_DATA_DEVICE_ID_KEY in data_dict and PROJECT_DATA_PROJECT_NAME_KEY in data_dict and
            PROJECT_DATA_PATH_KEY in data_dict and PROJECT_DATA_STORAGE_ID_KEY in data_dict):
            return cls(data_dict[PROJECT_DATA_DEVICE_ID_KEY], data_dict[PROJECT_DATA_PROJECT_NAME_KEY],
                       Path(data_dict[PROJECT_DATA_PATH_KEY]),data_dict[PROJECT_DATA_STORAGE_ID_KEY])
        return None




class ProjectManager:

    """
        Manages projects inside the device and search for them.

        :ivar list_project_names: list with the names of the projects found.
        :vartype list_project_names: list[str]
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: logging.Logger
    """

    def __init__(self, sync_engine: SyncEngine):
        """
            Constructor.
            :param sync_engine: Used to get information about the projects in the devices.
        """
        self.sync_engine = sync_engine
        self.list_project_names = []
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

    @staticmethod
    def get_project_name_from_path(path: Path, cartodroid_folder: str):
        """
            Get the project name from the path if there is one.
            :param path: path of the project.
            :param cartodroid_folder: string folder pattern that will be searched in the path to determinate the project name.
            :return: project name.
        """
        split = path.as_posix().split(cartodroid_folder)
        if len(split) == 2:
            if split[1].startswith("/"):
                project_name_path = split[1][1:]
            else:
                project_name_path = split[1]
            project_name_and_rest = project_name_path.split("/") if project_name_path else []
            if project_name_and_rest:
                return project_name_and_rest[0]
            else:
                return None
        return None


    def list_projects(self, device_id = None):
        """
        List all the projects found on the connected devices to the pc.
        The list of found projects will be saved on self.list_project_names
        :param device_id: id of the device where the search of projects will be performed. If None it will be performed
        on all connected devices.
        """
        self.list_project_names = []
        devices, successful  = self.sync_engine.discover_devices()
        if successful:
            self.logger.info("Looking for projects...")
            try:
                for found_device in devices:
                    if device_id and device_id != found_device.device_id:
                        continue
                    for storage in found_device.storages:
                        for cartodroid_folder in CARTODRUID_PROJECT_SPLITTERS:
                            path = Path(storage)
                            path = path / cartodroid_folder
                            files = self.sync_engine.list_files(True, str(path.as_posix()), [],[],
                                                                found_device, True)
                            self._search_projects_names_and_save(files,found_device,cartodroid_folder)
            except Exception:
                self.logger.error(traceback.format_exc())
        return self.list_project_names



    def _search_projects_names_and_save(self, files, found_device, cartodroid_folder):
        """
        Search projects names in the given device and prints them in the logger and storages them internally.
        :param files: list of directories found on ../cartodroid/projects/
        :param found_device: device where the search of projects will be performed.
        :param cartodroid_folder: folder pattern that will be searched in the path to determinate the project name.
        """
        for path in files:
            project_name = ProjectManager.get_project_name_from_path(path, cartodroid_folder)
            if project_name:
                if not any(project.project_name == project_name and
                           project.device_id == found_device.device_id for project in self.list_project_names):
                    self.logger.info("Found project in folder {path}, with name {project_name}, in the device with"
                                     " ID {found_device}.".format(path=path, project_name=project_name, found_device=found_device.device_id))
                    self.list_project_names.append(ProjectData(found_device.device_id, project_name, path))