import sys
import os

# Fix for compatibility with PyInstaller + PySide6 (shiboken) + six
try:
    import six
    six._SixMetaPathImporter._path = []
except Exception:
    pass

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPalette, QColor
from database.db_manager import DBManager
from ui.main_window import MainWindow

def apply_dark_theme(app: QApplication):
    # Force the cross-platform Fusion style
    app.setStyle("Fusion")

    # Configure the dark palette for all standard Qt elements
    palette = QPalette()

    # Dark theme color scheme
    dark_bg = QColor(18, 18, 18)        # #121212
    card_bg = QColor(30, 30, 30)        # #1E1E1E
    input_bg = QColor(34, 34, 34)       # #222222
    text_color = QColor(224, 224, 224)  # #E0E0E0
    white = QColor(255, 255, 255)
    highlight_color = QColor(138, 43, 226) # #8A2BE2 (Purple)

    palette.setColor(QPalette.Window, dark_bg)
    palette.setColor(QPalette.WindowText, text_color)
    palette.setColor(QPalette.Base, input_bg)
    palette.setColor(QPalette.AlternateBase, card_bg)
    palette.setColor(QPalette.ToolTipBase, card_bg)
    palette.setColor(QPalette.ToolTipText, white)
    palette.setColor(QPalette.Text, text_color)
    palette.setColor(QPalette.Button, card_bg)
    palette.setColor(QPalette.ButtonText, white)
    palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
    palette.setColor(QPalette.Link, highlight_color)
    palette.setColor(QPalette.Highlight, highlight_color)
    palette.setColor(QPalette.HighlightedText, white)

    # Colors for disabled elements
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(120, 120, 120))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor(120, 120, 120))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(120, 120, 120))
    palette.setColor(QPalette.Disabled, QPalette.Base, dark_bg)

    app.setPalette(palette)

def load_stylesheet(app: QApplication, qss_path: str):
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    else:
        print(f"Warning: Stylesheet file not found at {qss_path}")

def main():
    # Settings for high DPI screens (for Qt6 this is already built-in by default, but useful to mention)
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    app.setApplicationName("FinFlow")

    # Resource paths (styles, icons)
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS  # PyInstaller temporary extraction folder
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    qss_path = os.path.join(base_dir, "ui", "styles.qss")
    icon_path = os.path.join(base_dir, "assets", "icon.png")

    # Database path (reliable location in the user's folder)
    app_data_dir = os.path.join(os.path.expanduser("~"), ".finflow")
    if not os.path.exists(app_data_dir):
        os.makedirs(app_data_dir, exist_ok=True)

    db_path = os.path.join(app_data_dir, "finflow.db")

    # Database initialization
    db = DBManager(db_path=db_path)

    # Load QSS styles
    load_stylesheet(app, qss_path)

    # Create the main window
    window = MainWindow(db)

    # Set application icon
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
        window.setWindowIcon(app_icon)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
