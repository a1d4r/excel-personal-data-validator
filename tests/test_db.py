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
