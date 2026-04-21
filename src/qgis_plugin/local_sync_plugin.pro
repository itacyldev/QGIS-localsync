FORMS += \
    dialog/messages_dialog.ui \
    dialog/localsync_conf_panel.ui \
    dialog/localsync_save_layers.ui \
    dialog/project_wizard/project_wizard.ui \
    dialog/project_wizard/add_layers_page.ui \
    dialog/project_wizard/photo_layer_page.ui \


SOURCES += \
    localsync/device/mtp_device_locator.py \
    localsync/device/adb_device_locator.py \
    localsync/device/device_manager.py \
    localsync/transporter/mtp_transporter.py \
    localsync/transporter/adb_transporter.py \
    localsync/channels/mtp_channel.py \
    localsync/channels/adb_channel.py \
    localsync/core/sync_engine.py \
    localsync/project/project_manager.py \
    configuration/configuration_manager.py \
    configuration/photo_layers_configuration.py \
    tasks/read_devices.py \
    tasks/search_projects.py \
    tasks/read_config_file_carto.py \
    tasks/download_task.py \
    tasks/load_files.py \
    ui_controllers/devices_combo.py \
    dialog/localsync_conf_panel.py \
    dialog/messages_dialog.py \
    dialog/project_wizard/project_wizard.py \
    dialog/project_wizard/wizard_pages/file_selector.py \
    dialog/project_wizard/wizard_pages/photo_layer.py \
    dialog/project_wizard/wizard_pages/project_finder.py \
    dialog/project_wizard/wizard_pages/add_layers.py \
    events/project_configuration_changed.py \
    local_sync_plugin.py



TRANSLATIONS += \
    i18n/local_sync_plugin.ts