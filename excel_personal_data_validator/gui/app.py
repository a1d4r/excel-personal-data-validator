from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMainWindow, QStatusBar, QTabWidget

from excel_personal_data_validator.db import NameCategory, NameDatabase
from excel_personal_data_validator.gui.database_tab import DatabaseTab
from excel_personal_data_validator.gui.import_tab import ImportTab
from excel_personal_data_validator.gui.validate_tab import ValidateTab
from excel_personal_data_validator.paths import get_db_path

_WINDOW_TITLE = "Проверка ФИО в Excel"
_MIN_WIDTH = 850
_MIN_HEIGHT = 620


class MainWindow(QMainWindow):
    """Главное окно приложения."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(_WINDOW_TITLE)
        self.setMinimumSize(_MIN_WIDTH, _MIN_HEIGHT)
        self.resize(_MIN_WIDTH, _MIN_HEIGHT)

        self._db_path = get_db_path()
        self._db = NameDatabase(self._db_path)
        self._db.initialize()
        self._known_names: dict[NameCategory, set[str]] = {cat: self._db.load_all(cat) for cat in NameCategory}

        self._setup_ui()
        self._update_status_bar()

    def _setup_ui(self) -> None:
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        self._validate_tab = ValidateTab(db=self._db, known_names=self._known_names, db_path=self._db_path)
        tabs.addTab(self._validate_tab, "Проверка файла")

        self._import_tab = ImportTab(db=self._db, known_names=self._known_names, on_import_done=self._update_status_bar)
        tabs.addTab(self._import_tab, "Импорт в базу")

        self._database_tab = DatabaseTab(
            db=self._db, known_names=self._known_names, on_data_changed=self._update_status_bar
        )
        tabs.addTab(self._database_tab, "База данных")

        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

    def _update_status_bar(self) -> None:
        total = sum(len(v) for v in self._known_names.values())
        self._status_bar.showMessage(f"База: {self._db_path}  |  Записей: {total}")

    def closeEvent(self, event: QCloseEvent) -> None:
        self._db.close()
        super().closeEvent(event)
