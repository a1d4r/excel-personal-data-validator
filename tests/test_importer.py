from pathlib import Path

from excel_personal_data_validator.db import NameCategory, NameDatabase
from excel_personal_data_validator.importer import import_names_to_db, read_names_file


def test_read_names_file(tmp_path: Path):
    path = tmp_path / "names.txt"
    path.write_text("Иван\nПётр\nМария\n", encoding="utf-8")
    result = read_names_file(path)
    assert result == ["Иван", "Пётр", "Мария"]


def test_read_names_file_strips_whitespace(tmp_path: Path):
    path = tmp_path / "names.txt"
    path.write_text("  Иван  \n  Пётр\n", encoding="utf-8")
    result = read_names_file(path)
    assert result == ["Иван", "Пётр"]


def test_read_names_file_skips_empty_lines(tmp_path: Path):
    path = tmp_path / "names.txt"
    path.write_text("Иван\n\n\nПётр\n  \nМария\n", encoding="utf-8")
    result = read_names_file(path)
    assert result == ["Иван", "Пётр", "Мария"]


def test_read_names_file_empty(tmp_path: Path):
    path = tmp_path / "names.txt"
    path.write_text("", encoding="utf-8")
    result = read_names_file(path)
    assert result == []


def test_import_names_to_db(tmp_path: Path, tmp_db: NameDatabase):
    first_names = tmp_path / "first.txt"
    first_names.write_text("Иван\nПётр\n", encoding="utf-8")

    last_names = tmp_path / "last.txt"
    last_names.write_text("Иванов\nПетров\nСидоров\n", encoding="utf-8")

    files = {NameCategory.FIRST_NAME: first_names, NameCategory.LAST_NAME: last_names}
    counts = import_names_to_db(tmp_db, files)

    assert counts[NameCategory.FIRST_NAME] == 2
    assert counts[NameCategory.LAST_NAME] == 3

    assert "иван" in tmp_db.load_all(NameCategory.FIRST_NAME)
    assert "иванов" in tmp_db.load_all(NameCategory.LAST_NAME)


def test_import_names_to_db_all_categories(tmp_path: Path, tmp_db: NameDatabase):
    for name, _cat, content in [
        ("last.txt", NameCategory.LAST_NAME, "Иванов\n"),
        ("first.txt", NameCategory.FIRST_NAME, "Иван\n"),
        ("patronymic.txt", NameCategory.PATRONYMIC, "Иванович\n"),
    ]:
        (tmp_path / name).write_text(content, encoding="utf-8")

    files = {
        NameCategory.LAST_NAME: tmp_path / "last.txt",
        NameCategory.FIRST_NAME: tmp_path / "first.txt",
        NameCategory.PATRONYMIC: tmp_path / "patronymic.txt",
    }
    counts = import_names_to_db(tmp_db, files)

    assert counts[NameCategory.LAST_NAME] == 1
    assert counts[NameCategory.FIRST_NAME] == 1
    assert counts[NameCategory.PATRONYMIC] == 1
    assert "иванович" in tmp_db.load_all(NameCategory.PATRONYMIC)
