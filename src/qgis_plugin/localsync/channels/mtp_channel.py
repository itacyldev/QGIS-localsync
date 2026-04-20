import json
import os
import shutil
import uuid
from pathlib import Path
import subprocess
import platform
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from ...i18n import tr

from ...constants import QGIS_PLUGIN_NAME
from ...logger.qgis_logger_handler import QgisLoggerHandler
#Linux configuration
if platform.system() != "Windows":
    subprocess.CREATE_NO_WINDOW = 0


class MtpErrorType(Enum):
    SO_NOT_SUPPORTED = tr("Operative System not supported")
    POWERSHELL_NOT_FOUND = tr("Powershell not found")
    POWERSHELL_DISABLED = tr("Powershell disabled or blocked")
    EXECUTION_POLICY = tr("Execution policy too restrictive")
    PERMISSIONS_ERROR = tr("Not enough permissions")
    NO_DEVICE_CONNECTED = tr("No device connected")
    MTP_DISABLED = tr("MTP disabled in the device")
    SHELL_APPLICATION_ERROR = tr("Shell.Application error (COM)")
    SUBPROCESS_ERROR = tr("Error while executing subprocess")
    UNKNOWN_ERROR = tr("Unknown error")


@dataclass
class MtpStatus:
    available: bool
    error_type: Optional[MtpErrorType]
    error_message: str
    details: dict


class MtpChannel:

    """
        Group of methods that use adb to query/change data on the mobile device using MTP.

        :ivar _selected_device_id_path: virtual path of the device currently using.
        :vartype _selected_device_id_path: str
        :ivar _powershell_path: path to the PowerShell executable.
        :vartype _powershell_path: str
    """

    _selected_device_id_path = ""
    _powershell_path = None

    class MtpChecker:

        def check_availability(self) -> MtpStatus:
            """
                Verify the availability of MTP and returns the current state
                :return: MtpStatus of the current state.
            """

            # 1. Verificar SO
            if not self._check_os():
                return MtpStatus(
                    available=False,
                    error_type=MtpErrorType.SO_NOT_SUPPORTED,
                    error_message="MTP only available on Windows. Current OS: {OS}".format(OS=platform.system()),
                    details={"os": platform.system(), "version": platform.version()}
                )

            # 2. Verificar PowerShell
            ps_check = self._check_powershell()
            if not ps_check["available"]:
                return MtpStatus(
                    available=False,
                    error_type=ps_check["error_type"],
                    error_message=ps_check["message"],
                    details=ps_check
                )

            # 3. Verificar Shell.Application
            shell_check = self._check_shell_application()
            if not shell_check["available"]:
                return MtpStatus(
                    available=False,
                    error_type=shell_check["error_type"],
                    error_message=shell_check["message"],
                    details=shell_check
                )

            return MtpStatus(
                available=True,
                error_type=None,
                error_message="MTP available",
                details={}
            )

        def _check_os(self) -> bool:
            """
                Verify that OS is Windows
                :return: True if the OS is Windows. False otherwise.
            """
            return platform.system() == "Windows"

        def _check_powershell(self) -> dict:
            """
                Verify that powershell is available and functional.
                :return: MtpStatus of the current state.
            """
            try:
                cmd = "echo 'test'"
                result = MtpChannel.get_result_script(cmd, True, True)

                if result.returncode == 0:
                    return {"available": True, "version": self._get_ps_version()}
                else:
                    return {
                        "available": False,
                        "error_type": MtpErrorType.POWERSHELL_DISABLED,
                        "message": "PowerShell returned {result} code".format(result = result.returncode),
                        "stderr": result.stderr
                    }

            except FileNotFoundError:
                return {
                    "available": False,
                    "error_type": MtpErrorType.POWERSHELL_NOT_FOUND,
                    "message": "PowerShell not found on the system"
                }
            except subprocess.TimeoutExpired:
                return {
                    "available": False,
                    "error_type": MtpErrorType.SUBPROCESS_ERROR,
                    "message": "Powershell timeout."
                }
            except PermissionError:
                return {
                    "available": False,
                    "error_type": MtpErrorType.PERMISSIONS_ERROR,
                    "message": "Not enough permissions to execute Powershell"
                }
            except Exception as e:
                return {
                    "available": False,
                    "error_type": MtpErrorType.UNKNOWN_ERROR,
                    "message": f"Unknown error: {str(e)}"
                }

        def _check_shell_application(self) -> dict:
            """
                Verify that Shell.Application is available
                :return: MtpStatus of the current state.
            """
            ps_script = """
            try {
                $shell = New-Object -ComObject Shell.Application
                if ($shell) { 
                    Write-Output "OK" 
                } else { 
                    Write-Output "ERROR" 
                }
            } catch {
                Write-Output "EXCEPTION: $($_.Exception.Message)"
            }
            """

            try:
                result = MtpChannel.get_result_script(ps_script, True, True)

                if "OK" in result.stdout:
                    return {"available": True}
                elif "EXCEPTION" in result.stdout:
                    return {
                        "available": False,
                        "error_type": MtpErrorType.SHELL_APPLICATION_ERROR,
                        "message": "Error on Shell.Application COM",
                        "details": result.stdout
                    }
                else:
                    return {
                        "available": False,
                        "error_type": MtpErrorType.SHELL_APPLICATION_ERROR,
                        "message": "Shell.Application no available"
                    }

            except Exception as e:
                return {
                    "available": False,
                    "error_type": MtpErrorType.SUBPROCESS_ERROR,
                    "message": "Error when verifying Shell.Application: {error}".format(error=str(e))
                }


        def _get_ps_version(self) -> str:
            """
                Get Powershell version
                :return: MtpStatus of the current state.
            """
            try:
                cmd = "$PSVersionTable.PSVersion.ToString()"
                result = MtpChannel.get_result_script(cmd, True, True)
                return result.stdout.strip() if result.returncode == 0 else "Unknown"
            except Exception:
                return "Unknown"

    @staticmethod
    def is_available() -> MtpStatus:
        """
            Check if MTP is available in the system.
            :return: MtpStatus of the current state.
        """
        checker = MtpChannel.MtpChecker()
        return checker.check_availability()

    @staticmethod
    def get_selected_device_id_path() -> str:
        """
        Get the current selected device virtual path.
        :return: string with the current virtual path from the device selected.
        """
        return MtpChannel._selected_device_id_path

    @staticmethod
    def set_selected_device_id_path(_selected_device_id_path: str):
        """
        Set the current selected device virtual path.
        :param _selected_device_id_path: string with the current virtual path from the device that will be selected.
        """
        MtpChannel._selected_device_id_path = _selected_device_id_path


    @staticmethod
    def create_path_folder(output_path: str):
        """
            Create a folder in the device in the output path.
            :param output_path: string path of the folder.
        """
        ps_list = ", ".join(f"'{p}'" for p in output_path.split("/") if p)

        ps_script = f"""
                    & {{
                        $output_path = @({ps_list})

                        $shell = New-Object -ComObject Shell.Application
                        $computer = $shell.Namespace(17)
                        $device = $computer.Items() | Where-Object {{ $_.Path -eq "{MtpChannel._selected_device_id_path}" }}
                        $folder = $device.GetFolder
                        $not_found = $false
                        for ($i = 0; $i -lt $output_path.Count -and -not $not_found; $i++)
                        {{
                            $item = $folder.Items() | Where-Object {{ $_.Name -eq $output_path[$i] }}
                            if ($item -eq $null -and $i -lt 1)
                            {{
                                $not_found = $true
                            }}
                            else
                            {{
                                if($item -eq $null)
                                {{
                                    $folder_name = $output_path[$i]
                                    Write-Output "Creating new folder $folder_name"
                                    $folder.NewFolder($output_path[$i])
                                    $item = $folder.Items() | Where-Object {{ $_.Name -eq $output_path[$i] }}
                                }}
                                $folder = $item.GetFolder
                            }}
                        }}
                    }}
                    """

        result = MtpChannel.get_result_script(ps_script)
        logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()
        if result.strip():
            logger.info(result.strip())


    @staticmethod
    def push_file(file_path: Path, output_path: str, temporal_copy_path: str):
        """
            Copy a file from the PC to the device.
            :param file_path: Path of the file to copy.
            :param output_path: Path of the destination folder.
        """

        logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

        ps_list = ", ".join(f"'{p}'" for p in output_path.split("/") if p)

        out_path = Path(temporal_copy_path) / file_path.name

        os.makedirs(temporal_copy_path, exist_ok=True)

        for item in out_path.parent.iterdir():
            if item.is_file() or item.is_symlink():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


        shutil.copy(file_path, out_path)
        ps_script = f"""
                    & {{
                        $file_name = \"{str(file_path.name)}\"
                        $output_path = @({ps_list})
                        $temporal_input_path = \"{str(out_path.parent)}\"
                        $input_path = \"{str(file_path.parent)}\"
                        $shell = New-Object -ComObject Shell.Application
                        $computer = $shell.Namespace(17)
                        $device = $computer.Items() | Where-Object {{ $_.Path -eq "{MtpChannel._selected_device_id_path}" }}
                        $folder = $device.GetFolder
                        for ($i = 0; $i -lt $output_path.Count -and -not $not_found; $i++)
                        {{
                            $item = $folder.Items() | Where-Object {{ $_.Name -eq $output_path[$i] }}
                            if ($item -eq $null)
                            {{
                                $not_found = $true
                            }}
                            else
                            {{
                               $folder = $item.GetFolder
                            }}
                        }}
                        if ($not_found -ne $true)
                        {{
                            $sourceFolder = $shell.Namespace($temporal_input_path)
                            $item = $sourceFolder.ParseName($file_name) 
                            $existing = $folder.Items() | Where-Object {{ $_.Name -eq $file_name }}
                            if ($existing -ne $null) {{
                                $existing.InvokeVerb("delete")
                            }}
                            $timeout = 12
                            $elapsed = 0
                            $removed = $false
                            $copied = $null
                            $timeout_copy = 30
                            $elapsed_copy = 0
                            while ($elapsed -lt $timeout -and -not $removed) {{
                                $existing = $folder.Items() | Where-Object {{ $_.Name -eq $file_name }}
                                if ($existing -eq $null) {{
                                    $removed = $true
                                    $folder.CopyHere($item)

                                    while ($elapsed_copy -lt $timeout_copy) {{
                                        Start-Sleep -Seconds 1
                                        $elapsed_copy++
                                        $copied = $folder.Items() | Where-Object {{ $_.Name -eq $file_name }}
                                        if ($copied -ne $null) {{
                                            Write-Output  "Copying file $input_path\\$file_name."
                                            break
                                        }}
                                    }}
                                    break
                                }}
                                Start-Sleep -Seconds 1
                                $elapsed++
                            }}    
                            if ($elapsed_copy -ge $timeout_copy) {{
                                Write-Output "File copy timed out $file_name"
                            }}
                            else
                            {{
                                if($copied -eq $null -and $removed) {{
                                    Write-Output "Something went wrong while copying $file_name."
                                }} 
                                if($removed -eq $false){{
                                    Write-Output "File $file_name was not replaced."
                                }}   
                            }}
                        }}
                        else
                        {{
                            Write-Output "Device not found"
                        }}
                    }}
                    """

        logger.info(MtpChannel.get_result_script(ps_script).strip().rstrip("\n"))

        os.remove(out_path)

    @staticmethod
    def check_directory_exists(directory: str) -> bool:
        """
            Check if a directory exists.
            :param directory: Directory to check.
            :return: True if exists, False otherwise.
        """
        ps_list = ", ".join(f"'{p}'" for p in directory.split("/") if p)

        ps_script = f"""
                            & {{
                                $input_path = @({ps_list})
                                $shell = New-Object -ComObject Shell.Application
                                $computer = $shell.Namespace(17)
                                $not_found = $false
                                $device = $computer.Items() | Where-Object {{ $_.Path -eq "{MtpChannel._selected_device_id_path}" }}
                                $folder = $device.GetFolder
                                for ($i = 0; $i -lt $input_path.Count -and -not $not_found; $i++)
                                {{
                                    $item = $folder.Items() | Where-Object {{ $_.Name -eq $input_path[$i] }}
                                    if ($item -eq $null)
                                    {{
                                        $not_found = $true
                                    }}
                                    else
                                    {{
                                       $folder = $item.GetFolder
                                    }}
                                }}
                                
                                Write-Output $not_found
                                
                            }}
                            """

        result = MtpChannel.get_result_script(ps_script).strip().lower()
        if not result:
            return False

        return result in ("false", "0")



    @staticmethod
    def pull_file(file_path: Path, output_path: str):
        """
        Pull a file from the mobile to the PC.
        :param file_path: Path of the file to copy.
        :param output_path: Path of the destination folder
        """

        #Delete file if exists
        #$existing = $destFolder.Items() | Where - Object
        #{{ $_.Name - eq $file_name}}
        #if ($existing -ne $null) {{
        #    $existing.InvokeVerb("delete")
        #}}

        ps_list = ", ".join(f"'{p}'" for p in file_path.parent.as_posix().split("/") if p)
        ps_script = f"""
                    & {{
                        $file_name = \"{file_path.name}\"
                        $output_path = \"{str(Path(output_path))}\"
                        $input_path = @({ps_list})
                        $input_full_path = \"{str(file_path.parent)}\"                      
                        $shell = New-Object -ComObject Shell.Application
                        $computer = $shell.Namespace(17)
                        $device = $computer.Items() | Where-Object {{ $_.Path -eq "{MtpChannel._selected_device_id_path}" }}
                        $folder = $device.GetFolder
                        for ($i = 0; $i -lt $input_path.Count -and -not $not_found; $i++)
                        {{
                            $item = $folder.Items() | Where-Object {{ $_.Name -eq $input_path[$i] }}
                            if ($item -eq $null)
                            {{
                                $not_found = $true
                            }}
                            else
                            {{
                               $folder = $item.GetFolder
                            }}
                        }}
                        if ($not_found -ne $true)
                        {{
                            New-Item -ItemType Directory -Force -Path $output_path | Out-Null
                            $destFolder = $shell.Namespace($output_path)
                            $item = $folder.Items() | Where-Object {{ $_.Name -eq $file_name }}

                            $destFolder.CopyHere($item)
                            Write-Output "Copying file $input_full_path\\$file_name."
                        }}
                    }}
                    """

        logger = QgisLoggerHandler(
            QGIS_PLUGIN_NAME,
            level=logging.INFO
        ).get_logger()

        logger.info(MtpChannel.get_result_script(ps_script).strip().rstrip("\n"))


    @staticmethod
    def get_directories_list(search_path: str) -> list[Path]:
        """
        Get the list of directories recursively found in the search_path path and returns it as a list. It uses
        _selected_device_id_path as id of the device from where the list of directories will be returned.
        :param search_path: string path of the base directory from where the search will be performed.
        :return: list of directories found at search_path on the device with virtual_path = _selected_device_id_path.
        """
        ps_list = ", ".join(f"'{p}'" for p in search_path.split("/") if p)
        ps_script = f"""
                        & {{
                            function Get-File-List
                            {{
                            param($current_path, $folder_of_current_path)
                                $items = $folder.Items()
                                if ($item -eq $null)
                                {{
                                    return $current_list
                                }}

                                foreach ($item in $folder_of_current_path.Items())
                                 {{
                                    if ($item.IsFolder)
                                    {{
                                        $new_folder = $item.GetFolder
                                        $new_current_path = $current_path + "/" + $item.Name
                                        Write-Output $new_current_path
                                        $current_list = Get-File-List -start_path $start_path -current_path $new_current_path -folder_of_current_path $new_folder
                                    }}
                                }}
                                return $current_list
                            }}
                            
                            $path_list = @({ps_list})
                            $shell = New-Object -ComObject Shell.Application
                            $computer = $shell.Namespace(17)
                            $device = $computer.Items() | Where-Object {{ $_.Path -eq "{MtpChannel._selected_device_id_path}" }}
                            $folder = $device.GetFolder
                            $is_file = $false
                            $not_found = $false
                            if ($device -ne $null){{
                                for ($i = 0; $i -lt $path_list.Count -and -not $not_found; $i++){{
                                    $item = $folder.Items() | Where-Object {{ $_.Name -eq $path_list[$i] }}
                                    if ($item -eq $null){{
                                        $not_found = $true
                                    }}
                                    else {{
                                        if ($item.IsFolder -eq $false){{
                                            $is_file = $true
                                        }}
                                        else
                                        {{
                                            $folder = $item.GetFolder
                                        }}
                                    }}
                                }}
                                if ($not_found -ne $true -and $is_file -ne $true){{
                                    $list = Get-File-List -current_path "{search_path}" -folder_of_current_path $folder
                                    $list | ForEach-Object {{ $_ }}
                                }}
                            }}
                            else
                            {{
                                Write-Output "Device not found"
                            }}
                        }}
                        """

        result = MtpChannel.get_result_script(ps_script).strip()
        if not result:
            return []

        directory_list = [Path(line) for line in result.splitlines() if line.strip()]

        return directory_list




    @staticmethod
    def get_file_list(search_path: str) -> list[Path]:
        """
        Get the list of files recursively found in the search_path path and returns it as a dictionary. It uses
        _selected_device_id_path as id of the device from where the list of directories will be returned.
        :param search_path: string path of the base directory from where the search will be performed.
        :return: dictionary with directories and files found at search_path on the device with virtual_path = _selected_device_id_path.
        """

        ps_list = ", ".join(f"'{p}'" for p in search_path.split("/") if p)
        ps_script = f"""
                    & {{
                        function Get-File-List
                            {{
                            param($current_path, $folder_of_current_path)
                                $items = $folder.Items()
                                if ($item -eq $null)
                                {{
                                    return $current_list
                                }}

                                foreach ($item in $folder_of_current_path.Items())
                                 {{
                                    if ($item.IsFolder)
                                    {{
                                        $new_folder = $item.GetFolder
                                        $new_current_path = $current_path + "/" + $item.Name
                                        $current_list = Get-File-List -start_path $start_path -current_path $new_current_path -folder_of_current_path $new_folder
                                    }}
                                    else
                                    {{
                                        $new_path = $current_path + "/" + $item.Name
                                        Write-Output $new_path
                                    }}
                                }}
                                return $current_list
                            }}
                        $path_list = @({ps_list})
                        $shell = New-Object -ComObject Shell.Application
                        $computer = $shell.Namespace(17)
                        $device = $computer.Items() | Where-Object {{ $_.Path -eq "{MtpChannel._selected_device_id_path}" }}
                        $folder = $device.GetFolder
                        $is_file = $false
                        $not_found = $false
                        if ($device -ne $null){{
                            for ($i = 0; $i -lt $path_list.Count -and -not $not_found; $i++){{
                                $item = $folder.Items() | Where-Object {{ $_.Name -eq $path_list[$i] }}
                                if ($item -eq $null){{
                                    $not_found = $true
                                }}
                                else {{
                                    if ($item.IsFolder -eq $false){{
                                        $is_file = $true
                                    }}
                                    else
                                    {{
                                        $folder = $item.GetFolder
                                    }}
                                }}
                            }}
                            if ($not_found -ne $true -and  $is_file -ne $true){{
                                $list = Get-File-List -current_path "{search_path}" -folder_of_current_path $folder
                                $list | ForEach-Object {{ $_ }}

                            }}
                            else
                            {{
                                if($is_file)
                                {{
                                    $list = @()
                                    $root_path = ""
                                    for ($i = 0; $i -lt $path_list.Count -and -not $not_found; $i++){{
                                        if (($i+1) -eq $path_list.Count){{
                                            $list = @($root_path + "/" + $path_list[$i])
                                        }}
                                        else
                                        {{
                                            $root_path += "/" + $path_list[$i]
                                        }}
                                    }}
                                    $list | ForEach-Object {{ $_ }}
                                }}
                            }}
                        }}
                    }}
                    """

        result = MtpChannel.get_result_script(ps_script).strip()
        if not result:
            return []

        return [Path(line) for line in result.splitlines() if line.strip()]



    @staticmethod
    def get_storages(device_path: str) -> list:
        """
        Returns the disks found at the start of a connected device.
        :param device_path: string with the device path used to identify the connected device.
        :return: list of the storages found at the root of the device. (From Windows)
        """
        ps_script = f"""
                    & {{
                        $shell = New-Object -ComObject Shell.Application
                        $computer = $shell.Namespace(17)
                        $device = $computer.Items() | Where-Object {{ $_.Path -eq "{device_path}" }}
                        if ($device -ne $null) {{
                            $folder = $device.GetFolder
                            $items = $folder.Items()
                            $items | ConvertTo-Json
                        }}
                    }}
                    """

        result = MtpChannel.get_result_script(ps_script).strip()
        if not result:
            return []

        storages = json.loads(result)


        names = []
        if isinstance(storages, dict):
            names.append("/"+storages["Name"])
        else:
            for item in storages:
                names.append("/"+item["Name"])

        return names



    @staticmethod
    def get_devices() -> list:
        """
            Returns the list of connected devices found.
            :return: list of connected devices found.
        """

        ps_script = r"""
            & {
                $shell = New-Object -ComObject Shell.Application
                $myPC = $shell.Namespace(17)  # "This PC"
                
                $devices = @()
                
                foreach ($item in $myPC.Items()) {
                    if (-not $item.IsFileSystem) {
                        $parsing = $item.Path
                        if ($parsing -like "::*") {    
                            $device = @{
                                Name       = $item.Name
                                Type       = $item.Type
                                Path       = $item.Path
                                IsFileSystem = $item.IsFileSystem
                                ModifyDate = $item.ModifyDate
                                Size       = $item.Size
                            }
                
                            $devices += $device
                        }
                    }
                }
                # Convertir la lista de dispositivos a JSON
                $devices | ConvertTo-Json -Depth 5
            }
            """

        result_exec = MtpChannel.get_result_script(ps_script).strip()
        if not result_exec:
            return []
        devices = json.loads(result_exec)

        # PowerShell returns an object if there's only one result
        if isinstance(devices, dict):
            devices = [devices]


        return devices

    @staticmethod
    def get_information_about_device(device_id : str = None) -> dict:
        """
        Get more information about a connected device.
        :param device_id: id of the connected device that will be searched for more information.
        :return: information about the connected device.
        """

        ps_script = """
        Get-PnpDevice -Class WPD |
        Where-Object { $_.Status -eq 'OK' -and $_.Present -eq $true } |
        Select-Object FriendlyName, Caption, Description, Name, Manufacturer, InstanceId |
        ConvertTo-Json
        """

        result = MtpChannel.get_result_script(ps_script)

        if not result.strip():
            return {}

        if not device_id:
            return json.loads(result)
        else:
            result_json = json.loads(result)
            device_found_data = {}
            if isinstance(result_json, dict):
                result_json = [result_json]
            for device_info in result_json:
                if "InstanceId" in device_info:
                    device_id_found = device_info["InstanceId"].split("\\")
                    if device_id_found and device_id_found[-1].lower() == device_id.lower():
                        device_found_data = device_info
                        break
            return device_found_data


    @staticmethod
    def get_result_script(ps_script: str, get_full_result: bool = False, checking_availability: bool = False):
        """
        Execute the powershell script and returns the result
        :param ps_script: powershell script that will be executed.
        :param get_full_result: get full result of the script. If true it returns the CompletedProcess object, if false returns the stdout.
        :param checking_availability: Prevents exceptions from being thrown if an error has occurred in powershell operations, so that the launcher handles the response.
        :return: CompletedProcess or str with the result of the execution.
        """
        if MtpChannel._powershell_path is None:
            MtpChannel._powershell_path = os.path.join(os.environ["SystemRoot"], "System32", "WindowsPowerShell", "v1.0", "powershell.exe")

        result = subprocess.run(
            [MtpChannel._powershell_path, "-ExecutionPolicy", "Bypass", "-NoProfile", "-Command", ps_script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        if not checking_availability :
            if result.returncode != 0 or result.stderr.strip() != "":
                raise subprocess.CalledProcessError(
                    result.returncode,
                    result.args,
                    output=result.stdout,
                    stderr= "Powershell error: {error}".format(error = result.stderr)
                )

        if get_full_result:
            return result
        else:
            return result.stdout