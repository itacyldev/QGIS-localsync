import json
import logging

from typing import List
from ...constants import QGIS_PLUGIN_NAME
from ... import constants
from ...logger.qgis_logger_handler import QgisLoggerHandler


class SyncMapperData:

    """
        Save the configuration of a connection.
    """

    def __init__(self, source: str = "", destination: str="", includes: list[str]=None, excludes:list[str]=None):

        """
            Constructor.
            :param source: string path to pc folder where the files will be transported.
            :param destination: string path to device folder where the files will be transported.
            :param includes: list of string with glob filters. Used as a filter that will include those paths that fulfill one of them.
            :param excludes: list of string with glob filters. Used as a filter that will exclude those paths that fulfill one of them.
        """

        if includes is None:
            self.includes = []
        else:
            self.includes = includes
        if excludes is None:
            self.excludes = []
        else:
            self.excludes = excludes
        self.source = source
        self.destination = destination


    def to_dict(self):
        return {
            "source": self.source,
            "destination": self.destination,
            "includes": self.includes,
            "excludes": self.excludes,
        }


class SyncMapperReader:

    """
        Old class used to read the configuration JSON.
        :ivar logger: logger of the application. Used to keep logs.
        :vartype logger: QgisLoggerHandler
        :ivar sync_mappers_data: list of all the configurations found a loaded.
        :vartype sync_mappers_data: list[SyncMapperData]
    """

    def __init__(self):
        self.sync_mappers_data = []
        self.logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()


    def mapper_reader(self, json_path: str):
        """
        Read a json and fill self.sync_mappers_data with it.
        :param json_path: path to the json file.
        """
        json_data = self.read_json_from_path(json_path)
        try:
            for item in json_data:
                mapper_data = SyncMapperData()
                mapper_data.source = item[constants.SYNC_MAPPER_SOURCE_KEY]
                mapper_data.destination = item[constants.SYNC_MAPPER_DESTINATION_KEY]
                mapper_data.includes = item[constants.SYNC_MAPPER_INCLUDES_KEY]
                mapper_data.excludes = item[constants.SYNC_MAPPER_EXCLUDES_KEY]
                self.sync_mappers_data.append(mapper_data)
        except KeyError as e:

            self.logger.error("KeyError: " + str(e))
            return


    def read_json_from_path(self, path: str)-> dict:
        '''
            Read a json and create a dictionary from it.
            :param path: string path to json file.
            :result: dictionary with the json content.
        '''
        with open(path, "r", encoding="utf-8") as f:
            json_dict = json.load(f)
        return json_dict

    def write_json_in_path(self, path: str, data: str):
        '''
            Write a json and from a dictionary.
            :param path: string path where the json will be written.
            :param data: dictionary with the json content.
        '''
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)