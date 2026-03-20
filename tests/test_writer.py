from pathlib import Path

from openpyxl import Workbook, load_workbook

from excel_personal_data_validator.config import AppConfig
from excel_personal_data_validator.db import NameCategory
from excel_personal_data_validator.models import EntryDecision, ReviewSummary, UserAction
from excel_personal_data_validator.validator import UnknownEntry
from excel_personal_data_validator.writer import category_to_column, collect_corrections, save_corrected_excel


def test_save_corrected_excel(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    output = tmp_path / "output.xlsx"

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Фамилия", "Имя", "Отчество"])
    ws.append(["Ивано", "Иван", "Петрович"])
    ws.append(["Петров", "Алексй", "Сергеевич"])
    wb.save(source)
    wb.close()

    corrections = {(2, "A"): "Иванов", (3, "B"): "Алексей"}
    save_corrected_excel(source, output, corrections)

    wb = load_workbook(output)
    ws = wb.active
    assert ws is not None
    assert ws["A2"].value == "Иванов"
    assert ws["B3"].value == "Алексей"
    # Неизменённые ячейки
    assert ws["B2"].value == "Иван"
    assert ws["C2"].value == "Петрович"
    wb.close()


def test_save_corrected_excel_no_corrections(tmp_path: Path):
    source = tmp_path / "source.xlsx"
    output = tmp_path / "output.xlsx"

    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Данные"])
    wb.save(source)
    wb.close()

    save_corrected_excel(source, output, {})
    assert not output.exists()


def test_category_to_column():
    config = AppConfig(
        excel_path=Path("test.xlsx"),
        db_path=Path("test.db"),
        last_name_column="D",
        first_name_column="E",
        patronymic_column="F",
    )
    assert category_to_column(NameCategory.LAST_NAME, config) == "D"
    assert category_to_column(NameCategory.FIRST_NAME, config) == "E"
    assert category_to_column(NameCategory.PATRONYMIC, config) == "F"


def test_collect_corrections():
    config = AppConfig(excel_path=Path("test.xlsx"), db_path=Path("test.db"))
    entry1 = UnknownEntry(category=NameCategory.LAST_NAME, value="Ивано", row_numbers=(2, 5))
    entry2 = UnknownEntry(category=NameCategory.FIRST_NAME, value="Алексй", row_numbers=(3,))
    entry3 = UnknownEntry(category=NameCategory.PATRONYMIC, value="Хз", row_numbers=(4,))

    summary = ReviewSummary(
        decisions=[
            EntryDecision(entry=entry1, action=UserAction.REPLACE, replacement="Иванов"),
            EntryDecision(entry=entry2, action=UserAction.REPLACE, replacement="Алексей"),
            EntryDecision(entry=entry3, action=UserAction.SKIP),
        ]
    )

    corrections = collect_corrections(summary, config)
    assert corrections == {(2, "A"): "Иванов", (5, "A"): "Иванов", (3, "B"): "Алексей"}
