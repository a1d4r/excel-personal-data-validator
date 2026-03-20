from pathlib import Path

import pytest

from excel_personal_data_validator.db import NameCategory, NameDatabase


def test_initialize_creates_tables(tmp_path: Path):
    db = NameDatabase(tmp_path / "test.db")
    db.initialize()
    for cat in NameCategory:
        result = db.load_all(cat)
        assert result == set()
    db.close()


def test_add_name_and_load(tmp_db: NameDatabase):
    tmp_db.add_name(NameCategory.LAST_NAME, "Иванов")
    result = tmp_db.load_all(NameCategory.LAST_NAME)
    assert "иванов" in result


def test_add_name_duplicate_ignored(tmp_db: NameDatabase):
    tmp_db.add_name(NameCategory.FIRST_NAME, "Иван")
    tmp_db.add_name(NameCategory.FIRST_NAME, "Иван")
    result = tmp_db.load_all(NameCategory.FIRST_NAME)
    assert len(result) == 1


def test_add_name_case_insensitive_duplicate(tmp_db: NameDatabase):
    tmp_db.add_name(NameCategory.FIRST_NAME, "Иван")
    tmp_db.add_name(NameCategory.FIRST_NAME, "иван")
    result = tmp_db.load_all(NameCategory.FIRST_NAME)
    assert len(result) == 1


def test_add_names_bulk(tmp_db: NameDatabase):
    names = ["Иванов", "Петров", "Сидоров"]
    tmp_db.add_names_bulk(NameCategory.LAST_NAME, names)
    result = tmp_db.load_all(NameCategory.LAST_NAME)
    assert len(result) == 3
    assert "иванов" in result
    assert "петров" in result


def test_load_all_returns_lowercase(tmp_db: NameDatabase):
    tmp_db.add_name(NameCategory.PATRONYMIC, "Петрович")
    result = tmp_db.load_all(NameCategory.PATRONYMIC)
    assert "петрович" in result
    assert "Петрович" not in result


def test_context_manager(tmp_path: Path):
    db_path = tmp_path / "ctx.db"
    with NameDatabase(db_path) as db:
        db.initialize()
        db.add_name(NameCategory.FIRST_NAME, "Тест")

    # Проверяем что данные сохранены после закрытия
    with NameDatabase(db_path) as db:
        result = db.load_all(NameCategory.FIRST_NAME)
        assert "тест" in result


@pytest.mark.parametrize("category", list(NameCategory))
def test_categories_are_independent(tmp_db: NameDatabase, category: NameCategory):
    tmp_db.add_name(category, "Тестовое")
    for other in NameCategory:
        result = tmp_db.load_all(other)
        if other == category:
            assert len(result) == 1
        else:
            assert len(result) == 0


def test_list_names_returns_sorted(tmp_db: NameDatabase):
    tmp_db.add_names_bulk(NameCategory.LAST_NAME, ["Сидоров", "Алексеев", "Иванов"])
    rows = tmp_db.list_names(NameCategory.LAST_NAME)
    values = [v for _, v in rows]
    assert values == ["Алексеев", "Иванов", "Сидоров"]


def test_list_names_search_filter(tmp_db: NameDatabase):
    tmp_db.add_names_bulk(NameCategory.LAST_NAME, ["Иванов", "Иванова", "Петров"])
    rows = tmp_db.list_names(NameCategory.LAST_NAME, "иван")
    values = [v for _, v in rows]
    assert len(values) == 2
    assert all("ван" in v.lower() for v in values)


def test_list_names_empty_search(tmp_db: NameDatabase):
    tmp_db.add_names_bulk(NameCategory.FIRST_NAME, ["Иван", "Пётр"])
    rows = tmp_db.list_names(NameCategory.FIRST_NAME, "")
    assert len(rows) == 2


def test_update_name(tmp_db: NameDatabase):
    tmp_db.add_name(NameCategory.LAST_NAME, "Иванов")
    rows = tmp_db.list_names(NameCategory.LAST_NAME)
    row_id = rows[0][0]
    tmp_db.update_name(NameCategory.LAST_NAME, row_id, "Петров")
    updated = tmp_db.list_names(NameCategory.LAST_NAME)
    assert len(updated) == 1
    assert updated[0][1] == "Петров"


def test_delete_name(tmp_db: NameDatabase):
    tmp_db.add_names_bulk(NameCategory.LAST_NAME, ["Иванов", "Петров"])
    rows = tmp_db.list_names(NameCategory.LAST_NAME)
    assert len(rows) == 2
    tmp_db.delete_name(NameCategory.LAST_NAME, rows[0][0])
    remaining = tmp_db.list_names(NameCategory.LAST_NAME)
    assert len(remaining) == 1
