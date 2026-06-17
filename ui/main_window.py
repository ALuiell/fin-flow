from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, 
                             QPushButton, QStackedWidget, QFrame, QLabel)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QShortcut, QKeySequence
from database.db_manager import DBManager

# Импортируем страницы
from ui.dashboard_page import DashboardPage
from ui.transactions_page import TransactionsPage
from ui.calendar_page import CalendarPage
from ui.analytics_page import AnalyticsPage
from ui.subscriptions_page import SubscriptionsPage
from ui.budgets_page import BudgetsPage
from ui.settings_page import SettingsPage
from ui.dialogs import TransactionDialog

class MainWindow(QMainWindow):
    def __init__(self, db: DBManager):
        super().__init__()
        self.db = db
        self.setWindowTitle("FinFlow — Личный Финансовый Менеджер")
        self.resize(1150, 750)
        self.init_ui()
        self.init_shortcuts()

    def init_ui(self):
        # Главный контейнер
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Левый сайдбар
        sidebar = QFrame()
        sidebar.setObjectName("SidebarFrame")
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 10, 0, 10)
        sidebar_layout.setSpacing(5)

        # Заголовок приложения
        title_lbl = QLabel("🌊 FinFlow")
        title_lbl.setObjectName("AppTitleLabel")
        title_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(title_lbl)
        sidebar_layout.addSpacing(20)

        # Кнопки сайдбара
        self.nav_buttons = []
        menu_items = [
            ("📊 Обзор", 0),
            ("💸 Операции", 1),
            ("📅 Календарь", 2),
            ("📈 Аналитика", 3),
            ("🔔 Подписки", 4),
            ("🎯 Лимиты", 5),
            ("⚙️ Настройки", 6)
        ]

        for text, index in menu_items:
            btn = QPushButton(text)
            btn.setObjectName("SidebarButton")
            btn.setCheckable(True)
            if index == 0:
                btn.setChecked(True)
            # Передаем индекс при клике
            btn.clicked.connect(lambda checked, idx=index: self.switch_page(idx))
            sidebar_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sidebar_layout.addStretch()
        
        # Автор или статус в самом низу
        status_lbl = QLabel("v1.0.0 (Local)")
        status_lbl.setStyleSheet("color: #555555; padding: 10px; font-size: 11px;")
        status_lbl.setAlignment(Qt.AlignCenter)
        sidebar_layout.addWidget(status_lbl)

        main_layout.addWidget(sidebar)

        # 2. Правая часть - QStackedWidget с контентом
        self.pages_container = QStackedWidget()
        
        # Создаем страницы
        self.dashboard_page = DashboardPage(self.db)
        self.transactions_page = TransactionsPage(self.db)
        self.calendar_page = CalendarPage(self.db)
        self.analytics_page = AnalyticsPage(self.db)
        self.subscriptions_page = SubscriptionsPage(self.db)
        self.budgets_page = BudgetsPage(self.db)
        self.settings_page = SettingsPage(self.db)

        # Добавляем в стек
        self.pages_container.addWidget(self.dashboard_page)      # 0
        self.pages_container.addWidget(self.transactions_page)   # 1
        self.pages_container.addWidget(self.calendar_page)       # 2
        self.pages_container.addWidget(self.analytics_page)      # 3
        self.pages_container.addWidget(self.subscriptions_page)  # 4
        self.pages_container.addWidget(self.budgets_page)        # 5
        self.pages_container.addWidget(self.settings_page)       # 6

        main_layout.addWidget(self.pages_container, stretch=1)

        # Связываем сигналы изменения данных, чтобы страницы обновлялись синхронно
        self.dashboard_page.data_changed.connect(self.refresh_all_pages)
        self.transactions_page.data_changed.connect(self.refresh_all_pages)
        self.calendar_page.data_changed.connect(self.refresh_all_pages)
        self.subscriptions_page.data_changed.connect(self.refresh_all_pages)
        self.budgets_page.data_changed.connect(self.refresh_all_pages)
        self.settings_page.data_changed.connect(self.refresh_all_pages)

    def switch_page(self, page_index: int):
        self.pages_container.setCurrentIndex(page_index)
        
        # Снимаем checked с остальных кнопок
        for idx, btn in enumerate(self.nav_buttons):
            btn.setChecked(idx == page_index)
            
        # Обновляем данные на открываемой странице
        widget = self.pages_container.widget(page_index)
        if hasattr(widget, "refresh_data"):
            widget.refresh_data()

    def refresh_all_pages(self):
        # Обновляем все страницы в фоне
        self.dashboard_page.refresh_data()
        self.transactions_page.refresh_data()
        self.calendar_page.refresh_data()
        self.analytics_page.refresh_data()
        self.subscriptions_page.refresh_data()
        self.budgets_page.refresh_data()
        self.settings_page.refresh_data()
        
        # Обновляем фильтры (например, если изменились счета/категории)
        self.transactions_page.load_filters()

    def init_shortcuts(self):
        # Ctrl + N — быстрое создание транзакции
        self.shortcut_new = QShortcut(QKeySequence("Ctrl+N"), self)
        self.shortcut_new.activated.connect(self.quick_add_transaction)

        # Ctrl + 1..7 — переключение вкладок
        for i in range(7):
            seq = QKeySequence(f"Ctrl+{i+1}")
            shortcut = QShortcut(seq, self)
            shortcut.activated.connect(lambda idx=i: self.switch_page(idx))

    def quick_add_transaction(self):
        dialog = TransactionDialog(self.db, parent=self)
        if dialog.exec() == TransactionDialog.Accepted:
            self.refresh_all_pages()
