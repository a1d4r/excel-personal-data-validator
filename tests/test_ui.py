from unittest import mock

from excel_personal_data_validator.db import NameCategory, NameDatabase
from excel_personal_data_validator.ui import ReviewSummary, UserAction, run_interactive_review
from excel_personal_data_validator.validator import UnknownEntry


def test_add_to_db(tmp_db: NameDatabase, known_names):
    entries = [UnknownEntry(category=NameCategory.LAST_NAME, value="Новиков", row_numbers=(2,))]
    # Пользователь выбирает "Добавить в базу" (последний - 1 вариант)
    # Если нет похожих: [1] Ввести своё, [2] Добавить, [3] Пропустить → выбор 2
    with mock.patch("builtins.input", return_value="2"):
        summary = run_interactive_review(entries, known_names, tmp_db)

    assert len(summary.decisions) == 1
    assert summary.decisions[0].action == UserAction.ADD_TO_DB
    assert "новиков" in known_names[NameCategory.LAST_NAME]


def test_skip(tmp_db: NameDatabase, known_names):
    entries = [UnknownEntry(category=NameCategory.FIRST_NAME, value="Хзчто", row_numbers=(3,))]
    # Если нет похожих: [1] Ввести своё, [2] Добавить, [3] Пропустить → выбор 3
    with mock.patch("builtins.input", return_value="3"):
        summary = run_interactive_review(entries, known_names, tmp_db)

    assert summary.decisions[0].action == UserAction.SKIP


def test_replace_with_similar(tmp_db: NameDatabase, known_names):
    entries = [UnknownEntry(category=NameCategory.LAST_NAME, value="Иваноо", row_numbers=(2,))]
    # Выбираем первый похожий вариант
    with mock.patch("builtins.input", return_value="1"):
        summary = run_interactive_review(entries, known_names, tmp_db)

    assert summary.decisions[0].action == UserAction.REPLACE
    assert summary.decisions[0].replacement is not None


def test_replace_with_custom_value(tmp_db: NameDatabase, known_names):
    entries = [UnknownEntry(category=NameCategory.LAST_NAME, value="Хзфамилия", row_numbers=(2,))]
    # Нет похожих → [1] Ввести своё, [2] Добавить, [3] Пропустить
    # Выбор 1, затем ввод значения
    with mock.patch("builtins.input", side_effect=["1", "Правильная"]):
        summary = run_interactive_review(entries, known_names, tmp_db)

    assert summary.decisions[0].action == UserAction.REPLACE
    assert summary.decisions[0].replacement == "Правильная"


def test_summary_counts():
    decisions = [
        mock.Mock(action=UserAction.ADD_TO_DB),
        mock.Mock(action=UserAction.REPLACE),
        mock.Mock(action=UserAction.REPLACE),
        mock.Mock(action=UserAction.SKIP),
    ]
    summary = ReviewSummary(decisions=decisions)
    assert summary.added_count == 1
    assert summary.replaced_count == 2
    assert summary.skipped_count == 1
