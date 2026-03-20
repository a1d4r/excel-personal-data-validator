import dataclasses

from collections import defaultdict

from excel_personal_data_validator.db import NameCategory
from excel_personal_data_validator.reader import PersonRow


@dataclasses.dataclass(frozen=True)
class UnknownEntry:
    """Значение, не найденное в базе данных."""

    category: NameCategory
    value: str
    row_numbers: tuple[int, ...]


@dataclasses.dataclass(frozen=True)
class ValidationResult:
    """Результат валидации всех строк."""

    unknown_entries: list[UnknownEntry]
    total_rows: int


def validate_rows(rows: list[PersonRow], known_names: dict[NameCategory, set[str]]) -> ValidationResult:
    """Проверяет каждое поле каждой строки на наличие в базе.

    Группирует одинаковые неизвестные значения, собирает номера строк.
    Проверка регистронезависимая.
    """
    unknown_map: dict[tuple[NameCategory, str], list[int]] = defaultdict(list)

    field_mapping: list[tuple[NameCategory, str]] = []

    for row in rows:
        field_mapping = [
            (NameCategory.LAST_NAME, row.last_name),
            (NameCategory.FIRST_NAME, row.first_name),
            (NameCategory.PATRONYMIC, row.patronymic),
        ]
        for category, value in field_mapping:
            if not value:
                continue
            if value.lower() not in known_names.get(category, set()):
                unknown_map[(category, value)].append(row.row_number)

    unknown_entries = [
        UnknownEntry(category=cat, value=val, row_numbers=tuple(row_nums))
        for (cat, val), row_nums in sorted(unknown_map.items(), key=lambda item: (item[0][0], item[0][1].lower()))
    ]

    return ValidationResult(unknown_entries=unknown_entries, total_rows=len(rows))
