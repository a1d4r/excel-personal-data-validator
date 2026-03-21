from excel_personal_data_validator.matcher import find_similar


def test_find_similar_basic():
    known = {"иванов", "иванова", "петров", "сидоров"}
    result = find_similar("ивано", known)
    assert len(result) > 0
    assert "Иванов" in result


def test_find_similar_no_match():
    known = {"иванов", "петров"}
    result = find_similar("абвгд", known)
    assert len(result) == 0


def test_find_similar_exact_match():
    known = {"иванов", "петров"}
    result = find_similar("иванов", known)
    assert "Иванов" in result


def test_find_similar_max_results():
    known = {f"тест{i}" for i in range(100)}
    result = find_similar("тест1", known, max_results=3)
    assert len(result) <= 3


def test_find_similar_empty_known():
    result = find_similar("иванов", set())
    assert result == []
