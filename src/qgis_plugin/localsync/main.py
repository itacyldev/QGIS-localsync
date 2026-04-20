import argparse
import logging
import sys

from core.sync_engine import SyncEngine
from qgis_plugin.localsync.project.project_manager import ProjectManager
from qgis_plugin.localsync.project.sync_mapper_reader import SyncMapperReader
from qgis_plugin.localsync.host.host_manager import HostManager


def call_push_pull(args, logger, sync, pull):
    if not args.sync_config:
        logger.info("With the pull/push command the parameters --sync_config is required.")
        sys.exit(1)
    if not args.device_id:
        devices_found = sync.discover_devices()
        if devices_found and len(devices_found) > 0:
            if len(devices_found) > 1:
                logger.info("Found more than one device connected and not device id was provided. Exiting.")
                sys.exit(1)
            device_found = devices_found[0]
        else:
            device_found = None
    else:
        device_found = next((device for device in sync.discover_devices() if device.device_id == args.device_id), None)
    if not device_found:
        logger.info("Device not found.")
        sys.exit(1)
    mapper = SyncMapperReader()
    mapper.mapper_reader(args.sync_config)
    for file_sync_map in mapper.sync_mappers_data:
        filters = (file_sync_map.convert_mapper_reader_regex_list_to_regex_filter_list(False) +
                   file_sync_map.convert_mapper_reader_regex_list_to_regex_filter_list(True))
        device_found.path_to_project = file_sync_map.destination
        host = HostManager("", file_sync_map.source)
        sync.file_transport(device_found, host, filters, pull)


def main():

    parser = argparse.ArgumentParser(description="crtdrd-qgis_plugin program arguments")
    parser.add_argument("protocol", help="Select between mtp and adb protocol")
    parser.add_argument("command",help="Command that you wish to run")
    parser.add_argument("--sync_config",
                        help="Json file with the same structure that example.json with the data that you want to transfer.")
    parser.add_argument("--device_id",
                        help="Device identificator, that you can get when running crtsync devices")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


    if args.protocol == "adb" or args.protocol == "mtp":
        SyncEngine.activate_mtp_or_adb(args.protocol == "adb")
    else:
        logger.info("Provided protocol not supported. Use only adb or mtp.")
    sync = SyncEngine()


    if args.command == "projects":
        pr_man = ProjectManager(sync)
        pr_man.list_projects(args.device_id) # Comprobar

    if args.command == "devices":
        devices = sync.discover_devices()
        logger.info("%s", devices)

    if args.command == "push":
        call_push_pull(args, logger, sync, False)

    if args.command == "pull":
        call_push_pull(args, logger, sync, True)

if __name__ == "__main__":
    main()