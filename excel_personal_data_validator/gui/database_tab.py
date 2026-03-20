from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from excel_personal_data_validator.db import CATEGORY_LABELS, NameCategory, NameDatabase


class DatabaseTab(QWidget):
    """Вкладка просмотра и редактирования базы данных имён."""

    def __init__(
        self, db: NameDatabase, known_names: dict[NameCategory, set[str]], on_data_changed: Callable[[], None]
    ) -> None:
        super().__init__()
        self._db = db
        self._known_names = known_names
        self._on_data_changed = on_data_changed
        self._current_category = NameCategory.LAST_NAME
        self._setup_ui()
        self._load_data()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Верхняя панель: выбор категории + поиск
        top_row = QHBoxLayout()

        top_row.addWidget(QLabel("Категория:"))
        self._category_combo = QComboBox()
        for cat in NameCategory:
            self._category_combo.addItem(CATEGORY_LABELS[cat], cat)
        self._category_combo.currentIndexChanged.connect(self._on_category_changed)
        top_row.addWidget(self._category_combo)

        top_row.addSpacing(20)

        top_row.addWidget(QLabel("Поиск:"))
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Введите часть значения...")
        self._search_input.textChanged.connect(self._load_data)
        top_row.addWidget(self._search_input, stretch=1)

        layout.addLayout(top_row)

        # Таблица
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["ID", "Значение"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table, stretch=1)

        # Нижняя панель: кнопки
        btn_row = QHBoxLayout()

        self._count_label = QLabel("")
        btn_row.addWidget(self._count_label)

        btn_row.addStretch()

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self._add_entry)
        btn_row.addWidget(add_btn)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self._edit_entry)
        btn_row.addWidget(edit_btn)

        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(self._delete_entry)
        btn_row.addWidget(delete_btn)

        layout.addLayout(btn_row)

    def _on_category_changed(self) -> None:
        self._current_category = self._category_combo.currentData()
        self._load_data()

    def _load_data(self) -> None:
        search = self._search_input.text().strip()
        rows = self._db.list_names(self._current_category, search)

        self._table.setRowCount(len(rows))
        for i, (row_id, value) in enumerate(rows):
            id_item = QTableWidgetItem(str(row_id))
            id_item.setData(Qt.ItemDataRole.UserRole, row_id)
            id_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 0, id_item)
            self._table.setItem(i, 1, QTableWidgetItem(value))

        label = CATEGORY_LABELS[self._current_category]
        self._count_label.setText(f"{label}: {len(rows)} записей")

    def _selected_row(self) -> tuple[int, str] | None:
        items = self._table.selectedItems()
        if not items:
            QMessageBox.warning(self, "Внимание", "Выберите запись в таблице.")
            return None
        row = items[0].row()
        id_item = self._table.item(row, 0)
        value_item = self._table.item(row, 1)
        if id_item is None or value_item is None:
            return None
        row_id: int = id_item.data(Qt.ItemDataRole.UserRole)
        value = value_item.text()
        return row_id, value

    def _sync_known_names(self) -> None:
        """Пересинхронизирует in-memory кеш с БД."""
        for cat in NameCategory:
            self._known_names[cat] = self._db.load_all(cat)
        self._on_data_changed()

    def _add_entry(self) -> None:
        label = CATEGORY_LABELS[self._current_category]
        text, ok = QInputDialog.getText(self, "Добавить запись", f"{label}:")
        if not ok or not text.strip():
            return
        value = text.strip()
        self._db.add_name(self._current_category, value)
        self._sync_known_names()
        self._load_data()

    def _edit_entry(self) -> None:
        sel = self._selected_row()
        if sel is None:
            return
        row_id, old_value = sel
        label = CATEGORY_LABELS[self._current_category]
        text, ok = QInputDialog.getText(self, "Редактировать запись", f"{label}:", text=old_value)
        if not ok or not text.strip():
            return
        new_value = text.strip()
        if new_value == old_value:
            return
        try:
            self._db.update_name(self._current_category, row_id, new_value)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить: {exc}")
            return
        self._sync_known_names()
        self._load_data()

    def _delete_entry(self) -> None:
        sel = self._selected_row()
        if sel is None:
            return
        row_id, value = sel
        answer = QMessageBox.question(
            self, "Подтверждение", f"Удалить «{value}»?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._db.delete_name(self._current_category, row_id)
        self._sync_known_names()
        self._load_data()
