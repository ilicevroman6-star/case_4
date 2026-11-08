import os
import platform
from pathlib import Path
from typing import Union, List, Tuple
import ctypes

Pathstring = Union[str, Path]

def is_windows_os() -> bool:
    """
    Function to check if OS is Windows
    :return: True, if OS is Windows, else False
    """
    return platform.system().lower() == "windows"

def validate_windows_path(path: Pathstring) -> Tuple[bool, str]:
    """
    Function to check if windows path is valid
    :param path: path to check
    :return: true if windows path is valid, false otherwise
    """
    path_str = str(path)
    if not path_str.strip():
        return False, "Path cannot be empty"

    if len(path_str) > 260:
        return False, "Path cannot be more than 260 characters"

    forbidden_chars = '|/<>"?*'

    for char in forbidden_chars:
        if char in path_str:
            return False, f"Char {char} is forbidden"

    path_without_drive = path_str

    if len(path_str) >= 2 and path_str[1] == ":":
        path_without_drive = path_str[2:]

    if ':' in path_without_drive:
        return False, "Char ':' can only be used after disk letter"

    return True, ""

def format_size(size_bytes: int) -> str:
    """
    Function to format the size of the file for Windows
    :param size_bytes: size of the file
    :return: formatted size
    """
    units = ["B", "KB", "MB", "GB", "TB"]
    size = size_bytes
    unit_index = 0

    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if units[unit_index] == "B":
        return f"{int(size)} {units[unit_index]}"

    return f"{size:.1f}{units[unit_index]}"

def get_parent_path(path: Pathstring) -> str:
    """
    Function to get the parent path of path
    :param path: original path
    :return: parent path
    """
    parent = os.path.dirname(path)

    if parent == "":
        return path

    return parent

def safe_windows_listdir(path: Pathstring) -> List[str]:
    """
    Function to safely list all catalog contents
    :param path: path to catalog
    :return: list of catalog contents
    """
    try:
        return os.listdir(path)

    except PermissionError:
        #windows did not grant access to the folder
        return []

    except FileNotFoundError:
        #such a folder does not exist
        return []

    except NotADirectoryError:
        #the path points to a file, not to a folder.
        return []

    except OSError:
        #another Windows error, for example, a path that is too long
        return []

def is_hidden_windows_file(path: Pathstring) -> bool:
    """
    Function that checks whether a file is hidden in Windows.
    :param path: path to check
    :return: True if file is hidden in Windows, else False
    """
    attributes = ctypes.windll.kernel32.GetFileAttributesW(str(path))
    print(attributes)
    if attributes == -1:
        return False

    return attributes & 2 != 0


#Example
'''
file_path = Path(r'C:\Users\User\OneDrive\Рабочий стол\Программы\OBS-Studio-26.1.1-Full-Installer-x64 (1).exe')
size_in_bytes = file_path.stat().st_size
print("Размер в байтах:", size_in_bytes)
print("Размер файла:", format_size(size_in_bytes))
print(get_parent_path(file_path))
items = safe_windows_listdir(r'C:\Users\User\OneDrive\Рабочий стол\Программы')
print(items)
for item in items:
    print(is_hidden_windows_file(r'C:\Users\User\OneDrive\Рабочий стол\Программы' + '\\' + item))
'''