import os
from datetime import datetime
from typing import List, Dict, Any, Tuple, Generator, Set, Optional
from pathlib import PureWindowsPath

from utils import (
    validate_windows_path,
    validate_windows_path_recursive,
    resolve_long_paths_recursive,
    safe_windows_listdir,
    is_hidden_windows_file,
    get_parent_path
)


def get_current_drive() -> str:
    """
    Extracts and returns the current Windows drive letter from the current working directory.
    """
    drive, _ = os.path.splitdrive(os.getcwd())
    return drive if drive else "C:"


def list_available_drives() -> List[str]:
    """
    Retrieves a list of all available and accessible logical drive letters on the Windows system.
    """
    drives = []
    for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive_path = f"{drive_letter}:\\"
        if os.path.exists(drive_path):
            drives.append(f"{drive_letter}:")
    return drives


def list_directory(path: str) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Safely reads the content of a Windows directory using Architect utilities.
    Gathers detailed metadata for each file and folder including size, visibility, and modification dates.
    """
    items = safe_windows_listdir(path)
    if not items and not os.path.exists(path):
        return False, []

    data = []
    for item in items:
        full_path = os.path.join(path, item)
        is_dir = os.path.isdir(full_path)

        try:
            stat_info = os.stat(full_path)
            size = stat_info.st_size
            mod_time = datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d')
        except OSError:
            size = 0
            mod_time = "0000-00-00"

        item_type = 'folder' if is_dir else 'file'
        hidden_status = is_hidden_windows_file(full_path) or item.startswith('.')

        data.append({
            'name': item,
            'type': item_type,
            'size': size,
            'modified': mod_time,
            'hidden': hidden_status
        })

    return True, data


def format_directory_output(items: List[Dict[str, Any]]) -> None:
    """
    Prints a structured and readable text representation of the directory contents.
    Differentiates files from folders and highlights system or hidden entities.
    """
    if not items:
        print("Directory is empty or inaccessible.")
        return

    print(f"{'Type':<10} | {'Name':<30} | {'Size (Bytes)':<15} | {'Modified':<12} | {'Status'}")
    print("-" * 80)

    for item in items:
        status_str = "Hidden" if item['hidden'] else "Normal"
        size_str = str(item['size']) if item['type'] == 'file' else "<DIR>"

        print(f"{item['type']:<10} | {item['name']:<30} | {size_str:<15} | {item['modified']:<12} | {status_str}")


def move_up(current_path: str) -> str:
    """
    Navigates to the parent directory using the Architect path utility.
    Validates the result to ensure it is a proper Windows path.
    """
    parent = get_parent_path(current_path)
    is_valid, _ = validate_windows_path(parent)
    return parent if is_valid else current_path


def move_down(current_path: str, target_dir: str) -> Tuple[bool, str]:
    """
    Attempts to navigate down into a specified subfolder.
    Verifies folder existence via safe listing and checks path validity before returning.
    """
    available_items = safe_windows_listdir(current_path)

    match_found = False
    for item in available_items:
        if item.lower() == target_dir.lower():
            if os.path.isdir(os.path.join(current_path, item)):
                target_dir = item
                match_found = True
                break

    if not match_found:
        return False, current_path

    new_path = os.path.join(current_path, target_dir)
    is_valid, _ = validate_windows_path(new_path)

    if is_valid and os.path.exists(new_path):
        return True, new_path

    return False, current_path


def get_windows_special_folders() -> Dict[str, str]:
    """
    Fetches the precise local paths of standard Windows special directories using system environment variables.
    """
    user_profile = os.environ.get("USERPROFILE", "C:\\Users\\Default")

    return {
        'Desktop': os.path.join(user_profile, 'Desktop'),
        'Documents': os.path.join(user_profile, 'Documents'),
        'Downloads': os.path.join(user_profile, 'Downloads')
    }


def build_windows_tree_recursive(
        path: str,
        depth: int = 0,
        max_depth: int = 5,
        visited: Optional[Set[str]] = None
) -> Dict[str, Any]:
    """
    Recursively builds a Windows directory tree integrated with Architect utilities.

    Prevents stack overflow using max_depth and tracks real paths in visited set
    to avoid infinite loops caused by Junction Points and Symlinks.
    """
    if visited is None:
        visited = set()

    resolved_path = resolve_long_paths_recursive(path)
    name = os.path.basename(resolved_path) if os.path.basename(resolved_path) else resolved_path

    node = {
        "name": name,
        "type": "directory",
        "children": []
    }

    if depth > max_depth:
        return node

    is_valid, _ = validate_windows_path_recursive(resolved_path, depth=depth)
    if not is_valid:
        return {**node, "children": [{"name": "[Invalid Path Section]", "type": "error"}]}

    try:
        canonical_path = os.path.realpath(resolved_path)
    except OSError:
        canonical_path = os.path.abspath(resolved_path)

    if canonical_path in visited:
        return {**node, "children": [{"name": "[Circular Link Detected]", "type": "shortcut"}]}

    visited.add(canonical_path)
    items = safe_windows_listdir(resolved_path)

    for item in items:
        if item.startswith("$") or item.lower() == "system volume information":
            continue

        item_full_path = os.path.join(resolved_path, item)

        if os.path.isdir(resolve_long_paths_recursive(item_full_path)):
            child_node = build_windows_tree_recursive(
                item_full_path,
                depth=depth + 1,
                max_depth=max_depth,
                visited=visited.copy()
            )
            node["children"].append(child_node)
        else:
            node["children"].append({
                "name": item,
                "type": "file"
            })

    return node


def recursive_path_explorer(
        start_path: str,
        history: Optional[List[str]] = None,
        visited: Optional[Set[str]] = None
) -> Generator[Tuple[str, List[str]], None, None]:
    """
    Recursive lazy generator for traversing Windows directories.
    Tracks path history stack simulating back/forward navigation efficiently.
    """
    if history is None:
        history = []
    if visited is None:
        visited = set()

    resolved_start = resolve_long_paths_recursive(start_path)

    try:
        canonical_path = os.path.realpath(resolved_start)
    except OSError:
        canonical_path = os.path.abspath(resolved_start)

    if canonical_path in visited:
        return

    visited.add(canonical_path)
    current_history = history + [resolved_start]

    yield resolved_start, current_history

    items = safe_windows_listdir(resolved_start)

    for item in items:
        if item.startswith("$") or item.lower() == "system volume information":
            continue

        item_full_path = os.path.join(resolved_start, item)

        if os.path.isdir(resolve_long_paths_recursive(item_full_path)):
            yield from recursive_path_explorer(
                item_full_path,
                history=current_history,
                visited=visited.copy()
            )


def analyze_windows_structure_recursive(
        path: str,
        pattern: str = "*",
        level: int = 0,
        visited: Optional[Set[str]] = None
) -> List[Tuple[int, str, str]]:
    """
    Recursively scans Windows directory trees, classifies elements by type,
    and filters results based on the provided search pattern without external libraries.
    """
    if visited is None:
        visited = set()

    results: List[Tuple[int, str, str]] = []
    resolved_path = resolve_long_paths_recursive(path)

    try:
        canonical_path = os.path.realpath(resolved_path)
    except OSError:
        canonical_path = os.path.abspath(resolved_path)

    if canonical_path in visited:
        return results

    visited.add(canonical_path)
    items = safe_windows_listdir(canonical_path)

    for item in items:
        if item.startswith("$") or item.lower() == "system volume information":
            continue

        item_full_path = os.path.join(canonical_path, item)
        resolved_item_path = resolve_long_paths_recursive(item_full_path)

        is_dir = os.path.isdir(resolved_item_path)
        is_hidden = is_hidden_windows_file(resolved_item_path) or item.startswith(".")

        if is_dir:
            item_type = "DIR_SYSTEM" if is_hidden else "DIR"
        else:
            item_type = "FILE_HIDDEN" if is_hidden else "FILE"

        if pattern == "*" or PureWindowsPath(item).match(pattern):
            results.append((level, item_type, item_full_path))

        if is_dir:
            sub_directory_results = analyze_windows_structure_recursive(
                item_full_path,
                pattern=pattern,
                level=level + 1,
                visited=visited.copy()
            )
            results.extend(sub_directory_results)

    return results
