from collections.abc import Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from excel_personal_data_validator.db import CATEGORY_LABELS, NameCategory, NameDatabase
from excel_personal_data_validator.importer import import_names_to_db


class ImportTab(QWidget):
    """Вкладка импорта данных в базу из текстовых файлов."""

    def __init__(
        self, db: NameDatabase, known_names: dict[NameCategory, set[str]], on_import_done: Callable[[], None]
    ) -> None:
        super().__init__()
        self._db = db
        self._known_names = known_names
        self._on_import_done = on_import_done
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Импорт имён из текстовых файлов (по одному значению на строке):"))
        layout.addSpacing(10)

        # Файлы по категориям
        self._file_inputs: dict[NameCategory, QLineEdit] = {}
        for category in NameCategory:
            label = CATEGORY_LABELS[category]
            row = QHBoxLayout()
            file_input = QLineEdit()
            file_input.setPlaceholderText(f"Файл с категорией '{label}'...")
            file_input.setReadOnly(True)
            browse_btn = QPushButton("Обзор...")
            browse_btn.clicked.connect(lambda _checked, cat=category: self._browse_file(cat))
            row.addWidget(QLabel(f"{label}:"))
            row.addWidget(file_input, stretch=1)
            row.addWidget(browse_btn)
            layout.addLayout(row)
            self._file_inputs[category] = file_input

        layout.addSpacing(20)

        # Кнопка импорта
        btn_row = QHBoxLayout()
        import_btn = QPushButton("Импортировать")
        import_btn.setMinimumHeight(40)
        import_btn.clicked.connect(self._run_import)
        btn_row.addStretch()
        btn_row.addWidget(import_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addSpacing(10)

        # Результат
        self._result_label = QLabel("")
        layout.addWidget(self._result_label)

        layout.addStretch()

    def _browse_file(self, category: NameCategory) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Выберите текстовый файл", "", "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        if path:
            self._file_inputs[category].setText(path)

    def _run_import(self) -> None:
        files: dict[NameCategory, Path] = {}
        for category, input_field in self._file_inputs.items():
            text = input_field.text().strip()
            if text:
                path = Path(text)
                if not path.exists():
                    QMessageBox.warning(self, "Ошибка", f"Файл не найден: {path}")
                    return
                files[category] = path

        if not files:
            QMessageBox.warning(self, "Ошибка", "Выберите хотя бы один файл для импорта.")
            return

        try:
            self._db.initialize()
            counts = import_names_to_db(self._db, files)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Ошибка", str(exc))
            return

        # Обновляем known_names
        for category in NameCategory:
            self._known_names[category] = self._db.load_all(category)

        # Показываем результат
        total = sum(counts.values())
        parts = [f"{CATEGORY_LABELS[cat]}: {count}" for cat, count in counts.items()]
        parts.append(f"Всего: {total}")
        self._result_label.setText("Импорт завершён:\n" + "\n".join(parts))

        self._on_import_done()

        QMessageBox.information(self, "Готово", f"Импорт завершён. Загружено записей: {total}")
