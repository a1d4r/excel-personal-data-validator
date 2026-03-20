from pathlib import Path

from openpyxl import load_workbook


def save_corrected_excel(
    source_path: Path, output_path: Path, corrections: dict[tuple[int, str], str], sheet_name: str | None = None
) -> None:
    """Сохраняет исправленную копию Excel-файла.

    Args:
        source_path: путь к исходному файлу.
        output_path: путь для сохранения копии.
        corrections: словарь (номер_строки, буква_столбца) -> новое_значение.
        sheet_name: имя листа (None = активный лист).
    """
    if not corrections:
        return

    wb = load_workbook(source_path)

    if sheet_name:
        ws = wb[sheet_name]
    else:
        ws = wb.active
        if ws is None:
            wb.close()
            msg = f"В файле '{source_path}' нет активного листа"
            raise ValueError(msg)

    for (row_number, column_letter), new_value in corrections.items():
        cell_ref = f"{column_letter}{row_number}"
        ws[cell_ref] = new_value

    wb.save(output_path)
    wb.close()
