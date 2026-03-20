import dataclasses

from enum import StrEnum

from excel_personal_data_validator.validator import UnknownEntry


class UserAction(StrEnum):
    """Действие пользователя при обнаружении неизвестного значения."""

    ADD_TO_DB = "add"
    REPLACE = "replace"
    SKIP = "skip"


@dataclasses.dataclass
class EntryDecision:
    """Решение пользователя по конкретному неизвестному значению."""

    entry: UnknownEntry
    action: UserAction
    replacement: str | None = None


@dataclasses.dataclass
class ReviewSummary:
    """Итоги интерактивного обзора."""

    decisions: list[EntryDecision]

    @property
    def added_count(self) -> int:
        return sum(1 for d in self.decisions if d.action == UserAction.ADD_TO_DB)

    @property
    def replaced_count(self) -> int:
        return sum(1 for d in self.decisions if d.action == UserAction.REPLACE)

    @property
    def skipped_count(self) -> int:
        return sum(1 for d in self.decisions if d.action == UserAction.SKIP)
