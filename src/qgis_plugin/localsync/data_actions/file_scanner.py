from pathlib import Path


class FileScanner:

    @staticmethod
    def filter_files_list(file_list: list[Path], glob_filters: list[str], include: bool)-> list:
        """
            Filter the files found in file_list, to include/exclude the ones that fulfill glob_filters.
            :param file_list: list of Path objects containing the files to be filtered. (Result of channel.get_file_list)
            :param glob_filters: list of string glob filters that will be applied to the list of files.
            :param include: bool that indicates whether the filtered file should be included or not.
            :return: list of Path objects containing the files filtered.
        """
        if glob_filters:
            file_list_copy = []
            for path in file_list:
                for filt in glob_filters:
                    if path.match(filt) == include: ## Path.glob don't accept double asterisk. Alternative not found.
                        file_list_copy.append(path)
                        break
            return file_list_copy
        else:
            return file_list

