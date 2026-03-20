import sqlite3

from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path


class NameCategory(StrEnum):
    """Категория имени — соответствует таблице в БД."""

    LAST_NAME = "last_names"
    FIRST_NAME = "first_names"
    PATRONYMIC = "patronymics"


CATEGORY_LABELS: dict[NameCategory, str] = {
    NameCategory.LAST_NAME: "Фамилия",
    NameCategory.FIRST_NAME: "Имя",
    NameCategory.PATRONYMIC: "Отчество",
}

_TABLES = list(NameCategory)


class NameDatabase:
    """Репозиторий для работы с базой данных имён (SQLite)."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")

    def initialize(self) -> None:
        """Создаёт таблицы, если они не существуют."""
        for table in _TABLES:
            self._conn.execute(
                f"CREATE TABLE IF NOT EXISTS {table} ("
                "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
                "  value TEXT NOT NULL UNIQUE COLLATE NOCASE"
                ")"
            )
        self._conn.commit()

    def load_all(self, category: NameCategory) -> set[str]:
        """Загружает все значения категории в set (lowercase) для O(1) поиска."""
        cursor = self._conn.execute(f"SELECT value FROM {category}")  # noqa: S608
        return {row[0].lower() for row in cursor}

    def add_name(self, category: NameCategory, value: str) -> None:
        """Добавляет новое имя в указанную категорию."""
        self._conn.execute(f"INSERT OR IGNORE INTO {category} (value) VALUES (?)", (value,))  # noqa: S608
        self._conn.commit()

    def add_names_bulk(self, category: NameCategory, values: Iterable[str]) -> None:
        """Массовая вставка значений в категорию."""
        self._conn.executemany(
            f"INSERT OR IGNORE INTO {category} (value) VALUES (?)",  # noqa: S608
            [(v,) for v in values],
        )
        self._conn.commit()

    def close(self) -> None:
        """Закрывает соединение с БД."""
        self._conn.close()

    def __enter__(self) -> "NameDatabase":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
