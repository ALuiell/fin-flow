from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QFrame, QMessageBox, QTabWidget,
                             QFormLayout, QLineEdit, QComboBox, QInputDialog,
                             QTreeView, QAbstractItemView)
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel
from PySide6.QtGui import QColor, QKeySequence, QShortcut, QStandardItemModel, QStandardItem
from database.db_manager import DBManager
from models import Account, Category
from ui.dialogs import AccountDialog, CategoryDialog
from utils.currency_api import update_exchange_rates
from utils.formatting import format_amount

class SettingsPage(QWidget):
    data_changed = Signal()

    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Tab widget to separate settings
        self.tabs = QTabWidget()

        # 1. General
        self.tab_general = QWidget()
        self.init_general_tab()
        self.tabs.addTab(self.tab_general, "⚙️ Основные")

        # 2. Accounts
        self.tab_accounts = QWidget()
        self.init_accounts_tab()
        self.tabs.addTab(self.tab_accounts, "💳 Кошельки / Счета")

        # 3. Categories
        self.tab_categories = QWidget()
        self.init_categories_tab()
        self.tabs.addTab(self.tab_categories, "📁 Категории")

        layout.addWidget(self.tabs)

    def refresh_data(self):
        self.refresh_rates()
        self.refresh_accounts()
        self.refresh_categories()

    # --- TAB 1: GENERAL SETTINGS ---
    def init_general_tab(self):
        lay = QVBoxLayout(self.tab_general)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(15)

        form_card = QFrame()
        form_card.setObjectName("CardFrame")
        form_lay = QFormLayout(form_card)
        form_lay.setContentsMargins(15, 15, 15, 15)

        # Select base currency
        self.curr_combo = QComboBox()
        self.curr_combo.addItems(["USD", "EUR", "UAH", "RUB", "BYN", "KZT"])
        base_curr = self.db.get_setting("base_currency", "USD")
        self.curr_combo.setCurrentText(base_curr)
        self.curr_combo.currentIndexChanged.connect(self.save_base_currency)
        form_lay.addRow("Базовая валюта приложения:", self.curr_combo)

        # Expected monthly income
        self.salary_input = QLineEdit()
        planned = self.db.get_setting("planned_monthly_income", "2000")
        self.salary_input.setText(planned)

        salary_save_btn = QPushButton("Сохранить доход")
        salary_save_btn.setObjectName("SecondaryButton")
        salary_save_btn.clicked.connect(self.save_salary)

        salary_h = QHBoxLayout()
        salary_h.addWidget(self.salary_input)
        salary_h.addWidget(salary_save_btn)
        form_lay.addRow("Планируемый доход в месяц:", salary_h)

        # Open DB folder
        self.open_db_btn = QPushButton("📂 Открыть папку с базой данных")
        self.open_db_btn.setObjectName("SecondaryButton")
        self.open_db_btn.clicked.connect(self.open_db_folder)
        form_lay.addRow("Расположение данных:", self.open_db_btn)

        lay.addWidget(form_card)

        # Currency rates
        rates_card = QFrame()
        rates_card.setObjectName("CardFrame")
        rates_lay = QVBoxLayout(rates_card)
        rates_lay.setContentsMargins(15, 15, 15, 15)

        rates_header = QHBoxLayout()
        rates_title = QLabel("Курсы обмена валют (к USD)")
        rates_title.setObjectName("CardTitle")
        rates_header.addWidget(rates_title)

        self.sync_btn = QPushButton("🔄 Синхронизировать из сети")
        self.sync_btn.setObjectName("PrimaryButton")
        self.sync_btn.clicked.connect(self.sync_rates)
        rates_header.addWidget(self.sync_btn)

        rates_lay.addLayout(rates_header)

        self.rates_table = QTableWidget()
        self.rates_table.setColumnCount(3)
        self.rates_table.setHorizontalHeaderLabels(["Код валюты", "1 ед. валюты в USD", "Редактировать"])
        self.rates_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.rates_table.setColumnWidth(0, 150)
        self.rates_table.setColumnWidth(1, 250)
        self.rates_table.setColumnWidth(2, 150)
        self.rates_table.verticalHeader().setVisible(False)
        self.rates_table.setEditTriggers(QTableWidget.NoEditTriggers)
        rates_lay.addWidget(self.rates_table)

        lay.addWidget(rates_card)
        self.refresh_rates()

    def refresh_rates(self):
        rates = self.db.get_rates()
        self.rates_table.setRowCount(len(rates))
        for row, (code, val) in enumerate(rates.items()):
            self.rates_table.setItem(row, 0, QTableWidgetItem(code))
            self.rates_table.setItem(row, 1, QTableWidgetItem(f"{val:.5f}"))

            edit_btn = QPushButton("✏️")
            edit_btn.setObjectName("SecondaryButton")
            edit_btn.setMaximumWidth(40)
            edit_btn.clicked.connect(lambda ch=False, c=code, v=val: self.edit_rate(c, v))
            self.rates_table.setCellWidget(row, 2, edit_btn)

    def edit_rate(self, code: str, current_val: float):
        new_val, ok = QInputDialog.getDouble(
            self, "Курс валюты",
            f"Введите стоимость 1 {code} в USD:",
            current_val, 0.00001, 10000.0, 5
        )
        if ok:
            self.db.update_rate(code, new_val)
            self.refresh_rates()
            self.data_changed.emit()

    def sync_rates(self):
        self.sync_btn.setEnabled(False)
        self.sync_btn.setText("Синхронизация...")
        # Run in synchronous mode (acceptable for local app as timeout is 5s)
        success = update_exchange_rates(self.db)
        self.sync_btn.setEnabled(True)
        self.sync_btn.setText("🔄 Синхронизировать из сети")
        if success:
            QMessageBox.information(self, "Курсы валют", "Курсы успешно обновлены!")
            self.refresh_rates()
            self.data_changed.emit()
        else:
            QMessageBox.warning(self, "Курсы валют", "Не удалось подключиться к серверу валют.")

    def save_base_currency(self, idx):
        base_curr = self.curr_combo.currentText()
        self.db.set_setting("base_currency", base_curr)
        self.data_changed.emit()

    def save_salary(self):
        val = self.salary_input.text().strip()
        try:
            float(val)
            self.db.set_setting("planned_monthly_income", val)
            QMessageBox.information(self, "Сохранено", "Плановый доход успешно сохранен.")
            self.data_changed.emit()
        except ValueError:
            QMessageBox.warning(self, "Ошибка ввода", "Введите корректное число для дохода.")

    def open_db_folder(self):
        import os, sys, subprocess
        db_dir = os.path.dirname(os.path.abspath(self.db.db_path))
        if sys.platform == 'win32':
            os.startfile(db_dir)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', db_dir])
        else:
            subprocess.Popen(['xdg-open', db_dir])

    # --- TAB 2: ACCOUNT MANAGEMENT ---
    def init_accounts_tab(self):
        lay = QVBoxLayout(self.tab_accounts)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(15)

        btn_lay = QHBoxLayout()
        self.add_acc_btn = QPushButton("➕ Добавить счет")
        self.add_acc_btn.setObjectName("PrimaryButton")
        self.add_acc_btn.clicked.connect(self.add_account)
        btn_lay.addWidget(self.add_acc_btn)

        self.edit_acc_btn = QPushButton("✏️ Изменить")
        self.edit_acc_btn.setObjectName("SecondaryButton")
        self.edit_acc_btn.clicked.connect(self.edit_account)
        btn_lay.addWidget(self.edit_acc_btn)

        self.del_acc_btn = QPushButton("🗑️ Удалить")
        self.del_acc_btn.setObjectName("DangerButton")
        self.del_acc_btn.clicked.connect(self.delete_account)
        btn_lay.addWidget(self.del_acc_btn)
        btn_lay.addStretch()
        lay.addLayout(btn_lay)

        self.acc_table = QTableWidget()
        self.acc_table.setColumnCount(5)
        self.acc_table.setHorizontalHeaderLabels(["ID", "Название", "Баланс", "Валюта", "Цвет"])
        self.acc_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.acc_table.setColumnWidth(0, 50)
        self.acc_table.setColumnWidth(1, 300)
        self.acc_table.setColumnWidth(2, 200)
        self.acc_table.setColumnWidth(3, 150)
        self.acc_table.setColumnWidth(4, 100)
        self.acc_table.verticalHeader().setVisible(False)
        self.acc_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.acc_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.acc_table.setSelectionMode(QTableWidget.SingleSelection)
        lay.addWidget(self.acc_table)

        # Interactivity
        self.acc_table.itemDoubleClicked.connect(self.edit_account)

        self.acc_del_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.acc_table)
        self.acc_del_shortcut.setContext(Qt.WidgetShortcut)
        self.acc_del_shortcut.activated.connect(self.delete_account)

        self.refresh_accounts()

    def refresh_accounts(self):
        accs = self.db.get_accounts()
        self.acc_table.setRowCount(len(accs))
        for row, a in enumerate(accs):
            self.acc_table.setItem(row, 0, QTableWidgetItem(str(a.id)))
            self.acc_table.setItem(row, 1, QTableWidgetItem(a.name))
            self.acc_table.setItem(row, 2, QTableWidgetItem(format_amount(a.balance)))
            self.acc_table.setItem(row, 3, QTableWidgetItem(a.currency))

            # Color block
            color_item = QTableWidgetItem("■■■")
            color_item.setForeground(QColor(a.color))
            self.acc_table.setItem(row, 4, color_item)

    def add_account(self):
        dialog = AccountDialog(self.db, parent=self)
        if dialog.exec() == AccountDialog.Accepted:
            self.db.add_account(
                dialog.result_account.name,
                dialog.result_account.balance,
                dialog.result_account.currency,
                dialog.result_account.color
            )
            self.refresh_accounts()
            self.data_changed.emit()

    def edit_account(self, *args):
        row = self.acc_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Редактирование", "Выберите счет из таблицы.")
            return

        acc_id = int(self.acc_table.item(row, 0).text())
        acc = self.db.get_account(acc_id)
        if acc:
            dialog = AccountDialog(self.db, account=acc, parent=self)
            if dialog.exec() == AccountDialog.Accepted:
                self.db.update_account(dialog.result_account)
                self.refresh_accounts()
                self.data_changed.emit()

    def delete_account(self):
        row = self.acc_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Удаление", "Выберите счет для удаления.")
            return

        acc_id = int(self.acc_table.item(row, 0).text())

        # Protection against deleting the last account
        if len(self.db.get_accounts()) <= 1:
            QMessageBox.warning(self, "Удаление", "Нельзя удалить единственный кошелек.")
            return

        reply = QMessageBox.question(self, "Удаление счета", "Вы действительно хотите удалить этот счет? Все его транзакции также будут удалены!",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_account(acc_id):
                self.refresh_accounts()
                self.data_changed.emit()

    # --- TAB 3: CATEGORY MANAGEMENT ---
    def init_categories_tab(self):
        lay = QVBoxLayout(self.tab_categories)
        lay.setContentsMargins(15, 15, 15, 15)
        lay.setSpacing(15)

        btn_lay = QHBoxLayout()
        self.add_cat_btn = QPushButton("➕ Добавить категорию")
        self.add_cat_btn.setObjectName("PrimaryButton")
        self.add_cat_btn.clicked.connect(self.add_category)
        btn_lay.addWidget(self.add_cat_btn)

        self.edit_cat_btn = QPushButton("✏️ Изменить")
        self.edit_cat_btn.setObjectName("SecondaryButton")
        self.edit_cat_btn.clicked.connect(self.edit_category)
        btn_lay.addWidget(self.edit_cat_btn)

        self.del_cat_btn = QPushButton("🗑️ Удалить")
        self.del_cat_btn.setObjectName("DangerButton")
        self.del_cat_btn.clicked.connect(self.delete_category)
        btn_lay.addWidget(self.del_cat_btn)
        btn_lay.addStretch()
        lay.addLayout(btn_lay)

        self.cat_search = QLineEdit()
        self.cat_search.setPlaceholderText("Поиск по категориям...")
        self.cat_search.setStyleSheet("background-color: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 6px; padding: 6px;")
        self.cat_proxy = None
        self.cat_search.textChanged.connect(self.filter_categories)
        lay.addWidget(self.cat_search)

        self.cat_tree = QTreeView()
        self.cat_tree.setStyleSheet("QTreeView { background-color: #181818; border: none; outline: none; } QTreeView::item { padding: 4px; } QTreeView::item:hover { background-color: #2A2A2A; border-radius: 4px; }")
        self.cat_tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cat_tree.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cat_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cat_tree.setAlternatingRowColors(True)
        self.cat_tree.setIndentation(40)
        lay.addWidget(self.cat_tree)

        # Interactivity
        self.cat_tree.doubleClicked.connect(self.edit_category)

        self.cat_del_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.cat_tree)
        self.cat_del_shortcut.setContext(Qt.WidgetShortcut)
        self.cat_del_shortcut.activated.connect(self.delete_category)

        self.refresh_categories()

    def refresh_categories(self):
        cats = self.db.get_categories()

        # Sort so that subcategories go right after parents
        model = QStandardItemModel()
        model.setHorizontalHeaderLabels(["Категория", "Тип", "Цвет", "ID"])

        parents = {}
        # First add parents
        for c in cats:
            if c.parent_id is None:
                display_text = f"{c.icon or ''} {c.name}".strip()
                cat_item = QStandardItem(display_text)
                cat_item.setData(c.id, Qt.UserRole)
                type_desc = "Доход" if c.type == "income" else "Расход"
                type_item = QStandardItem(type_desc)
                color_item = QStandardItem("■■■")
                color_item.setForeground(QColor(c.color))
                id_item = QStandardItem(str(c.id))

                parents[c.id] = cat_item
                model.appendRow([cat_item, type_item, color_item, id_item])

        # Then subcategories
        for c in cats:
            if c.parent_id is not None:
                display_text = f"{c.icon or ''} {c.name}".strip()
                cat_item = QStandardItem(display_text)
                cat_item.setData(c.id, Qt.UserRole)
                type_desc = "Доход" if c.type == "income" else "Расход"
                type_item = QStandardItem(type_desc)
                color_item = QStandardItem("■■■")
                color_item.setForeground(QColor(c.color))
                id_item = QStandardItem(str(c.id))

                parent_item = parents.get(c.parent_id)
                if parent_item:
                    parent_item.appendRow([cat_item, type_item, color_item, id_item])
                else:
                    model.appendRow([cat_item, type_item, color_item, id_item])

        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setRecursiveFilteringEnabled(True)
        proxy.setFilterKeyColumn(0) # Search by name

        self.cat_proxy = proxy
        self.cat_proxy.setFilterFixedString(self.cat_search.text())
        self.cat_tree.setModel(proxy)

        self.cat_tree.header().setSectionResizeMode(QHeaderView.Interactive)
        self.cat_tree.setColumnWidth(0, 450)
        self.cat_tree.setColumnWidth(1, 150)
        self.cat_tree.setColumnWidth(2, 100)
        self.cat_tree.setColumnWidth(3, 50)
        self.cat_tree.setColumnHidden(3, True)

        self.cat_tree.expandAll()

    def filter_categories(self, text):
        if self.cat_proxy:
            self.cat_proxy.setFilterFixedString(text)
        self.cat_tree.expandAll()

    def add_category(self):
        dialog = CategoryDialog(self.db, parent=self)
        if dialog.exec() == CategoryDialog.Accepted:
            self.db.add_category(
                dialog.result_category.name,
                dialog.result_category.type,
                dialog.result_category.icon,
                dialog.result_category.color,
                dialog.result_category.parent_id
            )
            self.refresh_categories()
            self.data_changed.emit()

    def edit_category(self, *args):
        selection = self.cat_tree.selectionModel().selectedRows(0)
        if not selection:
            QMessageBox.warning(self, "Редактирование", "Выберите категорию из таблицы.")
            return

        cat_id = int(selection[0].data(Qt.UserRole))
        cat = self.db.get_category(cat_id)
        if cat:
            # Protection against editing the base default category "Other"
            if cat.name == "Другое":
                QMessageBox.warning(self, "Редактирование", "Нельзя редактировать категорию 'Другое' по умолчанию.")
                return

            dialog = CategoryDialog(self.db, category=cat, parent=self)
            if dialog.exec() == CategoryDialog.Accepted:
                self.db.update_category(dialog.result_category)
                self.refresh_categories()
                self.data_changed.emit()

    def delete_category(self):
        selection = self.cat_tree.selectionModel().selectedRows(0)
        if not selection:
            QMessageBox.warning(self, "Удаление", "Выберите категорию для удаления.")
            return

        cat_id = int(selection[0].data(Qt.UserRole))
        cat = self.db.get_category(cat_id)

        if cat.name == "Другое":
            QMessageBox.warning(self, "Удаление", "Категорию 'Другое' удалить нельзя.")
            return

        reply = QMessageBox.question(self, "Удаление категории", "Вы уверены? При удалении все связанные с ней транзакции будут перенесены в категорию 'Другое'.",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_category(cat_id):
                self.refresh_categories()
                self.data_changed.emit()
