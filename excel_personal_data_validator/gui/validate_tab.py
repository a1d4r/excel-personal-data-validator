from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from excel_personal_data_validator.config import AppConfig
from excel_personal_data_validator.db import NameCategory, NameDatabase
from excel_personal_data_validator.gui.review_widget import ReviewWidget
from excel_personal_data_validator.gui.workers import ValidateWorker
from excel_personal_data_validator.reader import get_output_path
from excel_personal_data_validator.validator import ValidationResult
from excel_personal_data_validator.writer import collect_corrections, save_corrected_excel


class ValidateTab(QWidget):
    """Вкладка проверки Excel-файла."""

    def __init__(self, db: NameDatabase, known_names: dict[NameCategory, set[str]], db_path: Path) -> None:
        super().__init__()
        self._db = db
        self._known_names = known_names
        self._db_path = db_path
        self._worker: ValidateWorker | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        self._stack = QStackedWidget()

        # Страница 0: форма настроек
        self._form_page = self._create_form_page()
        self._stack.addWidget(self._form_page)

        # Страница 1: просмотр неизвестных (создаётся при необходимости)
        self._review_widget: ReviewWidget | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(self._stack)

    def _create_form_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)

        # Выбор файла
        file_row = QHBoxLayout()
        self._file_input = QLineEdit()
        self._file_input.setPlaceholderText("Путь к .xlsx файлу...")
        self._file_input.setReadOnly(True)
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(QLabel("Файл Excel:"))
        file_row.addWidget(self._file_input, stretch=1)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)

        # Настройки столбцов
        form = QFormLayout()

        columns_row = QHBoxLayout()
        self._last_name_col = QLineEdit("A")
        self._last_name_col.setMaximumWidth(50)
        self._first_name_col = QLineEdit("B")
        self._first_name_col.setMaximumWidth(50)
        self._patronymic_col = QLineEdit("C")
        self._patronymic_col.setMaximumWidth(50)
        columns_row.addWidget(QLabel("Фамилии:"))
        columns_row.addWidget(self._last_name_col)
        columns_row.addSpacing(20)
        columns_row.addWidget(QLabel("Имена:"))
        columns_row.addWidget(self._first_name_col)
        columns_row.addSpacing(20)
        columns_row.addWidget(QLabel("Отчества:"))
        columns_row.addWidget(self._patronymic_col)
        columns_row.addStretch()
        form.addRow("Столбцы:", columns_row)

        settings_row = QHBoxLayout()
        self._sheet_input = QLineEdit()
        self._sheet_input.setPlaceholderText("активный лист")
        self._sheet_input.setMaximumWidth(200)
        self._start_row_input = QLineEdit("2")
        self._start_row_input.setMaximumWidth(50)
        settings_row.addWidget(QLabel("Лист:"))
        settings_row.addWidget(self._sheet_input)
        settings_row.addSpacing(20)
        settings_row.addWidget(QLabel("Начальная строка:"))
        settings_row.addWidget(self._start_row_input)
        settings_row.addStretch()
        form.addRow("Параметры:", settings_row)

        layout.addLayout(form)

        # Кнопка запуска
        btn_row = QHBoxLayout()
        self._validate_btn = QPushButton("Проверить")
        self._validate_btn.setMinimumHeight(40)
        self._validate_btn.clicked.connect(self._start_validation)
        btn_row.addStretch()
        btn_row.addWidget(self._validate_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        # Лог
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(200)
        layout.addWidget(self._log)

        layout.addStretch()
        return page

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Выберите Excel файл", "", "Excel файлы (*.xlsx)")
        if path:
            self._file_input.setText(path)

    def _build_config(self) -> AppConfig | None:
        excel_path = Path(self._file_input.text().strip())
        if not excel_path.name:
            QMessageBox.warning(self, "Ошибка", "Выберите Excel файл.")
            return None
        if not excel_path.exists():
            QMessageBox.warning(self, "Ошибка", f"Файл '{excel_path}' не найден.")
            return None

        try:
            start_row = int(self._start_row_input.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Начальная строка должна быть числом.")
            return None

        sheet = self._sheet_input.text().strip() or None

        return AppConfig(
            excel_path=excel_path,
            db_path=self._db_path,
            last_name_column=self._last_name_col.text().strip().upper() or "A",
            first_name_column=self._first_name_col.text().strip().upper() or "B",
            patronymic_column=self._patronymic_col.text().strip().upper() or "C",
            sheet_name=sheet,
            start_row=start_row,
        )

    def _start_validation(self) -> None:
        config = self._build_config()
        if config is None:
            return

        self._current_config = config
        self._log.clear()
        self._log.append("Чтение файла и проверка данных...")
        self._validate_btn.setEnabled(False)

        self._worker = ValidateWorker(config, self._known_names)
        self._worker.finished.connect(self._on_validation_done)
        self._worker.error.connect(self._on_validation_error)
        self._worker.start()

    def _on_validation_done(self, result: ValidationResult, total_rows: int) -> None:
        self._validate_btn.setEnabled(True)
        self._log.append(f"Прочитано строк: {total_rows}")

        if not result.unknown_entries:
            self._log.append("Все данные корректны!")
            QMessageBox.information(self, "Результат", "Все данные корректны!")
            return

        self._log.append(f"Найдено неизвестных значений: {len(result.unknown_entries)}")

        # Создаём виджет просмотра
        if self._review_widget is not None:
            self._stack.removeWidget(self._review_widget)
            self._review_widget.deleteLater()

        self._review_widget = ReviewWidget(
            unknown_entries=result.unknown_entries,
            known_names=self._known_names,
            db=self._db,
            on_complete=self._on_review_complete,
            on_cancel=self._on_review_cancel,
        )
        self._stack.addWidget(self._review_widget)
        self._stack.setCurrentWidget(self._review_widget)

    def _on_validation_error(self, error_msg: str) -> None:
        self._validate_btn.setEnabled(True)
        self._log.append(f"Ошибка: {error_msg}")
        QMessageBox.critical(self, "Ошибка", error_msg)

    def _on_review_complete(self, summary: "ReviewSummary") -> None:  # type: ignore[name-defined]  # noqa: F821
        self._stack.setCurrentIndex(0)

        corrections = collect_corrections(summary, self._current_config)

        output_path_str = ""
        if corrections:
            output_path = get_output_path(self._current_config.excel_path)
            save_corrected_excel(
                self._current_config.excel_path, output_path, corrections, self._current_config.sheet_name
            )
            output_path_str = str(output_path)

        parts = []
        if summary.replaced_count:
            parts.append(f"Исправлено: {summary.replaced_count}")
        if summary.added_count:
            parts.append(f"Добавлено в базу: {summary.added_count}")
        if summary.skipped_count:
            parts.append(f"Пропущено: {summary.skipped_count}")
        if output_path_str:
            parts.append(f"Сохранено: {output_path_str}")

        result_text = "\n".join(parts)
        self._log.append(f"\n{'=' * 40}\n{result_text}\n{'=' * 40}")

        msg = QMessageBox(self)
        msg.setWindowTitle("Итого")
        msg.setText(result_text)
        msg.setIcon(QMessageBox.Icon.Information)
        if output_path_str:
            msg.addButton("Открыть папку", QMessageBox.ButtonRole.ActionRole)
        msg.addButton("Готово", QMessageBox.ButtonRole.AcceptRole)
        msg.exec()

        if msg.clickedButton() and msg.clickedButton().text() == "Открыть папку":
            import subprocess
            import sys

            folder = str(Path(output_path_str).parent)
            if sys.platform == "win32":
                subprocess.Popen(["explorer", folder])  # noqa: S603, S607
            elif sys.platform == "darwin":
                subprocess.Popen(["open", folder])  # noqa: S603, S607
            else:
                subprocess.Popen(["xdg-open", folder])  # noqa: S603, S607

    def _on_review_cancel(self) -> None:
        self._stack.setCurrentIndex(0)
        self._log.append("Проверка отменена.")

    def _log_message(self, text: str) -> None:
        self._log.append(text)
        scrollbar = self._log.verticalScrollBar()
        if scrollbar is not None:
            scrollbar.setValue(scrollbar.maximum())
