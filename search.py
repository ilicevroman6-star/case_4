import os
import re
from typing import List, Dict, Any, Tuple
import utils
import navigation
import analysis

def find_files_windows(
    pattern: str,
    path: str,
    case_sensitive: bool = False
) -> List[str]:
    """
    Recursively searches for files matching a Windows wildcard pattern.

    :param pattern: The filename pattern to match (supports '*' and '?'
                    wildcards).
    :param path: The absolute path to the starting Windows directory.
    :param case_sensitive: Whether the search is case-sensitive.
                           Defaults to False.
    :return: A list of full file paths matching the specified pattern.
    """
    success_count, total_files = analysis.count_files(path)
    if not success_count or total_files == 0:
        return []

    escaped_pattern = re.escape(pattern)
    regex_pattern = escaped_pattern.replace(r"\*", ".*").replace(r"\?", ".")

    if not case_sensitive:
        regex_pattern = regex_pattern.lower()

    processed = [0]

    def search_recursive(current_path: str) -> List[str]:
        """Recursively collect file paths matching the regex pattern."""
        found = []
        success, items = navigation.list_directory(current_path)
        if not success:
            return found

        for item in items:
            full_path = os.path.join(current_path, item['name'])

            if item['type'] == 'folder':
                found.extend(search_recursive(full_path))
            else:
                processed[0] += 1

                percent = int((processed[0] / total_files) * 100)
                filled = int(20 * processed[0] // total_files)
                bar = "█" * filled + "-" * (20 - filled)
                print(
                    f"\rПрогресс: [{bar}] {percent}% "
                    f"({processed[0]}/{total_files})",
                    end=""
                )

                file_name = (
                    item['name'] if case_sensitive else item['name'].lower()
                )
                if re.fullmatch(regex_pattern, file_name):
                    found.append(full_path)

        return found

    return search_recursive(path)

def find_by_windows_extension(
    extensions: List[str],
    path: str
) -> List[str]:
    """
    Recursively searches for files matching a list of Windows extensions.

    :param extensions: A list of file extensions to search for
                       (e.g., ['.exe', 'msi', '.dll']).
    :param path: The absolute path to the starting Windows directory.
    :return: A list of full file paths matching the specified extensions.
    """
    if not extensions:
        return []

    success, stats = analysis.analyze_windows_file_types(path)
    if not success or not stats:
        return []

    valid_extensions = set()
    for ext in extensions:
        clean_ext = ext.lower()
        if not clean_ext.startswith("."):
            clean_ext = "." + clean_ext

        if clean_ext in stats and stats[clean_ext]["count"] > 0:
            valid_extensions.add(clean_ext)

    if not valid_extensions:
        return []

    def search_recursive(current_path: str) -> List[str]:
        """Recursively collect file paths with matching extensions."""
        found = []
        dir_success, items = navigation.list_directory(current_path)
        if not dir_success:
            return found

        for item in items:
            full_path = os.path.join(current_path, item["name"])

            if item["type"] == "folder":
                found.extend(search_recursive(full_path))
            else:
                file_ext = os.path.splitext(item["name"])[1].lower()
                if file_ext in valid_extensions:
                    found.append(full_path)

        return found

    return search_recursive(path)

def find_large_files_windows(
    min_size_mb: float,
    path: str
) -> List[Dict[str, Any]]:
    """
    Recursively searches for files exceeding a minimum size in megabytes.

    :param min_size_mb: The minimum file size threshold in megabytes.
    :param path: The absolute path to the starting Windows directory.
    :return: A list of dictionaries containing file details:
             [{'path': str, 'size_mb': float, 'type': str}, ...].
    """
    min_bytes = min_size_mb * 1024 * 1024
    success, total_bytes = analysis.count_bytes(path)
    if not success or total_bytes < min_bytes:
        return []

    def search_recursive(current_path: str) -> List[Dict[str, Any]]:
        """Recursively collect metadata for files meeting the size limit."""
        found = []
        dir_success, items = navigation.list_directory(current_path)
        if not dir_success:
            return found

        for item in items:
            full_path = os.path.join(current_path, item["name"])

            if item["type"] == "folder":
                found.extend(search_recursive(full_path))
            else:
                size_bytes = item.get("size", 0)
                if size_bytes >= min_bytes:
                    size_mb = round(size_bytes / (1024 * 1024), 2)
                    file_ext = (
                            os.path.splitext(item["name"])[1].lower()
                            or "<no_ext>"
                    )
                    found.append({
                        "path": full_path,
                        "size_mb": size_mb,
                        "type": file_ext
                    })

        return found

    return search_recursive(path)

def find_windows_system_files(path: str) -> List[str]:
    """
    Recursively searches for Windows system files (.exe, .dll, .sys).

    Checks system directories (such as Windows, System32, SysWOW64) within
    the given path while excluding standard user special folders.

    :param path: The absolute path to the directory to scan.
    :return: A list of full paths to detected Windows system files.
    """
    if not os.path.isdir(path):
        return []

    system_extensions = {".exe", ".dll", ".sys"}
    system_dir_names = {"windows", "system32", "syswow64", "drivers"}

    special_folders = navigation.get_windows_special_folders()
    user_dirs = {
        os.path.normcase(os.path.abspath(folder))
        for folder in special_folders.values()
    }

    normalized_root = os.path.normcase(os.path.abspath(path))
    if normalized_root in user_dirs:
        return []

    def is_system_location(dir_path: str) -> bool:
        """Check if a directory path belongs to a Windows system folder."""
        parts = os.path.normcase(os.path.abspath(dir_path)).split(os.sep)
        return any(part in system_dir_names for part in parts)

    def search_recursive(current_path: str) -> List[str]:
        """Recursively collect Windows system files from system folders."""
        found = []
        norm_current = os.path.normcase(os.path.abspath(current_path))
        if norm_current in user_dirs:
            return found

        success, items = navigation.list_directory(current_path)
        if not success:
            return found

        in_system_dir = is_system_location(current_path)

        for item in items:
            full_path = os.path.join(current_path, item["name"])

            if item["type"] == "folder":
                found.extend(search_recursive(full_path))
            elif in_system_dir:
                file_ext = os.path.splitext(item["name"])[1].lower()
                if file_ext in system_extensions:
                    found.append(full_path)

        return found

    return search_recursive(path)

def search_menu_handler(current_path: str) -> bool:
    """
    Interactive search menu handler for Windows directories.

    :param current_path: The directory path where the search is performed.
    :return: True if the user wants to continue searching, False to exit.
    """
    print(f"\n=== Меню поиска (Текущая папка: {current_path}) ===")

    ok_files, total_files = analysis.count_files(current_path)
    ok_bytes, total_bytes = analysis.count_bytes(current_path)
    if ok_files and ok_bytes:
        total_mb = round(total_bytes / (1024 * 1024), 2)
        print(f"Всего в каталоге: {total_files} файлов ({total_mb} МБ)")

    print("1. Поиск по шаблону (*, ?)")
    print("2. Поиск по расширениям (.exe, .txt и др.)")
    print("3. Поиск крупных файлов (по размеру в МБ)")
    print("4. Поиск системных файлов Windows")
    print("0. Вернуться в главное меню")

    choice = input("Выберите пункт меню: ").strip()

    match choice:
        case "1":
            pattern = input("Введите шаблон (например, *.txt): ").strip()
            case_input = input("Учитывать регистр? (y/n): ").strip().lower()
            results = find_files_windows(
                pattern, current_path, case_input == "y"
            )
            format_windows_search_results(results, "pattern")

        case "2":
            raw_exts = input(
                "Введите расширения через запятую (например, .exe, .dll): "
            ).strip()
            extensions = [
                ext.strip() for ext in raw_exts.split(",") if ext.strip()
            ]
            results = find_by_windows_extension(extensions, current_path)
            format_windows_search_results(results, "extension")

        case "3":
            try:
                min_mb = float(
                    input("Введите минимальный размер в МБ: ").strip()
                )
            except ValueError:
                print("Ошибка: нужно ввести число.")
                return True

            results = find_large_files_windows(min_mb, current_path)
            format_windows_search_results(results, "large")

        case "4":
            results = find_windows_system_files(current_path)
            format_windows_search_results(results, "system")

        case "0":
            return False

        case _:
            print("Неверный выбор. Пожалуйста, введите число от 0 до 4.")

    again = input("\nПродолжить поиск? (y/n): ").strip().lower()
    return again == "y"

def format_windows_search_results(
    results: List[Any],
    search_type: str
) -> None:
    """
    Format and print Windows search results based on the search type.

    :param results: A list of file paths (str) or file info dictionaries
                    (for 'large' search type).
    :param search_type: The type of search performed ('pattern', 'extension',
                        'large', or 'system').
    """
    titles = {
        "pattern": "Результаты поиска по шаблону",
        "extension": "Результаты поиска по расширениям",
        "large": "Найденные крупные файлы",
        "system": "Найденные системные файлы Windows"
    }
    header = titles.get(search_type, "Результаты поиска")

    print(f"\n{'=' * 50}")
    print(f"{header} (Всего: {len(results)})")
    print(f"{'=' * 50}")

    if not results:
        print("Файлы не найдены.")
        return

    file_paths: List[str] = []

    for index, item in enumerate(results, start=1):
        if search_type == "large" and isinstance(item, dict):
            path = item["path"]
            size_bytes = int(item["size_mb"] * 1024 * 1024)
            formatted_size = utils.format_size(size_bytes)
            file_type = item.get("type", "")
            print(f"{index}. {path}")
            print(f"   Размер: {formatted_size} | Тип: {file_type}")
            file_paths.append(path)
        else:
            path = str(item)
            try:
                size_bytes = os.path.getsize(path)
                formatted_size = utils.format_size(size_bytes)
            except OSError:
                formatted_size = "Неизвестно"

            print(f"{index}. {path} ({formatted_size})")
            file_paths.append(path)

    common_dir = (
        os.path.dirname(file_paths)
        if len(file_paths) == 1
        else os.path.commonpath(file_paths)
    )
    if os.path.isfile(common_dir):
        common_dir = os.path.dirname(common_dir)

    attr_stats = analysis.get_windows_file_attributes_stats(common_dir)
    print(f"{'-' * 50}")
    print(
        f"Атрибуты файлов в каталоге ({common_dir}): "
        f"Скрытые: {attr_stats['hidden']} | "
        f"Системные: {attr_stats['system']} | "
        f"Только чтение: {attr_stats['readonly']}"
    )
    print(f"{'=' * 50}")