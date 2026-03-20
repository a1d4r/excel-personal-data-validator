# Plan: Excel Personal Data Validator — Design & Implementation

## Context

Пользователь быстро вводит ФИО (фамилия, имя, отчество) в Excel-файл и допускает опечатки. Нужна консольная программа, которая:
- Читает Excel-файл (каждое поле в отдельном столбце)
- Сравнивает каждое значение с базой известных имён (SQLite, 50K+ записей)
- Показывает неизвестные значения пользователю: он решает — опечатка или новое имя (добавить в БД)
- Работает офлайн, упаковывается в exe через PyInstaller, быстро работает на старых ПК

## Принятые решения

- **Наполнение БД:** Только через работу с программой (без отдельной команды импорта). БД начинается пустой и пополняется по мере обработки Excel-файлов.
- **Язык интерфейса:** Русский — все сообщения, подсказки и вывод на русском языке.

## Структура модулей

```
excel_personal_data_validator/
    __init__.py              # (есть)
    __main__.py              # точка входа: python -m excel_personal_data_validator
    cli.py                   # argparse + main() — оркестрация
    config.py                # AppConfig (pydantic BaseModel)
    db.py                    # SQLite: схема, NameDatabase, NameCategory
    reader.py                # Чтение Excel через openpyxl
    validator.py             # Чистая функция валидации
    ui.py                    # Интерактивный консольный UI
    paths.py                 # Определение пути к БД (PyInstaller-совместимое)
tests/
    conftest.py              # Общие фикстуры
    test_db.py
    test_reader.py
    test_validator.py
    test_ui.py
    test_paths.py
    test_cli.py
```

Удалить: `excel_personal_data_validator/example.py`, `tests/test_example/`

## Зависимости

Добавить в `pyproject.toml`:
```toml
dependencies = [
    "pydantic>=2.9.2",
    "openpyxl>=3.1.0",
]
```

## 1. `paths.py` — Определение пути к БД

```python
def get_app_dir() -> Path:
    """Директория рядом с exe (PyInstaller) или cwd."""
    # sys.frozen → Path(sys.executable).parent
    # иначе → Path.cwd()

def get_db_path(db_name: str = "names.db") -> Path:
    """Полный путь к файлу БД."""
```

## 2. `config.py` — Конфигурация

```python
class AppConfig(pydantic.BaseModel):
    excel_path: Path
    db_path: Path
    last_name_column: str = "A"
    first_name_column: str = "B"
    patronymic_column: str = "C"
    sheet_name: str | None = None   # None = активный лист
    start_row: int = 2              # пропуск заголовка
```

## 3. `db.py` — БД и репозиторий

**Схема** — 3 таблицы с `COLLATE NOCASE`:
```sql
CREATE TABLE IF NOT EXISTS last_names (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    value TEXT NOT NULL UNIQUE COLLATE NOCASE
);
-- аналогично first_names, patronymics
```

**Классы:**
- `NameCategory(StrEnum)` — `LAST_NAME = "last_names"`, `FIRST_NAME = "first_names"`, `PATRONYMIC = "patronymics"`
- `NameDatabase`:
  - `__init__(db_path: Path)` — открывает соединение, `PRAGMA journal_mode=WAL`
  - `initialize()` — CREATE TABLE IF NOT EXISTS
  - `load_all(category) -> set[str]` — загрузка всех значений в set (lowercase) для O(1) поиска
  - `add_name(category, value)` — INSERT
  - `add_names_bulk(category, values)` — executemany
  - `close()` — закрытие соединения
  - Поддержка context manager (`__enter__`/`__exit__`)

**Производительность:** 50K строк → ~5-10 МБ RAM, загрузка <100мс.

## 4. `reader.py` — Чтение Excel

```python
@dataclasses.dataclass(frozen=True)
class PersonRow:
    row_number: int
    last_name: str
    first_name: str
    patronymic: str

def read_excel(config: AppConfig) -> list[PersonRow]:
    # openpyxl read_only=True, data_only=True
    # strip whitespace, пропуск пустых строк
```

## 5. `validator.py` — Валидация

```python
@dataclasses.dataclass(frozen=True)
class UnknownEntry:
    row_number: int
    category: NameCategory
    value: str

@dataclasses.dataclass(frozen=True)
class ValidationResult:
    valid_rows: list[PersonRow]
    unknown_entries: list[UnknownEntry]

def validate_rows(rows: list[PersonRow], known_names: dict[NameCategory, set[str]]) -> ValidationResult:
    # Чистая функция, case-insensitive проверка
```

## 6. `ui.py` — Интерактивный UI

```python
@dataclasses.dataclass
class ReviewSummary:
    added_to_db: list[tuple[NameCategory, str]]
    skipped_as_typos: list[tuple[NameCategory, str]]

def run_interactive_review(unknown_entries, db, known_names) -> ReviewSummary:
    # Группировка по (category, value), дедупликация
    # Показ: "Неизвестная фамилия 'Ивано' (строки: 5, 12, 47)"
    # [1] Добавить в базу  [2] Пропустить (опечатка)
    # Прогресс: "Проверка 3 из 15..."
    # Итог: "Добавлено: 5. Опечаток: 10."
```

## 7. `cli.py` + `__main__.py` — CLI

**Аргументы argparse:**
- `excel_file` (positional) — путь к .xlsx
- `--db-path` — путь к БД (по умолчанию: рядом с exe)
- `--last-name-col` (default "A")
- `--first-name-col` (default "B")
- `--patronymic-col` (default "C")
- `--sheet` — имя листа
- `--start-row` (default 2)

**Поток main():**
1. Парсинг аргументов → AppConfig
2. Открытие БД, initialize()
3. load_all() для трёх категорий → dict[NameCategory, set[str]]
4. read_excel() → list[PersonRow]
5. validate_rows() → ValidationResult
6. Если нет unknown → сообщение "Все данные корректны" и выход
7. Если есть → run_interactive_review()
8. Итоговая сводка

**`__main__.py`:**
```python
from excel_personal_data_validator.cli import main
if __name__ == "__main__":
    main()
```

## 8. PyInstaller

Команда: `pyinstaller --onefile --name validator excel_personal_data_validator/__main__.py`

БД `names.db` создаётся рядом с exe при первом запуске. Если пользователь удалит файл — создаётся заново (пустая) с предупреждением.

## Файлы для изменения

| Файл | Действие |
|------|----------|
| `pyproject.toml` | Добавить openpyxl в dependencies |
| `excel_personal_data_validator/example.py` | Удалить |
| `excel_personal_data_validator/__main__.py` | Создать |
| `excel_personal_data_validator/paths.py` | Создать |
| `excel_personal_data_validator/config.py` | Создать |
| `excel_personal_data_validator/db.py` | Создать |
| `excel_personal_data_validator/reader.py` | Создать |
| `excel_personal_data_validator/validator.py` | Создать |
| `excel_personal_data_validator/ui.py` | Создать |
| `excel_personal_data_validator/cli.py` | Создать |
| `tests/test_example/` | Удалить |
| `tests/conftest.py` | Создать |
| `tests/test_db.py` | Создать |
| `tests/test_reader.py` | Создать |
| `tests/test_validator.py` | Создать |
| `tests/test_ui.py` | Создать |
| `tests/test_paths.py` | Создать |
| `tests/test_cli.py` | Создать |

## Верификация

1. `uv run pytest` — все тесты проходят
2. `uv run mypy excel_personal_data_validator` — без ошибок
3. `uv run ruff check` — без ошибок
4. Ручной тест: создать тестовый .xlsx с ФИО, запустить `python -m excel_personal_data_validator test.xlsx`, проверить интерактивный флоу
