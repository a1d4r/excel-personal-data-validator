from pathlib import Path

from excel_personal_data_validator.config import AppConfig


def test_default_config():
    config = AppConfig(excel_path=Path("data.xlsx"), db_path=Path("names.db"))
    assert config.last_name_column == "A"
    assert config.first_name_column == "B"
    assert config.patronymic_column == "C"
    assert config.sheet_name is None
    assert config.start_row == 2


def test_custom_config():
    config = AppConfig(
        excel_path=Path("data.xlsx"),
        db_path=Path("names.db"),
        last_name_column="D",
        first_name_column="E",
        patronymic_column="F",
        sheet_name="Лист1",
        start_row=5,
    )
    assert config.last_name_column == "D"
    assert config.sheet_name == "Лист1"
    assert config.start_row == 5
