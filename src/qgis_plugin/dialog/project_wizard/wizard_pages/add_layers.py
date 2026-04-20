import os
from pathlib import Path

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QWizardPage, QTreeWidgetItem

from qgis.PyQt.Qt import Qt

from qgis.PyQt import uic
from qgis._core import QgsVectorLayer, QgsProject
from ....constants import WIZARD_LAYERS_GROUP_NAME

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), '..', 'add_layers_page.ui'))


class AddLayers(QWizardPage, FORM_CLASS):

    """
        Manages the 3rd page of the Cartodruid Project Wizard. It presents the layers from the selected files in the previous step,
        and let the user select them to add them to the QGIS TOC.
    """

    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.tree_layers.itemChanged.connect(self.handle_item_changed)


    def get_layer_icon(self, geometry_type: str) -> QIcon:
        """
        Returns the QIcon for the given geometry type. If the geometry type is not valid, returns a default table QIcon.
        :param geometry_type: Geometry type that will be assigned with an icon.
        :return: QIcon for the given geometry type.
        """
        icons = {
            "Point": QIcon(":/images/themes/default/mIconPointLayer.svg"),
            "MultiPoint": QIcon(":/images/themes/default/mIconPointLayer.svg"),
            "LineString": QIcon(":/images/themes/default/mIconLineLayer.svg"),
            "MultiLineString": QIcon(":/images/themes/default/mIconLineLayer.svg"),
            "Polygon": QIcon(":/images/themes/default/mIconPolygonLayer.svg"),
            "MultiPolygon": QIcon(":/images/themes/default/mIconPolygonLayer.svg")
        }
        return icons.get(geometry_type, QIcon(":/images/themes/default/mIconTableLayer.svg"))


    def initializePage(self):
        """
            Initialise the page with the necessary data to populate the treeWidget of the .ui
            Managed by QGIS, it is launched when the page is loaded.
        """
        self.tree_layers.clear()
        self.wizard().logger.info("Searching for layers in files...")
        preselected_layers = self.wizard().current_options.data_selected_layers
        for config in self.wizard().c_manager.convert_config_relative_path_to_absolute(self.wizard().c_manager.config):
            source = Path(config["source"])
            if source.name != "data":
                source = source / "data"

            for file in self.wizard().current_options.data_list_selected_files:
                full_path_file = source / file
                if os.path.isfile(full_path_file):
                    layer = QgsVectorLayer(full_path_file.as_posix(), "temp", "ogr")
                    sublayers = layer.dataProvider().subLayers()
                    parent_item = QTreeWidgetItem(0)
                    parent_item.setText(0, file)
                    parent_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    parent_item.setIcon(0, QIcon(":/images/themes/default/propertyicons/database.svg"))
                    parent_item.setCheckState(0, Qt.Unchecked)
                    self.wizard().logger.info("New parent item " + parent_item.text(0))
                    for sublayer in sublayers:
                        # Formato: "índice!!::!!nombre!!::!!geometría!!::!!tipo"
                        parts = sublayer.split("!!::!!")
                        layer_name = parts[1]
                        geom_type = parts[3]
                        item = QTreeWidgetItem([layer_name])
                        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                        if preselected_layers and file in preselected_layers and layer_name in preselected_layers[file]:
                            item.setCheckState(0, Qt.Checked)
                        else:
                            item.setCheckState(0, Qt.Unchecked)
                        item.setIcon(0, self.get_layer_icon(geom_type))
                        item.setData(0, Qt.UserRole, full_path_file)
                        self.wizard().logger.info("New child item " + item.text(0))
                        parent_item.addChild(item)
                    self.tree_layers.addTopLevelItem(parent_item)
                    parent_item.setExpanded(True)
        self.wizard().logger.info("Searching for layers in files ended.")

        self.check_parent_if_all_child_checked()


    def check_parent_if_all_child_checked(self):
        """
        Auto-check parent item if all the child items are checked.
        """
        root = self.tree_layers.invisibleRootItem()
        for i in range(root.childCount()):
            all_checked = True
            parent_item = root.child(i)
            for j in range(parent_item.childCount()):
                item = parent_item.child(j)
                if item.checkState(0) == Qt.Unchecked:
                    all_checked = False
                    break
            if all_checked:
                parent_item.setCheckState(0, Qt.Checked)

    def handle_item_changed(self, item: QTreeWidgetItem, column: int):
        """
        Handle item changes. Connected to itemChanged event for treeWidget.
        :param item: Item that has been changed.
        :param column: Column index.
        """

        state = item.checkState(0)
        self.update_item(item, state)

    def update_item(self, item: QTreeWidgetItem, state: Qt.CheckState):
        """
        Try to update the children of the item (if it has) setting the state to the state given.
        :param item: item from where the changes will be performed.
        :param state: state of the item.
        """
        self.tree_layers.blockSignals(True)
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
        if item.parent():
            if state == Qt.Unchecked:
                item.parent().setCheckState(0, Qt.Qt.Unchecked)
            else:
                all_checked = True
                for child in range(item.parent().childCount()):
                    if item.parent().child(child).checkState(0) == Qt.Unchecked:
                        all_checked = False
                        break
                if all_checked:
                    item.parent().setCheckState(0, Qt.Checked)
                else:
                    item.parent().setCheckState(0, Qt.Unchecked)
        self.tree_layers.blockSignals(False)


    def add_new_layer_to_save_state(self,key: str,value: str):
        """
            Adds a new layer to the ProjectWizardData selected layers property.
            :param key: file name from where the layer was retrieved.
            :param value: name of the layer to add.
        """
        if key in self.wizard().current_options.data_selected_layers:
            if value not in self.wizard().current_options.data_selected_layers[key]:
                self.wizard().current_options.data_selected_layers[key].append(value)
        else:
            self.wizard().current_options.data_selected_layers[key] = [value]


    def look_and_remove_value_and_key(self, key, value):
        """
            Removes the value from the ProjectWizardData selected layers property.
            If after removing the value the key have no value, then it also deletes the key.
            :param key: file name from where the layer was retrieved.
            :param value: name of the layer to remove.
        """
        selected_layers = self.wizard().current_options.data_selected_layers
        if key in selected_layers and value in selected_layers[key]:
            selected_layers[key].remove(value)
            if not selected_layers[key]:
                del selected_layers[key]
        self.wizard().current_options.data_selected_layers = selected_layers



    def validatePage(self):

        """
            Adds the selected layers from the wizard to the QGIS TOC. Also saves the selected files and layers into the wizard current_options property.
        """

        root = self.tree_layers.invisibleRootItem()
        loaded_uris = []
        self.wizard().logger.info("Adding new layers to TOC.")
        tree_root = QgsProject.instance().layerTreeRoot()
        group = tree_root.findGroup(WIZARD_LAYERS_GROUP_NAME)
        for layer in QgsProject.instance().mapLayers().values():
            parts = layer.source().split("|")
            path = parts[0]
            params = {}
            for p in parts[1:]:
                k, v = p.split("=")
                params[k] = v
            if "layername" in params:
                self.add_new_layer_to_save_state(Path(path).name, params["layername"])
            loaded_uris.append(layer.source())
        for i in range(root.childCount()):
            parent_item = root.child(i)
            for j in range(parent_item.childCount()):
                item = parent_item.child(j)
                layer_name = item.text(0)
                db_path = item.data(0, Qt.UserRole)
                if item.checkState(0) == Qt.Checked:
                    uri = f"{Path(db_path).as_posix()}|layername={layer_name}"
                    if uri not in loaded_uris:
                        vlayer = QgsVectorLayer(uri, layer_name, "ogr")
                        if vlayer.isValid():
                            self.wizard().logger.info("Adding layer " + layer_name)
                            QgsProject.instance().addMapLayer(vlayer, False)
                            if not group:
                                group = tree_root.addGroup(WIZARD_LAYERS_GROUP_NAME)
                            group.addLayer(vlayer)
                            self.add_new_layer_to_save_state(Path(db_path).name,layer_name)
                    else:
                        self.wizard().logger.info("Layer " + layer_name + " already exists in TOC.")
                else:
                    self.look_and_remove_value_and_key(Path(db_path).name, layer_name)
        self.wizard().save_carto_project_selections()
        return True