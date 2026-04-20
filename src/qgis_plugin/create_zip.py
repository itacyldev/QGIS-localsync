#!/usr/bin/env python
# coding=utf-8
import shutil
import sys
import getpass
import xmlrpc.client
import zipfile
from optparse import OptionParser
import os
from pathlib import Path


# standard_library.install_aliases()



def zip_deploy(deploy_folder: str, zip_filename: str):
    """
        Copies the necessary resources for the plugin and writes them inside a zip file.
        :param deploy_folder: folder where the zip file is located.
        :param zip_filename: name of the zip file.
    """
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
    excluded_folders = ["test", "scripts", "venv", "build", "__pycache__"]
    excluded_files = ["Makefile","pb_tool.cfg","pylintrc","README.txt", "README.html", "create_zip.py", "main.py", "resource.qrc"]
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(deploy_folder):
            # filter dirs variable inline to filter zip contents
            dirs[:] = [d for d in dirs if d not in excluded_folders and not d.startswith(".")]
            files[:] = [f for f in files if f not in excluded_files]
            for file in files:
                zf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file),
                                                                   os.path.join(deploy_folder, '..')))


def copy_resources(base_folder:str, deploy_folder:str):
    """
        Create a copy of the project excluding some folders.
        :param base_folder: base folder from whom the project will be copied.
        :param deploy_folder: folder where the project will be copied.
    """
    excluded_folders = ["test", "scripts", "venv", "build", "__pycache__"]
    # copy selected folders and contents to build
    contents = [f for f in os.listdir(base_folder) if not f.startswith(".") and f not in excluded_folders]

    for path in contents:
        full_path = os.path.join(base_folder, path)
        if os.path.isdir(full_path):
            shutil.copytree(full_path, os.path.join(deploy_folder, path))
        else:
            shutil.copy(full_path, os.path.join(deploy_folder, path))
    copy_readme(base_folder, deploy_folder)




def copy_readme(base_folder: str, deploy_folder: str):
    readme_path = (Path(base_folder).parent.parent / "readme.md").as_posix()
    deploy_path = Path(os.path.join(deploy_folder, "readme.md")).as_posix()
    shutil.copy(readme_path, deploy_path)



def create_zip(base_folder:str):
    """
        Create the necessary folders where a zip file will be created. Also copies the project and creates the zip file.
        :param base_folder: base folder from whom the project will be copied.
    """
    build_folder = os.path.join(base_folder, "build")
    if os.path.exists(build_folder):
        shutil.rmtree(build_folder)
    os.mkdir(build_folder)
    deploy_folder = os.path.join(build_folder, "CRTSYN")
    os.mkdir(deploy_folder)

    copy_resources(base_folder, deploy_folder)
    zip_filename = os.path.join(build_folder, "CRTSYN.zip")
    zip_deploy(deploy_folder, zip_filename)
    shutil.rmtree(deploy_folder)
    return zip_filename


if __name__ == "__main__":
    # create zip file before sending
    zip_file = create_zip(os.getcwd())
    print(f"Created zip file {zip_file}")