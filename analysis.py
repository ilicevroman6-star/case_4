import os
from typing import Dict, Any, List, Tuple, Optional, Set
from collections import defaultdict

import utils
import navigation

# Вспомогательные функции.

def _get_all_files(
        path: str,
        visited: Optional[Set[str]] = None,
        max_depth: int = 64,
        depth: int = 0,
) -> Tuple[List[Tuple[str, Dict[str, Any]]], List[Tuple[str, str]]]:
    """
    Recursively walks through a directory to collect all files.
    :param path: The absolute path to the starting directory.
    :param visited: A set of already visited paths to prevent infinite loops
                    (due to symlinks or junction points).
    :param max_depth: The maximum recursion depth allowed.
    :param depth: The current recursion depth (used internally).
    :return: A tuple containing two lists:
            1. A flat list of tuples (file_path, file_info_dict).
            2. A list of tuples (path, error_message) for inaccessible path.
    """

    files: List[Tuple[str, Dict[str, Any]]] = []
    errors: List[Tuple[str, str]] = []

    if visited is None:
        visited = set()

    try:
        norm = os.path.normcase(os.path.abspath(path))
    except OSError:
        errors.append((path, "Не удалось нормализовать путь"))

    norm = path
    if norm in visited:
        return files, errors
    visited.add(norm)

    if depth > max_depth:
        errors.append((path, f"Превышена максимальная глубина ({max_depth})"))
        return files, errors

    if not os.path.isdir(path):
        errors.append((path, "Не является каталогом"))
        return files, errors

    ok, items = navigation.list_directory(path)
    if not ok:
        errors.append((path, "Не удалось прочитать каталог"))
        return files, errors

    for item in items:
        name = item.get("name", "")
        if not name:
            continue
        full = os.path.join(path, name)
        itype = item.get("type", "file")

        if itype == "folder":
            sub_files, sub_errors = _get_all_files(full, visited, max_depth, depth + 1)
            files.extend(sub_files)
            errors.extend(sub_errors)
        else:
            files.append((full, item))

    return files, errors


def _is_system_file(full_path: str) -> bool:
    """
    Checks if a file has the Windows FILE_ATTRIBUTE_SYSTEM (0x4) attribute.

    :param full_path: The absolute path to the file to check.
    :return: True if the file has the system attribute, False otherwise
             (or if the OS is not Windows).
    """
    try:
        attrs = os.stat(full_path).st_file_attributes  # Windows-only
        return bool(attrs & 0x4)
    except (AttributeError, OSError):
        return False


def _is_readonly(full_path: str) -> bool:
    """
Checks if a file is write-protected (read-only).

    :param full_path: The absolute path to the file to check.
    :return: True if the file is read-only (cannot be written to), False otherwise.
    """
    try:
        return not os.access(full_path, os.W_OK)
    except OSError:
        return False

# Публичные функции.

def count_files(path: str) -> Tuple[bool, int]:
    """
    Recursively counts the total number of files in a Windows directory.

    :param path: The absolute path to the directory to analyze.
    :return: A tuple of (success_status, file_count).
             Returns (True, N) if successful, or (False, 0) if the directory does not exist.
    """
    if not os.path.isdir(path):
        return False, 0

    files, _errors = _get_all_files(path)
    return True, len(files)


def count_bytes(path: str) -> Tuple[bool, int]:
    """
    Recursively counts the total number of bytes in a Windows directory.
    :param path: The absolute path to the directory to analyze.
    :return: A tuple of (success_status, total_bytes).
             Returns (True, N) if successful, or (False, 0) if the directory does not exist.
    """
    if not os.path.isdir(path):
        return False, 0

    files, _errors = _get_all_files(path)
    total = 0
    for _full, info in files:
        size = info.get("size")
        if isinstance(size, int) and size > 0:
            total += size
    return True, total


def analyze_windows_file_types(path: str) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
    """
Analyzes file types by extension and calculates the count and total size for each.

    :param path: The absolute path to the directory to analyze.
    :return: A tuple of (success_status, stats_dict).
             Returns (True, dict) if successful, or (False, {}) if the directory does not exist.
             The dict format is: {".ext": {"count": int, "total_size": int}, ...}.
    """
    if not os.path.isdir(path):
        return False, {}

    files, _errors = _get_all_files(path)
    stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "total_size": 0})

    for full, info in files:
        ext = os.path.splitext(full)[1].lower() or "<no_ext>"
        stats[ext]["count"] += 1
        size = info.get("size")
        if isinstance(size, int) and size > 0:
            stats[ext]["total_size"] += size

    return True, dict(stats)


def get_windows_file_attributes_stats(path: str) -> Dict[str, int]:
    """
    Recursively counts Windows file attributes: hidden, system, and read-only.

    :param path: The absolute path to the directory to analyze.
    :return: A dictionary with counts for each attribute:
             {"hidden": int, "system": int, "readonly": int}.
             Returns zeros if the directory does not exist.
    """
    stats = {"hidden": 0, "system": 0, "readonly": 0}

    if not os.path.isdir(path):
        return stats

    files, _errors = _get_all_files(path)
    for full, info in files:
        # hidden: сначала берём из list_directory, если нет — через utils
        if info.get("hidden") or utils.is_hidden_windows_file(full):
            stats["hidden"] += 1
        if _is_system_file(full):
            stats["system"] += 1
        if _is_readonly(full):
            stats["readonly"] += 1

    return stats


def show_windows_directory_stats(path: str) -> bool:
    """
    Prints a comprehensive summary report of a Windows directory.

    :param path: The absolute path to the directory to analyze and display.
    :return: True if the report was successfully generated, False if the directory
             does not exist or cannot be accessed.
    """
    print(f"\n=== Статистика: {path} ===\n")

    if not os.path.isdir(path):
        print("[!] Каталог не существует или недоступен.")
        return False

    # Количество файлов.
    ok_files, total_files = count_files(path)
    if not ok_files:
        print("[!] Не удалось прочитать каталог.")
        return False

    # Общий размер.
    ok_bytes, total_bytes = count_bytes(path)

    # Считаем подкаталоги верхнего уровня.
    dirs_count = 0
    ok_dir, items = navigation.list_directory(path)
    if ok_dir:
        dirs_count = sum(1 for i in items if i.get("type") == "folder")

    print(f"Файлов:        {total_files}")
    print(f"Подкаталогов:  {dirs_count} (верхний уровень)")
    print(f"Общий размер:  {utils.format_size(total_bytes) if ok_bytes else 'н/д'}")

    # Типы файлов.
    ok_types, types = analyze_windows_file_types(path)
    if ok_types and types:
        print("\n--- Топ расширений по размеру ---")
        top = sorted(types.items(), key=lambda kv: kv[1]["total_size"], reverse=True)[:10]
        for ext, s in top:
            print(f"  {ext:<10} {s['count']:>6} шт.  {utils.format_size(s['total_size']):>10}")

    # Атрибуты.
    attrs = get_windows_file_attributes_stats(path)
    print("\n--- Атрибуты ---")
    print(f"  Скрытых:       {attrs['hidden']}")
    print(f"  Системных:     {attrs['system']}")
    print(f"  Только чтения: {attrs['readonly']}")

    # Крупнейшие файлы.
    files, errors = _get_all_files(path)
    big = sorted(
        [(f, i) for f, i in files if isinstance(i.get("size"), int) and i["size"] > 0],
        key=lambda x: x[1]["size"],
        reverse=True,
    )[:10]
    if big:
        print("\n--- Крупнейшие файлы ---")
        for full, info in big:
            print(f"  {utils.format_size(info['size']):>10}  {full}")

    # Ошибки доступа.
    if errors:
        print(f"\n[!] Пропущено из-за ошибок доступа: {len(errors)}")

    return True


# Тест (запускать только этот файл)

if __name__ == "__main__":
    # Он создает временную папку, кладет туда файлы и проверяет все 5 функций.

    import tempfile
    import shutil

    print("Создаем временную папку для теста...")
    tmp = tempfile.mkdtemp(prefix="fa_test_")

    try:
        os.makedirs(os.path.join(tmp, "sub", "deep"))

        with open(os.path.join(tmp, "a.txt"), "w") as f:
            f.write("x" * 100)
        with open(os.path.join(tmp, "b.pdf"), "wb") as f:
            f.write(b"\0" * 5000)
        with open(os.path.join(tmp, "sub", "c.txt"), "w") as f:
            f.write("y" * 200)
        with open(os.path.join(tmp, "sub", "deep", "d.exe"), "wb") as f:
            f.write(b"\0" * 70000)

        print("\n--- 1. count_files ---")
        print(count_files(tmp))  # (True, 4)

        print("\n--- 2. count_bytes ---")
        print(count_bytes(tmp))  #  (True, 75300)

        print("\n--- 3. analyze_windows_file_types ---")
        ok, types = analyze_windows_file_types(tmp)
        print(ok, types)

        print("\n--- 4. get_windows_file_attributes_stats ---")
        print(get_windows_file_attributes_stats(tmp))

        print("\n--- 5. show_windows_directory_stats ---")
        show_windows_directory_stats(tmp)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        print("\nВременная папка удалена. Тест завершен.")
