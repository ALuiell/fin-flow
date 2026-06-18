from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QDateEdit, QPushButton,
                             QFormLayout, QMessageBox, QWidget)
from PySide6.QtCore import QDate, Qt
from models import Transaction, Account, Category, Subscription
from utils.analytics_helper import eval_expression
from ui.custom_widgets import TagSelector, CategorySelectorWidget

class BaseDialog(QDialog):
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(380, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1E1E1E;
            }
            QLabel {
                font-weight: 600;
                color: #A0A0A0;
            }
        """)

class TransactionDialog(BaseDialog):
    def __init__(self, db, transaction: Transaction = None, parent=None):
        title = "Редактировать транзакцию" if transaction else "Добавить операцию"
        super().__init__(title, parent)
        self.db = db
        self.transaction = transaction

        self.init_ui()
        if transaction:
            self.load_transaction_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        # 1. Operation type
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Расход", "Доход", "Перевод"])
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        form.addRow("Тип:", self.type_combo)

        # 2. Amount (with expression support)
        self.amount_input = QLineEdit()
        self.amount_input.setPlaceholderText("Сумма (например: 150+200)")
        self.amount_input.editingFinished.connect(self.evaluate_amount)
        form.addRow("Сумма:", self.amount_input)

        # 3. Currency
        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "EUR", "UAH", "RUB", "BYN", "KZT"])
        base_curr = self.db.get_setting("base_currency", "USD")
        self.currency_combo.setCurrentText(base_curr)
        form.addRow("Валюта:", self.currency_combo)

        # 4. Withdrawal account / Account
        self.account_combo = QComboBox()
        self.load_accounts(self.account_combo)
        form.addRow("Счет:", self.account_combo)

        # 5. Deposit account (for transfer)
        self.transfer_label = QLabel("Счет зачисления:")
        self.transfer_combo = QComboBox()
        self.load_accounts(self.transfer_combo)
        form.addRow(self.transfer_label, self.transfer_combo)

        # 6. Category
        self.category_label = QLabel("Категория:")
        self.category_combo = CategorySelectorWidget()
        self.load_categories()
        form.addRow(self.category_label, self.category_combo)

        # 7. Date
        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        form.addRow("Дата:", self.date_input)

        # 8. Description
        self.desc_input = QLineEdit()
        form.addRow("Описание:", self.desc_input)

        # 9. Tags
        self.tags_input = TagSelector(self.db, self)
        form.addRow("Теги:", self.tags_input)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

        # Initialize default visibility
        self.on_type_changed(0)

    def load_accounts(self, combo: QComboBox):
        combo.clear()
        self.accounts = self.db.get_accounts()
        for acc in self.accounts:
            combo.addItem(f"{acc.name} ({acc.currency})", acc.id)

    def load_categories(self):
        self.category_combo.clear()
        self.categories = self.db.get_categories()

        # Filter based on the selected type
        current_type = self.type_combo.currentText().lower()
        # If transfer, categories are not needed at all
        if current_type == "расход":
            target_type = "expense"
        elif current_type == "доход":
            target_type = "income"
        else:
            return

        for cat in self.categories:
            if cat.type == target_type:
                self.category_combo.addItem(cat.name, cat.id, cat.parent_id, cat.icon)

    def on_type_changed(self, idx):
        type_str = self.type_combo.currentText()
        if type_str == "Перевод":
            # Hide categories, show deposit account
            self.category_label.hide()
            self.category_combo.hide()
            self.transfer_label.show()
            self.transfer_combo.show()
        else:
            # Show categories, hide deposit account
            self.category_label.show()
            self.category_combo.show()
            self.transfer_label.hide()
            self.transfer_combo.hide()
            self.load_categories()

    def evaluate_amount(self):
        text = self.amount_input.text().strip()
        if not text:
            return
        try:
            val = eval_expression(text)
            self.amount_input.setText(str(val))
            self.amount_input.setStyleSheet("")
        except ValueError:
            self.amount_input.setStyleSheet("border: 1px solid #F44336;")

    def load_transaction_data(self):
        t = self.transaction
        self.amount_input.setText(str(t.amount))

        # Set currency
        idx = self.currency_combo.findText(t.currency)
        if idx >= 0:
            self.currency_combo.setCurrentIndex(idx)

        # Set date
        qdate = QDate.fromString(t.date, "yyyy-MM-dd")
        self.date_input.setDate(qdate)

        # Set description and tags
        self.desc_input.setText(t.description or "")
        self.tags_input.set_tags(t.tags or "")

        # Set withdrawal account
        idx = self.account_combo.findData(t.account_id)
        if idx >= 0:
            self.account_combo.setCurrentIndex(idx)

        # Determine operation type
        if t.transfer_to_account_id:
            self.type_combo.setCurrentText("Перевод")
            idx_to = self.transfer_combo.findData(t.transfer_to_account_id)
            if idx_to >= 0:
                self.transfer_combo.setCurrentIndex(idx_to)
        else:
            cat = self.db.get_category(t.category_id)
            if cat:
                if cat.type == "income":
                    self.type_combo.setCurrentText("Доход")
                else:
                    self.type_combo.setCurrentText("Расход")
                self.load_categories()
                idx_cat = self.category_combo.findData(t.category_id)
                if idx_cat >= 0:
                    self.category_combo.setCurrentIndex(idx_cat)

    def save(self):
        self.evaluate_amount()
        try:
            amount = float(self.amount_input.text())
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Ошибка ввода", "Введите корректную сумму больше 0.")
            return

        currency = self.currency_combo.currentText()
        account_id = self.account_combo.currentData()
        date_str = self.date_input.date().toString("yyyy-MM-dd")
        desc = self.desc_input.text().strip()
        tags = self.tags_input.get_tags().strip()

        type_str = self.type_combo.currentText()

        category_id = None
        transfer_to_account_id = None

        if type_str == "Перевод":
            transfer_to_account_id = self.transfer_combo.currentData()
            if account_id == transfer_to_account_id:
                QMessageBox.warning(self, "Ошибка перевода", "Счета списания и зачисления должны отличаться.")
                return
        else:
            category_id = self.category_combo.currentData()
            if not category_id:
                QMessageBox.warning(self, "Ошибка категории", "Выберите категорию.")
                return

        # Create/Update transaction
        t_id = self.transaction.id if self.transaction else None

        # If we are editing a transaction, first delete the old one to restore balances, then write the new one
        if self.transaction:
            self.db.delete_transaction(t_id)

        new_t = Transaction(
            id=t_id,
            amount=amount,
            currency=currency,
            category_id=category_id,
            account_id=account_id,
            transfer_to_account_id=transfer_to_account_id,
            date=date_str,
            description=desc,
            tags=tags
        )
        self.db.add_transaction(new_t)
        self.accept()


class AccountDialog(BaseDialog):
    def __init__(self, db, account: Account = None, parent=None):
        title = "Редактировать счет" if account else "Создать счет"
        super().__init__(title, parent)
        self.db = db
        self.account = account
        self.init_ui()
        if account:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название (например: Основной)")
        form.addRow("Название:", self.name_input)

        self.balance_input = QLineEdit()
        self.balance_input.setText("0")
        form.addRow("Баланс:", self.balance_input)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "EUR", "UAH", "RUB", "BYN", "KZT"])
        base_curr = self.db.get_setting("base_currency", "USD")
        self.currency_combo.setCurrentText(base_curr)
        form.addRow("Валюта:", self.currency_combo)

        # Simple color selection (from predefined beautiful HEX codes)
        self.color_combo = QComboBox()
        self.colors = {
            "Зеленый": "#4CAF50",
            "Голубой": "#2196F3",
            "Оранжевый": "#FF9800",
            "Фиолетовый": "#9C27B0",
            "Бирюзовый": "#00BCD4",
            "Красный": "#F44336",
            "Темно-серый": "#607D8B"
        }
        for name, hex_val in self.colors.items():
            self.color_combo.addItem(name, hex_val)
        form.addRow("Цвет счета:", self.color_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def load_data(self):
        self.name_input.setText(self.account.name)
        self.balance_input.setText(str(self.account.balance))
        self.currency_combo.setCurrentText(self.account.currency)

        # Look for color
        for i in range(self.color_combo.count()):
            if self.color_combo.itemData(i) == self.account.color:
                self.color_combo.setCurrentIndex(i)
                break

    def save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка ввода", "Введите название счета.")
            return

        try:
            balance = float(self.balance_input.text().replace(",", "."))
        except ValueError:
            QMessageBox.warning(self, "Ошибка ввода", "Введите корректный баланс.")
            return

        currency = self.currency_combo.currentText()
        color = self.color_combo.currentData()

        self.result_account = Account(
            id=self.account.id if self.account else None,
            name=name,
            balance=balance,
            currency=currency,
            color=color
        )
        self.accept()


class CategoryDialog(BaseDialog):
    def __init__(self, db, category: Category = None, parent=None):
        title = "Редактировать категорию" if category else "Создать категорию"
        super().__init__(title, parent)
        self.db = db
        self.category = category
        self.init_ui()
        if category:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        form.addRow("Название:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItem("Расход", "expense")
        self.type_combo.addItem("Доход", "income")
        self.type_combo.currentIndexChanged.connect(self.load_parent_categories)
        form.addRow("Тип:", self.type_combo)

        self.parent_combo = QComboBox()
        form.addRow("Родительская категория:", self.parent_combo)

        self.load_parent_categories()

        self.icon_input = QLineEdit()
        self.icon_input.setPlaceholderText("Эмодзи (например: 🍏)")
        self.icon_input.setMaxLength(2)
        form.addRow("Иконка-Эмодзи:", self.icon_input)

        self.color_combo = QComboBox()
        self.colors = {
            "Зеленый": "#4CAF50",
            "Голубой": "#2196F3",
            "Оранжевый": "#FF9800",
            "Розовый": "#E91E63",
            "Фиолетовый": "#9C27B0",
            "Красный": "#F44336",
            "Серый": "#9E9E9E",
            "Золотой": "#FFC107",
            "Изумрудный": "#009688"
        }
        for name, hex_val in self.colors.items():
            self.color_combo.addItem(name, hex_val)
        form.addRow("Цвет категории:", self.color_combo)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def load_parent_categories(self):
        self.parent_combo.clear()
        self.parent_combo.addItem("Нет (Это основная категория)", None)

        target_type = self.type_combo.currentData()
        categories = self.db.get_categories()
        for cat in categories:
            if cat.parent_id is None and cat.type == target_type:
                if self.category and cat.id == self.category.id:
                    continue
                self.parent_combo.addItem(f"{cat.icon} {cat.name}", cat.id)

    def load_data(self):
        self.name_input.setText(self.category.name)
        self.icon_input.setText(self.category.icon or "")

        # Type
        if self.category.type == "income":
            self.type_combo.setCurrentIndex(1)
        else:
            self.type_combo.setCurrentIndex(0)

        # Parent
        if self.category.parent_id:
            idx = self.parent_combo.findData(self.category.parent_id)
            if idx >= 0:
                self.parent_combo.setCurrentIndex(idx)

        # Color
        for i in range(self.color_combo.count()):
            if self.color_combo.itemData(i) == self.category.color:
                self.color_combo.setCurrentIndex(i)
                break

    def save(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка ввода", "Введите название категории.")
            return

        icon = self.icon_input.text().strip()
        if not icon:
            icon = "💸"  # Default icon

        type_ = self.type_combo.currentData()
        color = self.color_combo.currentData()
        parent_id = self.parent_combo.currentData()

        self.result_category = Category(
            id=self.category.id if self.category else None,
            name=name,
            type=type_,
            icon=icon,
            color=color,
            parent_id=parent_id
        )
        self.accept()


class SubscriptionDialog(BaseDialog):
    def __init__(self, db, subscription: Subscription = None, parent=None):
        title = "Редактировать подписку" if subscription else "Добавить подписку"
        super().__init__(title, parent)
        self.db = db
        self.subscription = subscription
        self.init_ui()
        if subscription:
            self.load_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название (например: Spotify)")
        form.addRow("Название подписки:", self.name_input)

        self.amount_input = QLineEdit()
        self.amount_input.editingFinished.connect(self.evaluate_amount)
        form.addRow("Стоимость:", self.amount_input)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USD", "EUR", "UAH", "RUB", "BYN", "KZT"])
        base_curr = self.db.get_setting("base_currency", "USD")
        self.currency_combo.setCurrentText(base_curr)
        form.addRow("Валюта:", self.currency_combo)

        self.category_combo = CategorySelectorWidget()
        self.load_categories()
        form.addRow("Категория расходов:", self.category_combo)

        self.period_combo = QComboBox()
        self.period_combo.addItem("Ежемесячно", "monthly")
        self.period_combo.addItem("Ежегодно", "yearly")
        form.addRow("Периодичность:", self.period_combo)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        form.addRow("Дата списания:", self.date_input)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self.save)

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addWidget(self.save_btn)
        layout.addLayout(btn_layout)

    def load_categories(self):
        self.category_combo.clear()
        cats = self.db.get_categories()
        for cat in cats:
            if cat.type == "expense":
                self.category_combo.addItem(cat.name, cat.id, cat.parent_id, cat.icon)

    def evaluate_amount(self):
        text = self.amount_input.text().strip()
        if not text:
            return
        try:
            val = eval_expression(text)
            self.amount_input.setText(str(val))
            self.amount_input.setStyleSheet("")
        except ValueError:
            self.amount_input.setStyleSheet("border: 1px solid #F44336;")

    def load_data(self):
        sub = self.subscription
        self.name_input.setText(sub.name)
        self.amount_input.setText(str(sub.amount))
        self.currency_combo.setCurrentText(sub.currency)

        idx = self.category_combo.findData(sub.category_id)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)

        if sub.period == "yearly":
            self.period_combo.setCurrentIndex(1)
        else:
            self.period_combo.setCurrentIndex(0)

        qdate = QDate.fromString(sub.next_payment_date, "yyyy-MM-dd")
        self.date_input.setDate(qdate)

    def save(self):
        self.evaluate_amount()
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка ввода", "Введите название подписки.")
            return

        try:
            amount = float(self.amount_input.text())
            if amount <= 0:
                raise ValueError()
        except ValueError:
            QMessageBox.warning(self, "Ошибка ввода", "Введите корректную стоимость.")
            return

        currency = self.currency_combo.currentText()
        category_id = self.category_combo.currentData()
        period = self.period_combo.currentData()
        date_str = self.date_input.date().toString("yyyy-MM-dd")

        self.result_subscription = Subscription(
            id=self.subscription.id if self.subscription else None,
            name=name,
            amount=amount,
            currency=currency,
            category_id=category_id,
            period=period,
            next_payment_date=date_str,
            is_active=1
        )
        self.accept()
