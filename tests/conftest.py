from pathlib import Path

import pytest

from openpyxl import Workbook

from excel_personal_data_validator.db import NameCategory, NameDatabase


@pytest.fixture
def tmp_db(tmp_path: Path) -> NameDatabase:
    """Создаёт временную тестовую БД."""
    db = NameDatabase(tmp_path / "test.db")
    db.initialize()
    return db


@pytest.fixture
def known_names(tmp_db: NameDatabase) -> dict[NameCategory, set[str]]:
    """Возвращает набор известных имён для тестов."""
    test_data: dict[NameCategory, list[str]] = {
        NameCategory.LAST_NAME: ["Иванов", "Петров", "Сидоров", "Иванова", "Петрова"],
        NameCategory.FIRST_NAME: ["Иван", "Пётр", "Мария", "Елена", "Алексей"],
        NameCategory.PATRONYMIC: ["Иванович", "Петрович", "Сергеевич", "Ивановна", "Петровна"],
    }
    for category, values in test_data.items():
        tmp_db.add_names_bulk(category, values)
    return {cat: tmp_db.load_all(cat) for cat in NameCategory}


@pytest.fixture
def sample_xlsx(tmp_path: Path) -> Path:
    """Создаёт тестовый .xlsx файл с данными ФИО."""
    path = tmp_path / "test_data.xlsx"
    wb = Workbook()
    ws = wb.active
    assert ws is not None

    ws.append(["Фамилия", "Имя", "Отчество"])
    ws.append(["Иванов", "Иван", "Петрович"])
    ws.append(["Петров", "Пётр", "Сергеевич"])
    ws.append(["Ивано", "Елена", "Петровна"])  # опечатка в фамилии
    ws.append(["Сидоров", "Алексй", "Иванович"])  # опечатка в имени

    wb.save(path)
    wb.close()
    return path
