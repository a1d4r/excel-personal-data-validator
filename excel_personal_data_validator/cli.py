import argparse
import sys

from pathlib import Path

from excel_personal_data_validator.config import AppConfig
from excel_personal_data_validator.db import NameCategory, NameDatabase
from excel_personal_data_validator.paths import get_db_path
from excel_personal_data_validator.reader import get_output_path, read_excel
from excel_personal_data_validator.ui import ReviewSummary, UserAction, print_summary, run_interactive_review
from excel_personal_data_validator.validator import validate_rows
from excel_personal_data_validator.writer import save_corrected_excel


def build_parser() -> argparse.ArgumentParser:
    """Создаёт парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(
        prog="validator", description="Проверка ФИО в Excel-файле по базе данных известных имён."
    )
    parser.add_argument("excel_file", type=Path, help="Путь к .xlsx файлу с данными ФИО")
    parser.add_argument(
        "--db-path", type=Path, default=None, help="Путь к БД (по умолчанию: names.db рядом с программой)"
    )
    parser.add_argument("--last-name-col", default="A", help="Столбец с фамилиями (по умолчанию: A)")
    parser.add_argument("--first-name-col", default="B", help="Столбец с именами (по умолчанию: B)")
    parser.add_argument("--patronymic-col", default="C", help="Столбец с отчествами (по умолчанию: C)")
    parser.add_argument("--sheet", default=None, help="Имя листа (по умолчанию: активный лист)")
    parser.add_argument("--start-row", type=int, default=2, help="Первая строка данных, 1-based (по умолчанию: 2)")
    return parser


def _parse_config(args: argparse.Namespace) -> AppConfig:
    """Создаёт конфигурацию из аргументов командной строки."""
    excel_path: Path = args.excel_file
    if not excel_path.exists():
        print(f"Ошибка: файл '{excel_path}' не найден")
        sys.exit(1)

    return AppConfig(
        excel_path=excel_path,
        db_path=args.db_path or get_db_path(),
        last_name_column=args.last_name_col,
        first_name_column=args.first_name_col,
        patronymic_column=args.patronymic_col,
        sheet_name=args.sheet,
        start_row=args.start_row,
    )


def _collect_corrections(summary: ReviewSummary, config: AppConfig) -> dict[tuple[int, str], str]:
    """Собирает исправления из решений пользователя."""
    corrections: dict[tuple[int, str], str] = {}
    for decision in summary.decisions:
        if decision.action == UserAction.REPLACE and decision.replacement:
            column = _category_to_column(decision.entry.category, config)
            for row_num in decision.entry.row_numbers:
                corrections[(row_num, column)] = decision.replacement
    return corrections


def _category_to_column(category: NameCategory, config: AppConfig) -> str:
    """Возвращает букву столбца для указанной категории."""
    mapping = {
        NameCategory.LAST_NAME: config.last_name_column,
        NameCategory.FIRST_NAME: config.first_name_column,
        NameCategory.PATRONYMIC: config.patronymic_column,
    }
    return mapping[category]


def main() -> None:
    """Главная функция приложения."""
    config = _parse_config(build_parser().parse_args())

    if not config.db_path.exists():
        print(f"База данных не найдена. Создаётся новая: {config.db_path}")

    with NameDatabase(config.db_path) as db:
        db.initialize()

        print("Загрузка базы данных...")
        known_names: dict[NameCategory, set[str]] = {cat: db.load_all(cat) for cat in NameCategory}
        print(f"В базе: {sum(len(v) for v in known_names.values())} значений")

        print(f"Чтение файла: {config.excel_path}")
        rows = read_excel(config)
        print(f"Прочитано строк: {len(rows)}")

        if not rows:
            print("Файл пуст или не содержит данных.")
            return

        result = validate_rows(rows, known_names)

        if not result.unknown_entries:
            print("\nВсе данные корректны ✓")
            return

        summary = run_interactive_review(result.unknown_entries, known_names, db)
        corrections = _collect_corrections(summary, config)

        output_path_str: str | None = None
        if corrections:
            output_path = get_output_path(config.excel_path)
            save_corrected_excel(config.excel_path, output_path, corrections, config.sheet_name)
            output_path_str = str(output_path)

        print_summary(summary, output_path_str)
