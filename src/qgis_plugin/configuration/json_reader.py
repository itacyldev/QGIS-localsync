import json
from typing import Tuple


class JsonReader:



    def _create_config_keys(self, new_config_load: list[dict]) -> list[dict]:
        """
            Create all the keys that are not present in the given config and return it.
            :param new_config_load: dictionary with the configuration layout.
            :return: dictionary with the configuration layout and all the keys present.
        """
        for config in new_config_load:
            if "source" not in config:
                config["source"] = ""
            if "destination" not in config:
                config["destination"] = ""
            if "includes" not in config:
                config["includes"] = []
            if "excludes" not in config:
                config["excludes"] = []
        return new_config_load


    def create_config_from_text(self, json_text: str, bars_changed: bool) -> Tuple[bool, list[dict]]:
        """
            Create a configuration dictionary from the given text. Changes de bars \\ for /.
            :param json_text: string with the configuration as json text.
            :param bars_changed: boolean indicating has been changed.
            :return: Boolean indicating if the configuration was created successfully and the configuration dictionary.
        """
        new_config = [{}]
        try:
            if json_text:
                new_config_load = json.loads(json_text)
                new_config_load = self._create_config_keys(new_config_load)
                return False, new_config_load
            return False, new_config

        except json.JSONDecodeError:
            if bars_changed:
                return True, new_config
            else:
                sources = self._find_text_on_config(json_text, '"source"')
                destinations = self._find_text_on_config(json_text, '"destination"')

                text = self._change_bars_from_text(json_text, sources, is_destination=False)
                text = self._change_bars_from_text(text, destinations, is_destination=True)
                return self.create_config_from_text(text, True)



    def _find_text_on_config(self, json_text: str, text: str) -> list[int]:
        """
            Find a string in the given json_text, all matches and returns their index.
            :param json_text: string json where the string will be searched
            :param text: string with the text to search
            :return: list with the index of the strings found
        """
        found_list = []
        pos = 0
        while True:
            pos = json_text.find(text, pos)
            if pos != -1:
                found_list.append(pos)
                pos += 1
            else:
                break
        return found_list


    def _change_bars_from_text(self, text: str, keys_found: list[int], is_destination: bool) -> str:
        """
            Organize the json text and the list of index to give the _analyze_and_change_process the correct
            parameters.
            :param text: string json where the bars will be searched
            :param keys_found: list of index from where the bars will be searched and changed.
            :param is_destination: boolean that indicated if the key from text json that
             gave keys_found is "destination" (True) or "source" (False)
            :return: string json with the bars changed in the correct places.
        """

        add_to_idx_start = 8
        if is_destination:
            add_to_idx_start = 13

        text_list = list(text)
        if keys_found:
            for pos in keys_found:
                self._analyze_and_change_process(text_list, pos, add_to_idx_start)
        return "".join(text_list)


    def _analyze_and_change_process(self, text_list: list[str], pos: int, add_idx_start: int):
        """
            Check the list of letters text list, from the position pos + add_idx_start, checking the number of times that
            quotes are found to change the bars in the correct places.
            :param text_list: json string converted to list of characters (not string).
            :param pos: Position where the key was found.
            :param add_idx_start: length of the key string.
            :return: json string with the bars changed for the current key.
        """
        search_quotes = '"'
        bar = "\\"
        number_of_times_found = 0
        for idx, letter in enumerate(text_list[pos + add_idx_start:]):
            if letter == search_quotes:
                number_of_times_found += 1
            if number_of_times_found == 1 and letter == bar:
                text_list[pos + add_idx_start + idx] = "/"
            if number_of_times_found >= 2:
                break
