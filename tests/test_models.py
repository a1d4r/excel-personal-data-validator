from excel_personal_data_validator.db import NameCategory
from excel_personal_data_validator.models import EntryDecision, ReviewSummary, UserAction
from excel_personal_data_validator.validator import UnknownEntry


def test_summary_counts():
    entry = UnknownEntry(category=NameCategory.LAST_NAME, value="Тест", row_numbers=(1,))
    decisions = [
        EntryDecision(entry=entry, action=UserAction.ADD_TO_DB),
        EntryDecision(entry=entry, action=UserAction.REPLACE, replacement="Тестов"),
        EntryDecision(entry=entry, action=UserAction.REPLACE, replacement="Тестова"),
        EntryDecision(entry=entry, action=UserAction.SKIP),
    ]
    summary = ReviewSummary(decisions=decisions)
    assert summary.added_count == 1
    assert summary.replaced_count == 2
    assert summary.skipped_count == 1


def test_summary_empty():
    summary = ReviewSummary(decisions=[])
    assert summary.added_count == 0
    assert summary.replaced_count == 0
    assert summary.skipped_count == 0


def test_entry_decision_defaults():
    entry = UnknownEntry(category=NameCategory.FIRST_NAME, value="Тест", row_numbers=(1,))
    decision = EntryDecision(entry=entry, action=UserAction.SKIP)
    assert decision.replacement is None
