from pathlib import Path

import pydantic


class AppConfig(pydantic.BaseModel):
    """Конфигурация приложения."""

    excel_path: Path
    db_path: Path
    last_name_column: str = "A"
    first_name_column: str = "B"
    patronymic_column: str = "C"
    sheet_name: str | None = None
    start_row: int = 1
