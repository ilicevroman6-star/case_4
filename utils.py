import os
import platform
from pathlib import Path
from typing import Union, List, Tuple, Dict, Any
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
    if attributes == -1:
        return False

    return attributes & 2 != 0

MAX_DEPTH = 50

def validate_windows_path_recursive(path: Pathstring, depth: int = 0, visited: set = None) -> Tuple[bool, List[str]]:
    """
    Recursive check of a path and all its parent directories in Windows.
    :param path: current path
    :param depth: depth of recursion
    :param visited: if this path was visited already
    :return: (validity, list of problematic sections of the route)
    """
    if visited is None:
        visited = set()

    if depth > MAX_DEPTH:
        return False, ["There are too many nested folders in the path"]

    path_str = str(path)

    try:
        real_path = os.path.realpath(path_str)
    except OSError:
        real_path = os.path.abspath(path_str)

    if real_path in visited:
        return True, []

    visited.add(real_path)

    bad_parts: List[str] = []

    current_folder = os.path.basename(path_str.rstrip("\\/"))

    if current_folder == "":
        return True, []

    is_valid, error_message = validate_windows_path(current_folder)

    if not is_valid:
        current_folder = os.path.basename(path_str) or path_str
        bad_parts.append(f"{current_folder}: {error_message}")

    parent_path = get_parent_path(path_str)
    if parent_path != path_str:
        parent_valid, parent_bad_parts = validate_windows_path_recursive(parent_path, depth + 1, visited)
        bad_parts.extend(parent_bad_parts)

    if len(bad_parts) > 0:
        return False, bad_parts

    return True, []

def collect_windows_metadata_recursive(path: Pathstring, max_depth: int = 10,
                                       depth: int = 0, visited: set = None) -> Dict[str, Any]:
    """
    Recursive collection of Windows file system metadata
    :param visited: if this path was visited already
    :param depth: current depth
    :param path: current path
    :param max_depth: maximum depth of recursion
    :return: dictionary with metadata
    """

    if visited is None:
        visited = set()

    path_str = str(path)

    try:
        real_path = os.path.realpath(path_str)
    except OSError:
        real_path = os.path.abspath(path_str)

    if real_path in visited:
        return None

    visited.add(real_path)


    if depth > max_depth:
        return None

    if os.path.isfile(path_str):
        size_bytes = os.path.getsize(path_str)
        extension = os.path.splitext(path_str)[1].lower()

        if extension == "":
            print('without extension')

        return {
            "name": os.path.basename(path_str),
            "path": path_str,
            "type": "file",
            "depth": depth,
            "hidden": is_hidden_windows_file(path_str),
            "extension": extension,
            "size_bytes": size_bytes,
            "size": format_size(size_bytes)
        }

    elif os.path.isdir(path_str):
        folder_metadata = {
            "name": os.path.basename(path_str) or path_str,
            "path": path_str,
            "type": "folder",
            "depth": depth,
            "hidden": is_hidden_windows_file(path_str),
            "files_count": 0,
            "folders_count": 0,
            "hidden_count": 0,
            "total_size_bytes": 0,
            "total_size": "0 B",
            "extensions": {},
            "children": []
        }

        items = safe_windows_listdir(path_str)

        for item in items:
            item_path = os.path.join(path_str, item)

            child_info = collect_windows_metadata_recursive(item_path, max_depth, depth + 1, visited)

            if child_info is None:
                continue

            folder_metadata["children"].append(child_info)

            if child_info["type"] == "file":
                folder_metadata["files_count"] += 1
                folder_metadata["total_size_bytes"] += child_info["size_bytes"]

                extension = child_info["extension"]
                folder_metadata["extensions"][extension] = folder_metadata["extensions"].get(extension, 0) + 1

            else:
                folder_metadata["files_count"] += child_info["files_count"]
                folder_metadata["folders_count"] += 1 + child_info["folders_count"]
                folder_metadata["hidden_count"] += child_info["hidden_count"]
                folder_metadata["total_size_bytes"] += child_info["total_size_bytes"]

                for extension, count in child_info["extensions"].items():
                    folder_metadata["extensions"][extension] = folder_metadata["extensions"].get(extension, 0) + 1

            if child_info["hidden"]:
                folder_metadata["hidden_count"] += 1
        folder_metadata["total_size"] = format_size(folder_metadata["total_size_bytes"])

    return folder_metadata

def resolve_long_paths_recursive(path: Pathstring, prefix: str = "\\\\?\\:", depth: int = 0) -> str:
    """
    Recursive conversion of Windows long paths with UNC support
    :param path: path to check
    :param prefix: if long of path > 260, add it
    :return:
    """

    if depth > MAX_DEPTH:
        raise RecursionError(f"The maximum depth {MAX_DEPTH} has been exceeded")

    if not is_windows_os():
        return str(path)

    full_path = os.path.abspath(str(path))

    if full_path.startswith(prefix):
        return full_path

    parent = get_parent_path(full_path)

    if parent == full_path:
        resolved = full_path
    else:
        resolved_parent = resolve_long_paths_recursive(parent, prefix, depth + 1)
        resolved = resolved_parent.rstrip("\\") + "\\" + os.path.basename(full_path)

    if len(resolved) < 260 or resolved.startswith(prefix):
        return resolved

    if resolved.startswith("\\\\"):
        return "\\\\?\\UNC\\" + resolved[2:]

    return prefix + resolved




#Example
#print(validate_windows_path_recursive(r'C:\Users\User\OneDrive\Рабочий стол\Программы\OBS-Studio-26.1.1-Full-Installer-x64 (1).exe'))
#file_path = Path(r'C:\Users\User\OneDrive\Рабочий стол\Программы\OBS-Studio-26.1.1-Full-Installer-x64 (1).exe')
#size_in_bytes = file_path.stat().st_size
#print("Размер в байтах:", size_in_bytes)
#print("Размер файла:", format_size(size_in_bytes))
#print(get_parent_path(file_path))
#items = safe_windows_listdir(r'C:\Users\User\OneDrive\Рабочий стол\Программы')
#print(items)
#for item in items:
#   print(is_hidden_windows_file(r'C:\Users\User\OneDrive\Рабочий стол\Программы' + '\\' + item))
#print( collect_windows_metadata_recursive(r'C:\Users\User\OneDrive\Рабочий стол\Программы'))