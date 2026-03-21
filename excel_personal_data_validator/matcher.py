import difflib


def find_similar(value: str, known_values: set[str], max_results: int = 5, cutoff: float = 0.6) -> list[str]:
    """Ищет похожие значения в базе с помощью нечёткого сравнения.

    Использует difflib.get_close_matches из стандартной библиотеки.
    Возвращает список похожих значений, отсортированный по убыванию сходства.
    """
    matches = difflib.get_close_matches(value.lower(), list(known_values), n=max_results, cutoff=cutoff)
    return [m.title() for m in matches]
