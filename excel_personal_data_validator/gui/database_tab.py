from collections.abc import Callable

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPersistentModelIndex, Qt
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
    QTableView,
    QVBoxLayout,
    QWidget,
)

from excel_personal_data_validator.db import CATEGORY_LABELS, NameCategory, NameDatabase

_HEADERS = ["ID", "Значение"]
_DEFAULT_PARENT = QModelIndex()


class _NameTableModel(QAbstractTableModel):
    """Модель данных для таблицы имён. Виртуализирует отрисовку через QTableView."""

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[tuple[int, str]] = []

    def set_data(self, rows: list[tuple[int, str]]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rowCount(self, parent: QModelIndex | QPersistentModelIndex = _DEFAULT_PARENT) -> int:  # noqa: ARG002
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | QPersistentModelIndex = _DEFAULT_PARENT) -> int:  # noqa: ARG002
        return 2

    def data(self, index: QModelIndex | QPersistentModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None
        row_id, value = self._rows[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return str(row_id) if index.column() == 0 else value
        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() == 0:
            return Qt.AlignmentFlag.AlignCenter
        if role == Qt.ItemDataRole.UserRole:
            return row_id
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return _HEADERS[section]
        return None

    def row_at(self, index: int) -> tuple[int, str]:
        return self._rows[index]


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
        self._model = _NameTableModel()
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

        # Таблица (QTableView + модель для виртуализации)
        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
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
        self._model.set_data(rows)

        label = CATEGORY_LABELS[self._current_category]
        self._count_label.setText(f"{label}: {len(rows)} записей")

    def _selected_row(self) -> tuple[int, str] | None:
        indexes = self._table.selectionModel().selectedRows()
        if not indexes:
            QMessageBox.warning(self, "Внимание", "Выберите запись в таблице.")
            return None
        return self._model.row_at(indexes[0].row())

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
