from ...localsync.project.project_manager import ProjectData
from ...constants import CARTODRUID_CONNECT_CONFIG_BOX, CARTODRUID_CONNECT_IMAGE_BOX, \
    CARTODRUID_CONNECT_DATA_BOX, CARTODRUID_CONNECT_DATA_LIST, CARTODRUID_CONNECT_PROJECT, \
    CARTODRUID_CONNECT_DATA_LIST_FULL, CARTODRUID_CONNECT_DATA_SELECTED_LAYERS, \
    CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS


class ProjectWizardData:

    """
    Stores the data necessary for the ProjectWizard.
    :ivar _project_selected: Current project that has been selected in the wizard.
    :vartype _project_selected: ProjectData
    :ivar config_box_selected: Saves whether the config combobox was checked or not.
    :vartype config_box_selected: bool
    :ivar image_box_selected: Saves whether the image combobox was checked or not.
    :vartype image_box_selected: bool
    :ivar data_box_selected: Saves whether the data combobox was checked or not.
    :vartype data_box_selected: bool
    :ivar data_list_selected_files: list of files on the list view of the second page that were selected, with the .sqlite found on th data folder of the Cartodruid project.
    :vartype data_list_selected_files: list
    :ivar data_list_full: full list of files on the list view of the second page, with the .sqlite found on th data folder of the Cartodruid project.
    :vartype data_list_full: list
    :ivar data_selected_layers: dict of layers selected on the third page of the wizard. Key: File name, Value: List of layers selected on that file.
    :vartype data_selected_layers: dict
    """

    _project_selected = None
    config_box_selected = False
    image_box_selected = False
    data_box_selected = False
    data_list_selected_files = []
    data_list_full = []
    data_selected_layers = {}
    save_photo_layers = False

    def __init__(self, _project_selected: ProjectData=None, config_box_selected:bool=False, image_box_selected:bool=False,
                 data_box_selected:bool=False, data_list_selected_files:list=None, data_list_full:list=None, data_selected_layers:dict=None,
                 photo_selected_folders:list=None):
        self._project_selected = _project_selected
        self.config_box_selected = config_box_selected
        self.image_box_selected = image_box_selected
        self.data_box_selected = data_box_selected
        self.data_list_selected_files = data_list_selected_files if data_list_selected_files else []
        self.data_list_full = data_list_full if data_list_full else []
        self.data_selected_layers = data_selected_layers if data_selected_layers else {}
        self.photo_selected_folders = photo_selected_folders if photo_selected_folders else []



    def change_project(self, new_project: ProjectData) -> bool:
        """
            Changes the current project and restart the state of the instance if the project name is different between the new and the old.
            :param new_project: new project to change to.
        """
        is_new_project = False
        if self._project_selected:
            if self._project_selected.project_name != new_project.project_name:
                self.config_box_selected = False
                self.image_box_selected = False
                self.data_box_selected = False
                self.data_list_selected_files = []
                self.data_list_full = []
                self.data_selected_layers = {}
                self.photo_selected_folders = []
                is_new_project = True
        else:
            is_new_project = True
        self._project_selected = new_project
        return is_new_project



    def get_project_selected(self) -> ProjectData:
        """
        Returns the current project.
        :return: the current project.
        """
        return self._project_selected

    def to_dict(self) -> dict:
        """
            Converts the data stored by the instance to a dictionary.
            :return: dictionary with the data of the instance.
        """
        return {
            CARTODRUID_CONNECT_PROJECT: self._project_selected.to_dict(),
            CARTODRUID_CONNECT_CONFIG_BOX: self.config_box_selected,
            CARTODRUID_CONNECT_IMAGE_BOX: self.image_box_selected,
            CARTODRUID_CONNECT_DATA_BOX: self.data_box_selected,
            CARTODRUID_CONNECT_DATA_LIST: self.data_list_selected_files,
            CARTODRUID_CONNECT_DATA_LIST_FULL: self.data_list_full,
            CARTODRUID_CONNECT_DATA_SELECTED_LAYERS: self.data_selected_layers,
            CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS: self.photo_selected_folders
        }

    def can_convert_to_dict(self) -> bool:
        """
            Check whether the instance can be converted to a dictionary or not.
            :return: True if the instance can be converted to a dictionary, False otherwise.
        """
        return self._project_selected is not None

    @classmethod
    def from_dict(cls, data_dict: dict) -> "ProjectWizardData":
        """
        Creates an instance of the class from the data of a dictionary. If the data is incomplete, then it returns a new instance.
        :param data_dict: dictionary with the data of the instance.
        """
        contains_keys = (CARTODRUID_CONNECT_PROJECT in data_dict and CARTODRUID_CONNECT_CONFIG_BOX in data_dict and
            CARTODRUID_CONNECT_IMAGE_BOX in data_dict and CARTODRUID_CONNECT_DATA_BOX in data_dict and
            CARTODRUID_CONNECT_DATA_LIST in data_dict and CARTODRUID_CONNECT_DATA_SELECTED_LAYERS in data_dict and
            CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS in data_dict)
        if contains_keys:
            return cls(ProjectData.from_dict(data_dict[CARTODRUID_CONNECT_PROJECT]), data_dict[CARTODRUID_CONNECT_CONFIG_BOX],
                       data_dict[CARTODRUID_CONNECT_IMAGE_BOX],data_dict[CARTODRUID_CONNECT_DATA_BOX],
                       data_dict[CARTODRUID_CONNECT_DATA_LIST], data_dict[CARTODRUID_CONNECT_DATA_LIST_FULL], data_dict[CARTODRUID_CONNECT_DATA_SELECTED_LAYERS],
                       data_dict[CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS])
        return ProjectWizardData()

