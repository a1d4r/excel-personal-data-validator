from excel_personal_data_validator.db import NameCategory
from excel_personal_data_validator.reader import PersonRow
from excel_personal_data_validator.validator import validate_rows


def test_all_known(known_names):
    rows = [
        PersonRow(row_number=2, last_name="Иванов", first_name="Иван", patronymic="Петрович"),
        PersonRow(row_number=3, last_name="Петров", first_name="Пётр", patronymic="Сергеевич"),
    ]
    result = validate_rows(rows, known_names)
    assert len(result.unknown_entries) == 0
    assert result.total_rows == 2


def test_unknown_detected(known_names):
    rows = [PersonRow(row_number=2, last_name="Ивано", first_name="Иван", patronymic="Петрович")]
    result = validate_rows(rows, known_names)
    assert len(result.unknown_entries) == 1
    assert result.unknown_entries[0].value == "Ивано"
    assert result.unknown_entries[0].category == NameCategory.LAST_NAME
    assert result.unknown_entries[0].row_numbers == (2,)


def test_case_insensitive(known_names):
    rows = [PersonRow(row_number=2, last_name="иванов", first_name="ИВАН", patronymic="петрович")]
    result = validate_rows(rows, known_names)
    assert len(result.unknown_entries) == 0


def test_groups_same_unknowns(known_names):
    rows = [
        PersonRow(row_number=2, last_name="Ивано", first_name="Иван", patronymic="Петрович"),
        PersonRow(row_number=5, last_name="Ивано", first_name="Елена", patronymic="Ивановна"),
    ]
    result = validate_rows(rows, known_names)
    last_name_unknowns = [e for e in result.unknown_entries if e.category == NameCategory.LAST_NAME]
    assert len(last_name_unknowns) == 1
    assert last_name_unknowns[0].row_numbers == (2, 5)


def test_empty_values_skipped(known_names):
    rows = [PersonRow(row_number=2, last_name="", first_name="Иван", patronymic="")]
    result = validate_rows(rows, known_names)
    assert len(result.unknown_entries) == 0


def test_multiple_categories_unknown(known_names):
    rows = [PersonRow(row_number=2, last_name="Неизвестный", first_name="Неизвестное", patronymic="Неизвестнович")]
    result = validate_rows(rows, known_names)
    assert len(result.unknown_entries) == 3
    categories = {e.category for e in result.unknown_entries}
    assert categories == {NameCategory.LAST_NAME, NameCategory.FIRST_NAME, NameCategory.PATRONYMIC}
