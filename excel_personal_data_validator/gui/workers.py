from PySide6.QtCore import QThread, Signal

from excel_personal_data_validator.config import AppConfig
from excel_personal_data_validator.db import NameCategory
from excel_personal_data_validator.reader import read_excel
from excel_personal_data_validator.validator import ValidationResult, validate_rows


class ValidateWorker(QThread):
    """Фоновый поток для чтения Excel и валидации."""

    finished = Signal(ValidationResult, int)
    error = Signal(str)

    def __init__(self, config: AppConfig, known_names: dict[NameCategory, set[str]]) -> None:
        super().__init__()
        self._config = config
        self._known_names = known_names

    def run(self) -> None:
        try:
            rows = read_excel(self._config)
            result = validate_rows(rows, self._known_names)
            self.finished.emit(result, len(rows))
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
