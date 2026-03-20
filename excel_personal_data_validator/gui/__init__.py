import sys

from PySide6.QtWidgets import QApplication

from excel_personal_data_validator.gui.app import MainWindow


def launch_gui() -> None:
    """Запускает графический интерфейс приложения."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
