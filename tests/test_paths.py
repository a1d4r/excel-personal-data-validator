import sys

from pathlib import Path
from unittest import mock

from excel_personal_data_validator.paths import get_app_dir, get_db_path


def test_get_app_dir_not_frozen():
    """В обычном режиме возвращает cwd."""
    result = get_app_dir()
    assert result == Path.cwd()


def test_get_app_dir_frozen():
    """Для PyInstaller возвращает директорию exe."""
    frozen = True
    with (
        mock.patch.object(sys, "frozen", frozen, create=True),
        mock.patch.object(sys, "executable", "/opt/app/validator.exe"),
    ):
        result = get_app_dir()
        assert result == Path("/opt/app")


def test_get_db_path_default():
    result = get_db_path()
    assert result.name == "names.db"


def test_get_db_path_custom_name():
    result = get_db_path("custom.db")
    assert result.name == "custom.db"
