import json
import logging
import os
import traceback
from pathlib import Path
from typing import Tuple

from PyQt5.QtCore import QVariant
from PyQt5.QtWidgets import QMessageBox

from qgis import processing
from qgis._core import QgsLayerTreeGroup, QgsFeature, QgsMapLayer
from qgis.core import QgsEditorWidgetSetup, QgsLayerTreeLayer, QgsVectorLayer, QgsProject, QgsVectorFileWriter
from ..constants import WIZARD_PHOTO_LAYERS_HTML_NOTICE, QGIS_PLUGIN_NAME, WIZARD_LAYERS_GROUP_NAME, \
    WIZARD_PHOTO_LAYERS_GROUP_NAME, QGIS_SCOPE_NAME, CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS, \
    CARTODRUID_CONNECT_PHOTO_SAVE_LAYERS, CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS_IDS
from ..i18n import tr
from ..logger.qgis_logger_handler import QgisLoggerHandler



class PhotoLayersConfiguration:

    """
        Manages the configuration of the function to create photo layers automatically by the plugin.
        :ivar config: Stores the mapping between folder-name:layer-name.
        :vartype config: dict
        :ivar config_ids: Stores the mapping between layer-name:layer-id.
        :vartype config_ids: dict
        :ivar save_layers_in_gkpg: boolean that indicates whether the layers created will be persisted or not.
        :vartype save_layers_in_gkpg: bool
        :ivar ignore_remove: A flag to prevent the “remove layers” event from being triggered
        :vartype ignore_remove: bool
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: QgisLoggerHandler
    """


    config = {}
    save_layers_in_gkpg = False
    config_ids = {}
    ignore_remove = False

    def __init__(self):
        """
            Constructor
        """
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        self.read_config()
        QgsProject.instance().layerWillBeRemoved.connect(self.removed_layer_from_config)

    def removed_layer_from_config(self,layer_id:str):
        """
            Used in the event layerWillBeRemoved. Remove from config and config_ids the reference to the layer
            that will be removed.
            param: layer_id: the id of the layer to be removed.
        """
        if self.ignore_remove:
            return
        node = QgsProject.instance().mapLayer(layer_id)
        if node is None:
            return
        key_to_remove = None
        for k, v in self.config_ids.items():
            if v == node.id():
                key_to_remove = k
                break
        if key_to_remove:
            key_to_remove2 = None
            del self.config_ids[key_to_remove]
            for k, v in self.config.items():
                if v == key_to_remove:
                    key_to_remove2 = k
                    break
            if key_to_remove2:
                del self.config[key_to_remove2]
            self.save_config()



    def save_config(self):
        """
        Persist the values of config, config_ids and save_layers_in_gkpg in the QGIS project file.
        """
        project = QgsProject.instance()
        project.writeEntry(
            QGIS_SCOPE_NAME,
            CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS,
            json.dumps(self.config)
        )
        project.writeEntry(
            QGIS_SCOPE_NAME,
            CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS_IDS,
            json.dumps(self.config_ids)
        )
        project.writeEntry(
            QGIS_SCOPE_NAME,
            CARTODRUID_CONNECT_PHOTO_SAVE_LAYERS,
            self.save_layers_in_gkpg
        )


    def change_save_config_value(self, new_value:bool):
        """
            Change the value of save_layers_in_gkpg and persist it.
            param new_value: new value that will be stored in save_layers_in_gkpg.
        """
        self.save_layers_in_gkpg = new_value
        self.save_config()


    def read_config(self):
        """
            Read the configurations from the QGIS project file.
        """
        project = QgsProject.instance()

        value, ok = project.readEntry(
            QGIS_SCOPE_NAME,
            CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS
        )
        try:
            if ok:
                self.config = json.loads(value)
        except json.JSONDecodeError:
            self.logger.warning("Json malformed. The json provided for photo_config is malformed.")
            self.logger.warning(value)
            QMessageBox.warning(None, "Json malformed", tr("The json provided for photo_config is malformed."))

        value, ok = project.readEntry(
            QGIS_SCOPE_NAME,
            CARTODRUID_CONNECT_PHOTO_SELECTED_LAYERS_IDS
        )
        try:
            if ok:
                self.config_ids = json.loads(value)
        except json.JSONDecodeError:
            self.logger.warning("Json malformed. The json provided for photo_config_ids is malformed.")
            self.logger.warning(value)
            QMessageBox.warning(None, "Json malformed", tr("The json provided for photo_config_ids is malformed."))

        project = QgsProject.instance()
        value, ok = project.readEntry(
            QGIS_SCOPE_NAME,
            CARTODRUID_CONNECT_PHOTO_SAVE_LAYERS
        )
        if ok:
            self.save_layers_in_gkpg = value == "True"


    def add_to_config(self, folder_name:str, layer_name:str):
        """
            Add a new record to the config.
            param folder_name: key for the new record.
            param layer_name: value for the new record.
        """
        if layer_name and folder_name:
            if layer_name in self.config.values():
                self.config = {k: v for k, v in self.config.items() if v != layer_name}
            self.config[folder_name] = layer_name
            self.save_config()

    def add_to_config_ids(self, layer:QgsVectorLayer):
        """
            Add a new record to the config_ids.
            param layer: from whom the name and the id will be stored as the new record.
        """
        self.config_ids[layer.name()] = layer.id()

    def save_new_config(self, config:dict):
        """
            Change the config with a new value. Also, this causes that the config_ids have to be changed trying to
            use the new values with the old ones.
            Finally, the new values are saved in the QGIS project file.
            param config: new config that will be saved.
        """
        dict_of_keys_to_change = {}
        for key in self.config_ids:
            if key not in config.values() and key in self.config.values():
                for k, v in self.config.items():
                    if v == key and k in config:
                        dict_of_keys_to_change[config[k]] = key
        if dict_of_keys_to_change:
            self.change_layer_names(dict_of_keys_to_change)
            for key in dict_of_keys_to_change:
                self.config_ids[key] = self.config_ids.pop(dict_of_keys_to_change[key])


        self.config = config
        self.save_config()

    def get_save_layers_bool(self) -> bool:
        """
            save_layers_in_gkpg getter.
            :return: bool save_layers_in_gkpg.
        """
        return self.save_layers_in_gkpg

    def set_save_layers_bool(self, save:bool):
        """
        save_layers_in_gkpg setter. Also, the new value is saved in the QGIS project file.
        :param save: bool save_layers_in_gkpg.
        """
        self.save_layers_in_gkpg = save
        self.save_config()

    def change_layer_names(self, dict_of_keys_to_change:dict):
        """
        Change the names of the layers indicated by new ones.
        :param dict_of_keys_to_change: Key: new name of the layer, value: id of the layer to be changed.
        """
        for key in dict_of_keys_to_change:
            layer = QgsProject.instance().mapLayer(self.config_ids[dict_of_keys_to_change[key]])
            if layer:
                layer.setName(key)

    def restart_config(self):
        """
        Restart the config. The config_ids is not restarted and will be updated when the next download happens.
        """
        self.config = {}

    def get_photo_group(self)->QgsLayerTreeGroup:
        """
        Return the QgsLayerTreeGroup where the photo layers have to be saved in the TOC. If the group does not existe
        then it is created.
        :return: The group where the photo layers should be saved.
        """
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(WIZARD_LAYERS_GROUP_NAME)
        if not group:
            group = root.addGroup(WIZARD_LAYERS_GROUP_NAME)
        photo_group = group.findGroup(WIZARD_PHOTO_LAYERS_GROUP_NAME)
        if not photo_group:
            photo_group = group.addGroup(WIZARD_PHOTO_LAYERS_GROUP_NAME)
        return photo_group


    def create_or_update_photo_layers(self):
        """
        Main process, where the records in config will be used to create the corresponding layers and populate config_ids
        with the layers created/updated.
        """
        if self.config:
            pictures_folder = os.path.join(
                Path(QgsProject.instance().absolutePath()).as_posix(),
                "cartodruid",
                "pictures"
            )
            for folder_name in self.config:
                folder = os.path.join(pictures_folder, folder_name)
                layer = self._create_or_modify_photo_layer(folder, self.config[folder_name])
                if self.save_layers_in_gkpg and layer:
                    self._create_or_modify_gkpg_file_and_use_on_toc(folder, folder_name, layer)
            for key, value in self.config_ids.items():
                project = QgsProject.instance()
                if not project.mapLayer(value):
                    del self.config[key]



    def delete_photo_group_if_empty(self, photo_group:QgsLayerTreeGroup):
        if len(photo_group.children()) == 0:
            parent = photo_group.parent()
            if parent:
                parent.removeChildNode(photo_group)
                if len(parent.children()) == 0:
                    root = parent.parent()
                    if root:
                        root.removeChildNode(parent)


    def _create_or_modify_gkpg_file_and_use_on_toc(self, folder:str, folder_name:str, layer:QgsVectorLayer):
        """
            Create the files from the temporal layers created by the _create_or_modify_photo_layer method.
            If the layer provided is not temporary, then the file is not recreated.
            :param folder: path to the folder with the images of the layer created.
            :param folder_name: name of the folder with the images of the layer created.
            :param layer: layer created in a previous step with the geospatial images from folder.
        """
        if not layer:
            return
        if not layer.isTemporary():
            self.logger.info(f"Layer {layer.name()} already up to date.")
            return

        file = Path(folder).parent / (folder_name + ".gpkg")
        project = QgsProject.instance()

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = layer.name()
        options.actionOnExistingFile = QgsVectorFileWriter.ActionOnExistingFile.CreateOrOverwriteFile
        error = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            file.as_posix(),
            QgsProject.instance().transformContext(),
            options
        )
        new_layer = QgsVectorLayer(f"{file.as_posix()}|layername={layer.name()}", layer.name(), "ogr")
        new_layer.setMapTipTemplate(WIZARD_PHOTO_LAYERS_HTML_NOTICE)
        self._apply_widget_setup(new_layer)
        parent = layer.parent()
        self.ignore_remove = True
        if isinstance(parent, QgsLayerTreeGroup):
            index = parent.children().index(layer)
            project.addMapLayer(new_layer, False)
            parent.insertLayer(index, new_layer)
            parent.removeChildNode(layer)
        else:
            photo_group = self.get_photo_group()
            project.addMapLayer(new_layer, False)
            photo_group.addLayer(new_layer)
            photo_group.removeLayer(layer)
        self.ignore_remove = False
        if error[0] == 0:
            self.add_to_config_ids(new_layer)
            self.logger.info("Photo layer " + layer.name() + " saved correctly.")
        else:
            self.logger.error("There was an error while trying to create or modify the layer " + layer.name() + ". Error"
                            ":" + str(error))


    def _apply_widget_setup(self, layer:QgsVectorLayer):
        """
        Changes necessary for any layer created for the photo layer. Changes the options to add the necessary visualizations
        on the identification spatial objects' menu.
        :param layer: layer where the options need to be applied.
        """
        idx_photo = layer.fields().indexFromName("photo")
        idx_directory = layer.fields().indexFromName("directory")
        layer.setEditorWidgetSetup(idx_photo, QgsEditorWidgetSetup(
            "ExternalResource",
            {
                'DocumentViewer': 1,
                'FileWidget': True,
                'FileWidgetButton': True,
                'RelativeStorage': 0,
                'UseLink': True,
                'FullUrl': True
            }
        ))
        layer.setEditorWidgetSetup(idx_directory, QgsEditorWidgetSetup(
            "ExternalResource",
            {
                'DocumentViewer': 1,
                'FileWidget': True,
                'FileWidgetButton': True,
                'StorageMode': 1,
                'RelativeStorage': 0,
                'UseLink': True,
                'FullUrl': True
            }
        ))


    def change_layer_name(self, old_layer_name:str, layer:QgsMapLayer):
        """
            Change the name of a photo layer, updating the options and creating a unique name.
            :param old_layer_name: name of the layer before it was changed.
            :param layer: layer with the new name.
        """
        new_layer_name = layer.name()
        if new_layer_name in self.config_ids:
            QMessageBox.critical(None, "CartoDruid device sync",
                                 tr("The Photo layers created by the plugin can't have the same name."
                                    "The layer name will be changed to a new one available."))
            for number in range(0,100):
                new_name = new_layer_name +"_"+ str(number)
                if new_name not in self.config_ids:
                    layer.setName(new_name)
                    new_layer_name = new_name
                    break
            self.config_ids[new_layer_name] = self.config_ids.pop(old_layer_name)
            key = None
            for k, v in self.config.items():
                if v == old_layer_name:
                    key = k
                    break
            if key:
                self.config[key] = new_layer_name



    def _create_or_modify_photo_layer(self, folder:str, layer_name:str) -> QgsVectorLayer:
        """
            Create a new temporal photo layer using the importphotos process. Changes the layer created to add the necessary options
            to be the same as if the user used the process from the QGIS GUI.
            :param folder: folder where the photos are located.
            :param layer_name: name of the new created layer.
            :param photo_group: QgsLayerTreeGroup containing the new layer created.
            :return: The layer created or found. None if it was not created of found.
        """
        path_folder = Path(folder)
        if path_folder.exists() and path_folder.is_dir() and any(path_folder.iterdir()):
            photo_group = self.get_photo_group()
            new_photo_layer = processing.run("native:importphotos",
                                             {'FOLDER': folder,
                                              'RECURSIVE': False, 'OUTPUT': 'TEMPORARY_OUTPUT'})
            layer = new_photo_layer['OUTPUT']
            layer.setName(layer_name)
            layer.setMapTipTemplate(WIZARD_PHOTO_LAYERS_HTML_NOTICE)
            self._apply_widget_setup(layer)
            if layer_name in self.config_ids:
                old_layer = QgsProject.instance().mapLayer(self.config_ids[layer_name])
                if old_layer.name() != layer_name:
                    self.change_layer_name(layer_name, old_layer)
                if isinstance(old_layer, QgsVectorLayer):
                    old_layer = self._edit_older_layer(old_layer, layer)
                    return old_layer

            QgsProject.instance().addMapLayer(layer, False)
            photo_group.addLayer(layer)
            self.logger.info("Photo layer " + layer.name() + " created correctly.")
            self.add_to_config_ids(layer)
            return layer
        else:
            self.logger.info("The folder with the name " + Path(folder).name + " could not be found or was empty, so no photo layer"
                                                                               " was created.")
        return None


    def _edit_older_layer(self,old_layer:QgsVectorLayer, new_layer:QgsVectorLayer) -> QgsVectorLayer:
        """
        Change the values in an old layer with the values found in the new one.
        :param old_layer: Layer that will be changed.
        :param new_layer: Layer from whom the values will be read
        :return: The old layer with the new values.
        """
        old_layer.startEditing()
        old_layer.dataProvider().truncate()
        feature_list = []
        fields = old_layer.fields()
        for feature in new_layer.getFeatures():
            new_feature = QgsFeature(fields)
            new_feature.setGeometry(feature.geometry())
            for field in fields:
                name = field.name()
                if name == 'fid':  # autogenerado por gpkg
                    continue
                try:
                    val = feature[name]
                except KeyError:
                    val = None
                if field.type() == QVariant.Int and isinstance(val, str):
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        val = None
                new_feature.setAttribute(name, val)
            feature_list.append(new_feature)
        old_layer.dataProvider().addFeatures(feature_list)
        old_layer.commitChanges()
        return old_layer

    def unload(self):
        """
        Disconnect the layerWillBeRemoved event.
        """
        try:
            QgsProject.instance().layerWillBeRemoved.disconnect(self.removed_layer_from_config)
        except TypeError:
            self.logger.error("Error while trying to disconnect layerWillBeRemoved signal from PhotoLayersConfiguration class.")