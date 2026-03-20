from pathlib import Path

from excel_personal_data_validator.db import NameCategory, NameDatabase


def read_names_file(path: Path) -> list[str]:
    """Читает файл с именами (по одному на строке), возвращает непустые строки."""
    text = path.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def import_names_to_db(db: NameDatabase, files: dict[NameCategory, Path]) -> dict[NameCategory, int]:
    """Импортирует имена из файлов в БД. Возвращает количество загруженных значений по категориям."""
    result: dict[NameCategory, int] = {}
    for category, path in files.items():
        names = read_names_file(path)
        if names:
            db.add_names_bulk(category, names)
        result[category] = len(names)
    return result
