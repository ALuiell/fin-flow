from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QScrollArea, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from database.db_manager import DBManager
from utils.analytics_helper import calculate_safe_to_spend
from utils.formatting import format_money
from ui.dialogs import TransactionDialog

class DashboardPage(QWidget):
    # Signal to update the whole application after adding a transaction
    data_changed = Signal()

    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Left part - Balance, Safe-to-Spend, Quick actions, Accounts
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)

        # 1. Balance and Safe-to-Spend card
        balance_card = QFrame()
        balance_card.setObjectName("CardFrame")
        balance_layout = QHBoxLayout(balance_card)
        balance_layout.setContentsMargins(20, 20, 20, 20)

        # Total balance
        total_bal_layout = QVBoxLayout()
        bal_title = QLabel("Общий баланс")
        bal_title.setObjectName("CardTitle")
        self.bal_value = QLabel("0 RUB")
        self.bal_value.setObjectName("CardValue")
        total_bal_layout.addWidget(bal_title)
        total_bal_layout.addWidget(self.bal_value)
        total_bal_layout.addStretch()

        # Safe-to-Spend limit for the day
        safe_spend_layout = QVBoxLayout()
        safe_title = QLabel("Можно потратить сегодня")
        safe_title.setObjectName("CardTitle")
        self.safe_value = QLabel("0 RUB")
        self.safe_value.setObjectName("CardValue")
        self.safe_value.setStyleSheet("color: #8A2BE2; font-size: 28px;")
        safe_spend_layout.addWidget(safe_title)
        safe_spend_layout.addWidget(self.safe_value)
        safe_spend_layout.addStretch()

        balance_layout.addLayout(total_bal_layout)
        balance_layout.addSpacing(30)
        balance_layout.addLayout(safe_spend_layout)
        balance_layout.addStretch()
        left_layout.addWidget(balance_card)

        # 2. Monthly expense/income indicator cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)

        # Monthly income
        inc_card = QFrame()
        inc_card.setObjectName("CardFrame")
        inc_lay = QVBoxLayout(inc_card)
        inc_title = QLabel("Доходы месяца")
        inc_title.setObjectName("CardTitle")
        self.inc_value = QLabel("+0 RUB")
        self.inc_value.setStyleSheet("color: #00E676; font-weight: bold; font-size: 20px;")
        inc_lay.addWidget(inc_title)
        inc_lay.addWidget(self.inc_value)
        stats_layout.addWidget(inc_card)

        # Monthly expenses
        exp_card = QFrame()
        exp_card.setObjectName("CardFrame")
        exp_lay = QVBoxLayout(exp_card)
        exp_title = QLabel("Расходы месяца")
        exp_title.setObjectName("CardTitle")
        self.exp_value = QLabel("-0 RUB")
        self.exp_value.setStyleSheet("color: #F44336; font-weight: bold; font-size: 20px;")
        exp_lay.addWidget(exp_title)
        exp_lay.addWidget(self.exp_value)
        stats_layout.addWidget(exp_card)

        left_layout.addLayout(stats_layout)

        # 3. Account list (Wallets)
        accounts_card = QFrame()
        accounts_card.setObjectName("CardFrame")
        accounts_lay = QVBoxLayout(accounts_card)
        accounts_title = QLabel("Мои счета")
        accounts_title.setObjectName("CardTitle")
        accounts_lay.addWidget(accounts_title)

        self.accounts_list = QListWidget()
        self.accounts_list.setSelectionMode(QListWidget.NoSelection)
        self.accounts_list.setStyleSheet("background: transparent; border: none;")
        accounts_lay.addWidget(self.accounts_list)
        left_layout.addWidget(accounts_card, stretch=2)

        main_layout.addLayout(left_layout, stretch=3)

        # Right part - Quick buttons and Recent transactions
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)

        # Quick buttons
        actions_card = QFrame()
        actions_card.setObjectName("CardFrame")
        actions_layout = QHBoxLayout(actions_card)
        actions_layout.setContentsMargins(15, 15, 15, 15)

        self.add_exp_btn = QPushButton("💸 Расход")
        self.add_exp_btn.setObjectName("PrimaryButton")
        self.add_exp_btn.setStyleSheet("background-color: #B00020;")
        self.add_exp_btn.clicked.connect(lambda: self.open_tx_dialog("Расход"))

        self.add_inc_btn = QPushButton("💼 Доход")
        self.add_inc_btn.setObjectName("PrimaryButton")
        self.add_inc_btn.setStyleSheet("background-color: #00897B;")
        self.add_inc_btn.clicked.connect(lambda: self.open_tx_dialog("Доход"))

        self.add_transfer_btn = QPushButton("🔄 Перевод")
        self.add_transfer_btn.setObjectName("SecondaryButton")
        self.add_transfer_btn.clicked.connect(lambda: self.open_tx_dialog("Перевод"))

        actions_layout.addWidget(self.add_exp_btn)
        actions_layout.addWidget(self.add_inc_btn)
        actions_layout.addWidget(self.add_transfer_btn)
        right_layout.addWidget(actions_card)

        # Recent transactions
        txs_card = QFrame()
        txs_card.setObjectName("CardFrame")
        txs_layout = QVBoxLayout(txs_card)
        txs_title = QLabel("Последние операции")
        txs_title.setObjectName("CardTitle")
        txs_layout.addWidget(txs_title)

        self.tx_table = QTableWidget()
        self.tx_table.setColumnCount(4)
        self.tx_table.setHorizontalHeaderLabels(["Дата", "Описание / Категория", "Счет", "Сумма"])
        self.tx_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tx_table.setColumnWidth(0, 110)
        self.tx_table.setColumnWidth(1, 450)
        self.tx_table.setColumnWidth(2, 150)
        self.tx_table.setColumnWidth(3, 150)
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tx_table.setSelectionBehavior(QTableWidget.SelectRows)
        txs_layout.addWidget(self.tx_table)

        right_layout.addWidget(txs_card, stretch=4)

        main_layout.addLayout(right_layout, stretch=4)

        # Initial population
        self.refresh_data()

    def refresh_data(self):
        base_currency = self.db.get_setting("base_currency", "RUB")
        
        # 1. Calculate total balance across all accounts
        total_balance_base = 0.0
        accounts = self.db.get_accounts()
        for acc in accounts:
            balance_converted = self.db.convert_amount(acc.balance, acc.currency, base_currency)
            total_balance_base += balance_converted
        self.bal_value.setText(format_money(total_balance_base, base_currency))

        # 2. Update Safe-to-Spend
        safe_data = calculate_safe_to_spend(self.db)
        self.safe_value.setText(format_money(safe_data['safe_today'], base_currency))
        self.inc_value.setText(f"+{format_money(safe_data['actual_incomes'], base_currency)}")
        self.exp_value.setText(f"-{format_money(safe_data['actual_expenses'], base_currency)}")

        # 3. Account list
        self.accounts_list.clear()
        for acc in accounts:
            item = QListWidgetItem()
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(10, 5, 10, 5)
            
            # Account color dot
            color_dot = QLabel("●")
            color_dot.setStyleSheet(f"color: {acc.color}; font-size: 16px;")
            
            name_lbl = QLabel(acc.name)
            name_lbl.setStyleSheet("font-weight: 600;")
            
            bal_lbl = QLabel(format_money(acc.balance, acc.currency))
            bal_lbl.setStyleSheet("font-weight: bold; color: #FFFFFF;")
            
            layout.addWidget(color_dot)
            layout.addWidget(name_lbl)
            layout.addStretch()
            layout.addWidget(bal_lbl)
            
            item.setSizeHint(widget.sizeHint())
            self.accounts_list.addItem(item)
            self.accounts_list.setItemWidget(item, widget)

        # 4. Recent transactions
        txs = self.db.get_transactions()[:8]  # last 8
        self.tx_table.setRowCount(len(txs))
        
        for row_idx, t in enumerate(txs):
            # Date
            self.tx_table.setItem(row_idx, 0, QTableWidgetItem(t['date']))
            
            # Description
            if t['transfer_to_account_id']:
                desc = f"🔄 Перевод на {t['transfer_account_name']}"
            else:
                desc = f"{t['category_icon']} {t['category_name']}"
                if t['description']:
                    desc += f" ({t['description']})"
            
            self.tx_table.setItem(row_idx, 1, QTableWidgetItem(desc))
            
            # Account
            self.tx_table.setItem(row_idx, 2, QTableWidgetItem(t['account_name']))
            
            # Amount
            amount_str = format_money(t['amount'], t['currency'])
            amount_item = QTableWidgetItem()
            
            if t['transfer_to_account_id']:
                amount_item.setText(f" {amount_str}")
                amount_item.setForeground(QColor("#A0A0A0"))
            elif t['category_type'] == 'income':
                amount_item.setText(f"+{amount_str}")
                amount_item.setForeground(QColor("#00E676"))
            else:
                amount_item.setText(f"-{amount_str}")
                amount_item.setForeground(QColor("#F44336"))
                
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.tx_table.setItem(row_idx, 3, amount_item)

    def open_tx_dialog(self, default_type: str):
        dialog = TransactionDialog(self.db, parent=self)
        dialog.type_combo.setCurrentText(default_type)
        dialog.on_type_changed(0)
        
        if dialog.exec() == TransactionDialog.Accepted:
            self.refresh_data()
            self.data_changed.emit()
