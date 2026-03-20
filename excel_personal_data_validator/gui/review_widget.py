from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from excel_personal_data_validator.db import CATEGORY_LABELS, NameCategory, NameDatabase
from excel_personal_data_validator.matcher import find_similar
from excel_personal_data_validator.models import EntryDecision, ReviewSummary, UserAction
from excel_personal_data_validator.validator import UnknownEntry

_ACTION_CUSTOM = "custom"
_ACTION_ADD_TO_DB = "add_to_db"
_ACTION_SKIP = "skip"


class ReviewWidget(QWidget):
    """Виджет интерактивного просмотра неизвестных значений."""

    def __init__(
        self,
        unknown_entries: list[UnknownEntry],
        known_names: dict[NameCategory, set[str]],
        db: NameDatabase,
        on_complete: Callable[[ReviewSummary], None],
        on_cancel: Callable[[], None],
    ) -> None:
        super().__init__()
        self._entries = unknown_entries
        self._known_names = known_names
        self._db = db
        self._on_complete = on_complete
        self._on_cancel = on_cancel

        self._decisions: list[EntryDecision | None] = [None] * len(unknown_entries)
        self._current_index = 0

        self._setup_ui()
        self._setup_shortcuts()
        self._show_entry(0)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self._total_label = QLabel()
        self._position_label = QLabel()
        self._position_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        header.addWidget(self._total_label)
        header.addStretch()
        header.addWidget(self._position_label)
        layout.addLayout(header)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line)

        # Информация о текущем значении
        info_layout = QVBoxLayout()
        self._category_label = QLabel()
        self._value_label = QLabel()
        self._value_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self._rows_label = QLabel()
        info_layout.addWidget(self._category_label)
        info_layout.addWidget(self._value_label)
        info_layout.addWidget(self._rows_label)
        layout.addLayout(info_layout)

        layout.addSpacing(10)

        # Похожие в базе + действия
        self._options_container = QVBoxLayout()
        self._similar_label = QLabel("Похожие в базе:")
        layout.addWidget(self._similar_label)

        self._radio_group = QButtonGroup(self)
        self._radios_widget = QWidget()
        self._radios_layout = QVBoxLayout(self._radios_widget)
        self._radios_layout.setContentsMargins(20, 0, 0, 0)
        layout.addWidget(self._radios_widget)

        # Поле для своего значения
        custom_row = QHBoxLayout()
        self._custom_radio = QRadioButton("Ввести своё:")
        self._custom_input = QLineEdit()
        self._custom_input.setEnabled(False)
        self._custom_radio.toggled.connect(self._custom_input.setEnabled)
        custom_row.addWidget(self._custom_radio)
        custom_row.addWidget(self._custom_input, stretch=1)
        layout.addLayout(custom_row)

        # Добавить в базу / Пропустить
        self._add_db_radio = QRadioButton("Добавить в базу")
        self._skip_radio = QRadioButton("Пропустить")
        layout.addWidget(self._add_db_radio)
        layout.addWidget(self._skip_radio)

        layout.addSpacing(10)

        # Кнопки навигации
        nav_row = QHBoxLayout()
        self._cancel_btn = QPushButton("Отмена")
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._back_btn = QPushButton("\u25c0 Назад")
        self._back_btn.clicked.connect(self._go_back)
        self._next_btn = QPushButton("Применить и далее \u25b6")
        self._next_btn.setDefault(True)
        self._next_btn.clicked.connect(self._go_next)
        nav_row.addWidget(self._cancel_btn)
        nav_row.addStretch()
        nav_row.addWidget(self._back_btn)
        nav_row.addWidget(self._next_btn)
        layout.addLayout(nav_row)

        # Разделитель
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line2)

        # Прогресс
        progress_row = QHBoxLayout()
        self._replaced_label = QLabel("Исправлено: 0")
        self._added_label = QLabel("Добавлено: 0")
        self._skipped_label = QLabel("Пропущено: 0")
        progress_row.addWidget(self._replaced_label)
        progress_row.addSpacing(20)
        progress_row.addWidget(self._added_label)
        progress_row.addSpacing(20)
        progress_row.addWidget(self._skipped_label)
        progress_row.addStretch()
        layout.addLayout(progress_row)

        layout.addStretch()

    def _setup_shortcuts(self) -> None:
        for i in range(1, 6):
            shortcut = QShortcut(str(i), self)
            shortcut.activated.connect(lambda idx=i: self._select_radio(idx))

    def _select_radio(self, index: int) -> None:
        """Выбирает radio-кнопку по номеру (1-based)."""
        buttons = self._radio_group.buttons()
        if 1 <= index <= len(buttons):
            buttons[index - 1].setChecked(True)

    def _show_entry(self, index: int) -> None:
        self._current_index = index
        entry = self._entries[index]

        self._total_label.setText(f"Неизвестных значений: {len(self._entries)}")
        self._position_label.setText(f"[{index + 1} / {len(self._entries)}]")

        label = CATEGORY_LABELS.get(entry.category, entry.category.value)
        self._category_label.setText(f"Категория: {label}")
        self._value_label.setText(f"'{entry.value}'")
        self._rows_label.setText(f"Строки: {', '.join(str(r) for r in entry.row_numbers)}")

        similar = self._rebuild_similar_radios(entry)
        self._current_similar = similar

        # Восстанавливаем предыдущее решение если есть
        prev = self._decisions[index]
        if prev is not None:
            self._restore_decision(prev, similar)
        elif similar:
            self._radio_group.buttons()[0].setChecked(True)
        else:
            self._skip_radio.setChecked(True)

        self._custom_input.clear()
        if prev and prev.action == UserAction.REPLACE and prev.replacement not in similar:
            self._custom_input.setText(prev.replacement or "")

        # Обновляем кнопки
        self._back_btn.setEnabled(index > 0)
        is_last = index == len(self._entries) - 1
        self._next_btn.setText("Завершить" if is_last else "Применить и далее \u25b6")

        self._update_progress()

    def _rebuild_similar_radios(self, entry: UnknownEntry) -> list[str]:
        """Удаляет старые radio-кнопки похожих и создаёт новые."""
        permanent = {self._custom_radio, self._add_db_radio, self._skip_radio}
        for btn in list(self._radio_group.buttons()):
            if btn not in permanent:
                self._radio_group.removeButton(btn)
                btn.deleteLater()

        while self._radios_layout.count():
            item = self._radios_layout.takeAt(0)
            if item is not None:
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

        similar = find_similar(entry.value, self._known_names.get(entry.category, set()))

        if similar:
            self._similar_label.show()
            for name in similar:
                radio = QRadioButton(name)
                self._radios_layout.addWidget(radio)
                self._radio_group.addButton(radio)
        else:
            self._similar_label.hide()

        self._radio_group.addButton(self._custom_radio)
        self._radio_group.addButton(self._add_db_radio)
        self._radio_group.addButton(self._skip_radio)

        return similar

    def _restore_decision(self, decision: EntryDecision, similar: list[str]) -> None:
        if decision.action == UserAction.REPLACE and decision.replacement in similar:
            idx = similar.index(decision.replacement)
            buttons = [
                b
                for b in self._radio_group.buttons()
                if b not in (self._custom_radio, self._add_db_radio, self._skip_radio)
            ]
            if idx < len(buttons):
                buttons[idx].setChecked(True)
        elif decision.action == UserAction.REPLACE:
            self._custom_radio.setChecked(True)
        elif decision.action == UserAction.ADD_TO_DB:
            self._add_db_radio.setChecked(True)
        else:
            self._skip_radio.setChecked(True)

    def _build_decision(self) -> EntryDecision | None:
        entry = self._entries[self._current_index]
        checked = self._radio_group.checkedButton()

        if checked is None:
            QMessageBox.warning(self, "Ошибка", "Выберите действие.")
            return None

        if checked is self._skip_radio:
            return EntryDecision(entry=entry, action=UserAction.SKIP)

        if checked is self._add_db_radio:
            self._db.add_name(entry.category, entry.value)
            self._known_names[entry.category].add(entry.value.lower())
            return EntryDecision(entry=entry, action=UserAction.ADD_TO_DB)

        if checked is self._custom_radio:
            custom = self._custom_input.text().strip()
            if not custom:
                QMessageBox.warning(self, "Ошибка", "Введите значение.")
                return None
            return EntryDecision(entry=entry, action=UserAction.REPLACE, replacement=custom)

        # Один из похожих
        return EntryDecision(entry=entry, action=UserAction.REPLACE, replacement=checked.text())

    def _go_next(self) -> None:
        decision = self._build_decision()
        if decision is None:
            return

        self._decisions[self._current_index] = decision

        if self._current_index < len(self._entries) - 1:
            self._show_entry(self._current_index + 1)
        else:
            # Завершение
            final_decisions = [d for d in self._decisions if d is not None]
            summary = ReviewSummary(decisions=final_decisions)
            self._on_complete(summary)

    def _go_back(self) -> None:
        if self._current_index > 0:
            # Сохраняем текущее решение
            decision = self._build_decision()
            if decision is not None:
                self._decisions[self._current_index] = decision
            self._show_entry(self._current_index - 1)

    def _update_progress(self) -> None:
        replaced = sum(1 for d in self._decisions if d and d.action == UserAction.REPLACE)
        added = sum(1 for d in self._decisions if d and d.action == UserAction.ADD_TO_DB)
        skipped = sum(1 for d in self._decisions if d and d.action == UserAction.SKIP)
        self._replaced_label.setText(f"Исправлено: {replaced}")
        self._added_label.setText(f"Добавлено: {added}")
        self._skipped_label.setText(f"Пропущено: {skipped}")
