import sys

from pathlib import Path


def get_app_dir() -> Path:
    """Возвращает директорию приложения.

    Для PyInstaller --onefile: директория, содержащая .exe.
    Для обычного запуска: текущая рабочая директория.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path.cwd()


def get_db_path(db_name: str = "names.db") -> Path:
    """Возвращает полный путь к файлу базы данных."""
    return get_app_dir() / db_name
