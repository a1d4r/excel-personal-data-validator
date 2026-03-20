from pathlib import Path

from openpyxl import Workbook
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from excel_personal_data_validator.db import NameCategory, NameDatabase
from excel_personal_data_validator.gui.database_tab import DatabaseTab
from excel_personal_data_validator.gui.import_tab import ImportTab
from excel_personal_data_validator.gui.review_widget import ReviewWidget
from excel_personal_data_validator.gui.validate_tab import ValidateTab
from excel_personal_data_validator.models import ReviewSummary, UserAction
from excel_personal_data_validator.validator import UnknownEntry


def _make_db(tmp_path: Path) -> tuple[NameDatabase, dict[NameCategory, set[str]]]:
    """Создаёт тестовую БД с именами."""
    db = NameDatabase(tmp_path / "test.db")
    db.initialize()
    db.add_names_bulk(NameCategory.LAST_NAME, ["Иванов", "Петров", "Сидоров", "Иванова"])
    db.add_names_bulk(NameCategory.FIRST_NAME, ["Иван", "Пётр", "Мария", "Алексей"])
    db.add_names_bulk(NameCategory.PATRONYMIC, ["Иванович", "Петрович", "Сергеевич"])
    known = {cat: db.load_all(cat) for cat in NameCategory}
    return db, known


def _make_entries() -> list[UnknownEntry]:
    """Создаёт тестовые неизвестные записи."""
    return [
        UnknownEntry(category=NameCategory.LAST_NAME, value="Ивано", row_numbers=(2, 5)),
        UnknownEntry(category=NameCategory.FIRST_NAME, value="Алексй", row_numbers=(3,)),
        UnknownEntry(category=NameCategory.PATRONYMIC, value="Хзотч", row_numbers=(4,)),
    ]


# ============================================================
# ReviewWidget tests
# ============================================================


class TestReviewWidget:
    def test_initial_state(self, qtbot, tmp_path):
        """Виджет показывает первую запись при создании."""
        db, known = _make_db(tmp_path)
        entries = _make_entries()

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        assert widget._current_index == 0
        assert widget._position_label.text() == "[1 / 3]"
        assert "Ивано" in widget._value_label.text()
        assert "Фамилия" in widget._category_label.text()
        assert widget._back_btn.isEnabled() is False

    def test_navigate_next(self, qtbot, tmp_path):
        """Кнопка 'Далее' переходит к следующей записи."""
        db, known = _make_db(tmp_path)
        entries = _make_entries()

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        widget._skip_radio.setChecked(True)
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)

        assert widget._current_index == 1
        assert widget._position_label.text() == "[2 / 3]"
        assert "Алексй" in widget._value_label.text()
        assert widget._back_btn.isEnabled() is True

    def test_navigate_back(self, qtbot, tmp_path):
        """Кнопка 'Назад' возвращает к предыдущей записи."""
        db, known = _make_db(tmp_path)
        entries = _make_entries()

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        # Идём вперёд
        widget._skip_radio.setChecked(True)
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)
        assert widget._current_index == 1

        # Идём назад
        widget._skip_radio.setChecked(True)
        qtbot.mouseClick(widget._back_btn, Qt.MouseButton.LeftButton)
        assert widget._current_index == 0
        assert widget._position_label.text() == "[1 / 3]"

    def test_skip_action(self, qtbot, tmp_path):
        """Пропуск записывает решение SKIP."""
        db, known = _make_db(tmp_path)
        entries = _make_entries()

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        widget._skip_radio.setChecked(True)
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)

        assert widget._decisions[0] is not None
        assert widget._decisions[0].action == UserAction.SKIP

    def test_replace_with_similar(self, qtbot, tmp_path):
        """Выбор похожего значения записывает решение REPLACE."""
        db, known = _make_db(tmp_path)
        entries = _make_entries()

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        # Первая запись "Ивано" — должны быть похожие (Иванов, Иванова)
        similar_buttons = [
            b
            for b in widget._radio_group.buttons()
            if b not in (widget._custom_radio, widget._add_db_radio, widget._skip_radio)
        ]
        assert len(similar_buttons) > 0

        similar_buttons[0].setChecked(True)
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)

        assert widget._decisions[0] is not None
        assert widget._decisions[0].action == UserAction.REPLACE
        assert widget._decisions[0].replacement is not None

    def test_add_to_db(self, qtbot, tmp_path):
        """'Добавить в базу' сохраняет в БД и обновляет known_names."""
        db, known = _make_db(tmp_path)
        entries = [UnknownEntry(category=NameCategory.LAST_NAME, value="Новиков", row_numbers=(2,))]

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        widget._add_db_radio.setChecked(True)
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)

        assert "новиков" in known[NameCategory.LAST_NAME]
        assert "новиков" in db.load_all(NameCategory.LAST_NAME)

    def test_custom_value(self, qtbot, tmp_path):
        """Ввод своего значения записывает REPLACE с пользовательским текстом."""
        db, known = _make_db(tmp_path)
        entries = [
            UnknownEntry(category=NameCategory.LAST_NAME, value="Хзфам", row_numbers=(2,)),
            UnknownEntry(category=NameCategory.LAST_NAME, value="Хзфам2", row_numbers=(3,)),
        ]

        results: list[ReviewSummary] = []
        widget = ReviewWidget(entries, known, db, on_complete=results.append, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        widget._custom_radio.setChecked(True)
        widget._custom_input.setText("Правильная")
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)

        assert widget._decisions[0] is not None
        assert widget._decisions[0].action == UserAction.REPLACE
        assert widget._decisions[0].replacement == "Правильная"

    def test_complete_callback(self, qtbot, tmp_path):
        """Завершение просмотра вызывает on_complete с ReviewSummary."""
        db, known = _make_db(tmp_path)
        entries = [UnknownEntry(category=NameCategory.LAST_NAME, value="Хзфам", row_numbers=(2,))]

        results: list[ReviewSummary] = []
        widget = ReviewWidget(entries, known, db, on_complete=results.append, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        widget._skip_radio.setChecked(True)
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)

        assert len(results) == 1
        assert results[0].skipped_count == 1

    def test_progress_counters(self, qtbot, tmp_path):
        """Счётчики прогресса обновляются после каждого решения."""
        db, known = _make_db(tmp_path)
        entries = _make_entries()

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        # Пропускаем первую запись
        widget._skip_radio.setChecked(True)
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)

        assert "Пропущено: 1" in widget._skipped_label.text()

    def test_last_entry_shows_finish_button(self, qtbot, tmp_path):
        """На последней записи кнопка показывает 'Завершить'."""
        db, known = _make_db(tmp_path)
        entries = [UnknownEntry(category=NameCategory.LAST_NAME, value="Хзфам", row_numbers=(2,))]

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        assert "Завершить" in widget._next_btn.text()

    def test_action_buttons_exist_after_navigation(self, qtbot, tmp_path):
        """Постоянные radio-кнопки не исчезают при переходе между записями."""
        db, known = _make_db(tmp_path)
        entries = _make_entries()

        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: None)
        qtbot.addWidget(widget)

        widget._skip_radio.setChecked(True)
        qtbot.mouseClick(widget._next_btn, Qt.MouseButton.LeftButton)

        # После перехода постоянные кнопки должны быть живы и видны
        assert not widget._custom_radio.isHidden()
        assert not widget._add_db_radio.isHidden()
        assert not widget._skip_radio.isHidden()

    def test_cancel(self, qtbot, tmp_path):
        """Кнопка 'Отмена' вызывает on_cancel."""
        db, known = _make_db(tmp_path)
        entries = _make_entries()

        cancelled = []
        widget = ReviewWidget(entries, known, db, on_complete=lambda _: None, on_cancel=lambda: cancelled.append(True))
        qtbot.addWidget(widget)

        qtbot.mouseClick(widget._cancel_btn, Qt.MouseButton.LeftButton)
        assert len(cancelled) == 1


# ============================================================
# ValidateTab tests
# ============================================================


class TestValidateTab:
    def test_form_fields_exist(self, qtbot, tmp_path):
        """Форма содержит все необходимые поля."""
        db, known = _make_db(tmp_path)

        widget = ValidateTab(db=db, known_names=known, db_path=tmp_path / "test.db")
        qtbot.addWidget(widget)

        assert widget._file_input is not None
        assert widget._last_name_col.text() == "A"
        assert widget._first_name_col.text() == "B"
        assert widget._patronymic_col.text() == "C"
        assert widget._start_row_input.text() == "2"

    def test_build_config_no_file(self, qtbot, tmp_path, monkeypatch):
        """_build_config возвращает None если файл не выбран."""
        db, known = _make_db(tmp_path)

        widget = ValidateTab(db=db, known_names=known, db_path=tmp_path / "test.db")
        qtbot.addWidget(widget)

        # Подавляем QMessageBox
        monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *args, **kwargs: None)

        result = widget._build_config()
        assert result is None

    def test_build_config_valid(self, qtbot, tmp_path):
        """_build_config строит корректный AppConfig."""
        db, known = _make_db(tmp_path)

        xlsx = tmp_path / "test.xlsx"
        wb = Workbook()
        wb.save(xlsx)
        wb.close()

        widget = ValidateTab(db=db, known_names=known, db_path=tmp_path / "test.db")
        qtbot.addWidget(widget)

        widget._file_input.setReadOnly(False)
        widget._file_input.setText(str(xlsx))
        widget._file_input.setReadOnly(True)

        config = widget._build_config()
        assert config is not None
        assert config.excel_path == xlsx
        assert config.last_name_column == "A"
        assert config.start_row == 2


# ============================================================
# ImportTab tests
# ============================================================


class TestImportTab:
    def test_form_fields_exist(self, qtbot, tmp_path):
        """Форма содержит поля для всех трёх категорий."""
        db, known = _make_db(tmp_path)

        widget = ImportTab(db=db, known_names=known, on_import_done=lambda: None)
        qtbot.addWidget(widget)

        assert NameCategory.LAST_NAME in widget._file_inputs
        assert NameCategory.FIRST_NAME in widget._file_inputs
        assert NameCategory.PATRONYMIC in widget._file_inputs

    def test_import_with_file(self, qtbot, tmp_path, monkeypatch):
        """Импорт из файла добавляет данные в БД."""
        db, known = _make_db(tmp_path)
        done_called = []

        widget = ImportTab(db=db, known_names=known, on_import_done=lambda: done_called.append(True))
        qtbot.addWidget(widget)

        # Создаём тестовый файл
        names_file = tmp_path / "names.txt"
        names_file.write_text("Козлов\nМедведев\n", encoding="utf-8")

        widget._file_inputs[NameCategory.LAST_NAME].setReadOnly(False)
        widget._file_inputs[NameCategory.LAST_NAME].setText(str(names_file))
        widget._file_inputs[NameCategory.LAST_NAME].setReadOnly(True)

        # Подавляем QMessageBox.information
        monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.information", lambda *args, **kwargs: None)

        widget._run_import()

        assert "козлов" in known[NameCategory.LAST_NAME]
        assert "медведев" in known[NameCategory.LAST_NAME]
        assert len(done_called) == 1

    def test_import_no_files_warns(self, qtbot, tmp_path, monkeypatch):
        """Импорт без файлов показывает предупреждение."""
        db, known = _make_db(tmp_path)
        warned = []

        widget = ImportTab(db=db, known_names=known, on_import_done=lambda: None)
        qtbot.addWidget(widget)

        monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *args, **kwargs: warned.append(True))

        widget._run_import()
        assert len(warned) == 1


# ============================================================
# DatabaseTab tests
# ============================================================


class TestDatabaseTab:
    def test_initial_load(self, qtbot, tmp_path):
        """Таблица загружает данные при создании."""
        db, known = _make_db(tmp_path)
        changed = []

        widget = DatabaseTab(db=db, known_names=known, on_data_changed=lambda: changed.append(True))
        qtbot.addWidget(widget)

        # По умолчанию выбрана категория LAST_NAME
        assert widget._model.rowCount() == len(db.list_names(NameCategory.LAST_NAME))
        assert "Фамилия" in widget._count_label.text()

    def test_category_switch(self, qtbot, tmp_path):
        """Переключение категории перезагружает данные."""
        db, known = _make_db(tmp_path)

        widget = DatabaseTab(db=db, known_names=known, on_data_changed=lambda: None)
        qtbot.addWidget(widget)

        # Переключаемся на «Имя» (индекс 1)
        widget._category_combo.setCurrentIndex(1)
        assert widget._model.rowCount() == len(db.list_names(NameCategory.FIRST_NAME))
        assert "Имя" in widget._count_label.text()

    def test_search_filters_data(self, qtbot, tmp_path):
        """Поиск фильтрует записи по подстроке."""
        db, known = _make_db(tmp_path)

        widget = DatabaseTab(db=db, known_names=known, on_data_changed=lambda: None)
        qtbot.addWidget(widget)

        total_before = widget._model.rowCount()
        widget._search_input.setText("Иван")
        filtered = widget._model.rowCount()
        assert filtered < total_before
        assert filtered > 0

    def test_add_entry(self, qtbot, tmp_path, monkeypatch):
        """Добавление записи через диалог."""
        db, known = _make_db(tmp_path)
        changed = []

        widget = DatabaseTab(db=db, known_names=known, on_data_changed=lambda: changed.append(True))
        qtbot.addWidget(widget)

        count_before = widget._model.rowCount()
        monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", lambda *args, **kwargs: ("Козлов", True))

        widget._add_entry()

        assert widget._model.rowCount() == count_before + 1
        assert "козлов" in known[NameCategory.LAST_NAME]
        assert len(changed) == 1

    def test_edit_entry(self, qtbot, tmp_path, monkeypatch):
        """Редактирование выбранной записи."""
        db, known = _make_db(tmp_path)

        widget = DatabaseTab(db=db, known_names=known, on_data_changed=lambda: None)
        qtbot.addWidget(widget)

        # Выбираем первую строку
        widget._table.selectRow(0)
        old_value = widget._model.row_at(0)[1]

        monkeypatch.setattr("PySide6.QtWidgets.QInputDialog.getText", lambda *args, **kwargs: ("Новиков", True))

        widget._edit_entry()

        # Проверяем что старое значение заменено
        assert "новиков" in known[NameCategory.LAST_NAME]
        assert old_value.lower() not in known[NameCategory.LAST_NAME]

    def test_delete_entry(self, qtbot, tmp_path, monkeypatch):
        """Удаление записи с подтверждением."""
        db, known = _make_db(tmp_path)

        widget = DatabaseTab(db=db, known_names=known, on_data_changed=lambda: None)
        qtbot.addWidget(widget)

        count_before = widget._model.rowCount()
        widget._table.selectRow(0)
        deleted_value = widget._model.row_at(0)[1]

        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes
        )

        widget._delete_entry()

        assert widget._model.rowCount() == count_before - 1
        assert deleted_value.lower() not in known[NameCategory.LAST_NAME]

    def test_delete_cancelled(self, qtbot, tmp_path, monkeypatch):
        """Отмена удаления не изменяет данные."""
        db, known = _make_db(tmp_path)

        widget = DatabaseTab(db=db, known_names=known, on_data_changed=lambda: None)
        qtbot.addWidget(widget)

        count_before = widget._model.rowCount()
        widget._table.selectRow(0)

        monkeypatch.setattr(
            "PySide6.QtWidgets.QMessageBox.question", lambda *args, **kwargs: QMessageBox.StandardButton.No
        )

        widget._delete_entry()

        assert widget._model.rowCount() == count_before

    def test_no_selection_warns(self, qtbot, tmp_path, monkeypatch):
        """Попытка редактирования/удаления без выбора показывает предупреждение."""
        db, known = _make_db(tmp_path)
        warned = []

        widget = DatabaseTab(db=db, known_names=known, on_data_changed=lambda: None)
        qtbot.addWidget(widget)

        monkeypatch.setattr("PySide6.QtWidgets.QMessageBox.warning", lambda *args, **kwargs: warned.append(True))

        widget._edit_entry()
        assert len(warned) == 1

        widget._delete_entry()
        assert len(warned) == 2
