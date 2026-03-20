import dataclasses

from enum import StrEnum

from excel_personal_data_validator.db import CATEGORY_LABELS, NameCategory, NameDatabase
from excel_personal_data_validator.matcher import find_similar
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


def run_interactive_review(
    unknown_entries: list[UnknownEntry], known_names: dict[NameCategory, set[str]], db: NameDatabase
) -> ReviewSummary:
    """Интерактивный обзор неизвестных значений.

    Для каждого значения показывает похожие из БД и предлагает действия.
    """
    decisions: list[EntryDecision] = []
    total = len(unknown_entries)

    print(f"\n{'=' * 40}")
    print(f"Найдено неизвестных значений: {total}")
    print(f"{'=' * 40}")

    for idx, entry in enumerate(unknown_entries, start=1):
        label = CATEGORY_LABELS.get(entry.category, entry.category.value)
        rows_str = ", ".join(str(r) for r in entry.row_numbers)

        print(f"\n[{idx}/{total}] {label} '{entry.value}' (строки: {rows_str})")

        similar = find_similar(entry.value, known_names.get(entry.category, set()))

        options: list[str] = []
        for i, s in enumerate(similar, start=1):
            options.append(f"  [{i}] {s}")

        next_num = len(similar) + 1
        options.append(f"  [{next_num}] Ввести своё значение")
        next_num += 1
        options.append(f"  [{next_num}] Добавить '{entry.value}' в базу")
        next_num += 1
        options.append(f"  [{next_num}] Пропустить")

        if similar:
            print("Похожие в базе:")
        print("\n".join(options))

        decision = _get_user_choice(entry, similar, db, known_names)
        decisions.append(decision)

    return ReviewSummary(decisions=decisions)


def print_summary(summary: ReviewSummary, output_path: str | None = None) -> None:
    """Выводит итоговую сводку."""
    print(f"\n{'=' * 40}")
    print("Итого:")
    if summary.replaced_count:
        print(f"  Исправлено: {summary.replaced_count}")
    if summary.added_count:
        print(f"  Добавлено в базу: {summary.added_count}")
    if summary.skipped_count:
        print(f"  Пропущено: {summary.skipped_count}")
    if output_path:
        print(f"  Результат сохранён: {output_path}")
    print(f"{'=' * 40}")


def _get_user_choice(
    entry: UnknownEntry, similar: list[str], db: NameDatabase, known_names: dict[NameCategory, set[str]]
) -> EntryDecision:
    """Запрашивает выбор пользователя и возвращает решение."""
    total_options = len(similar) + 3  # similar + ввести своё + добавить в БД + пропустить

    while True:
        raw = input("Выбор: ").strip()
        if not raw.isdigit():
            print(f"Введите число от 1 до {total_options}")
            continue

        choice = int(raw)
        if choice < 1 or choice > total_options:
            print(f"Введите число от 1 до {total_options}")
            continue

        # Выбрана похожая из БД
        if choice <= len(similar):
            replacement = similar[choice - 1]
            print(f"✓ Заменено на '{replacement}' в строках: {', '.join(str(r) for r in entry.row_numbers)}")
            return EntryDecision(entry=entry, action=UserAction.REPLACE, replacement=replacement)

        # Ввести своё значение
        if choice == len(similar) + 1:
            custom = input("Введите правильное значение: ").strip()
            if not custom:
                print("Значение не может быть пустым")
                continue
            print(f"✓ Заменено на '{custom}' в строках: {', '.join(str(r) for r in entry.row_numbers)}")
            return EntryDecision(entry=entry, action=UserAction.REPLACE, replacement=custom)

        # Добавить в БД
        if choice == len(similar) + 2:
            db.add_name(entry.category, entry.value)
            known_names[entry.category].add(entry.value.lower())
            print(f"✓ '{entry.value}' добавлено в базу")
            return EntryDecision(entry=entry, action=UserAction.ADD_TO_DB)

        # Пропустить
        print("→ Пропущено")
        return EntryDecision(entry=entry, action=UserAction.SKIP)
