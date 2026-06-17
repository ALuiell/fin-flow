from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFrame, QMessageBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from database.db_manager import DBManager
from models import Subscription
from ui.dialogs import SubscriptionDialog
from datetime import datetime

class SubscriptionsPage(QWidget):
    data_changed = Signal()

    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Верхний информационный блок
        info_card = QFrame()
        info_card.setObjectName("CardFrame")
        info_layout = QHBoxLayout(info_card)
        info_layout.setContentsMargins(20, 20, 20, 20)

        # Всего подписок
        count_lay = QVBoxLayout()
        count_title = QLabel("Активных подписок")
        count_title.setObjectName("CardTitle")
        self.count_val = QLabel("0")
        self.count_val.setObjectName("CardValue")
        count_lay.addWidget(count_title)
        count_lay.addWidget(self.count_val)
        info_layout.addLayout(count_lay)
        info_layout.addSpacing(30)

        # Общая сумма в месяц
        sum_lay = QVBoxLayout()
        sum_title = QLabel("Общая сумма в месяц")
        sum_title.setObjectName("CardTitle")
        self.sum_val = QLabel("0.00 RUB")
        self.sum_val.setObjectName("CardValue")
        self.sum_val.setStyleSheet("color: #8A2BE2;")
        sum_lay.addWidget(sum_title)
        sum_lay.addWidget(self.sum_val)
        info_layout.addLayout(sum_lay)
        info_layout.addSpacing(30)

        # Процент от зарплаты
        salary_lay = QVBoxLayout()
        salary_title = QLabel("Доля от планируемого дохода")
        salary_title.setObjectName("CardTitle")
        self.salary_val = QLabel("0.0%")
        self.salary_val.setObjectName("CardValue")
        salary_lay.addWidget(salary_title)
        salary_lay.addWidget(self.salary_val)
        info_layout.addLayout(salary_lay)
        
        info_layout.addStretch()
        layout.addWidget(info_card)

        # 2. Кнопки действий
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Добавить подписку")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_subscription)

        self.edit_btn = QPushButton("✏️ Изменить")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_subscription)

        self.del_btn = QPushButton("🗑️ Удалить")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_subscription)

        self.toggle_btn = QPushButton("⏯️ Вкл / Выкл подписку")
        self.toggle_btn.setObjectName("SecondaryButton")
        self.toggle_btn.clicked.connect(self.toggle_subscription)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.toggle_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # 3. Таблица подписок
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Название", "Категория", "Стоимость", "Период", "Списание", "Статус"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 50)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 150)
        self.table.setColumnWidth(4, 150)
        self.table.setColumnWidth(5, 120)
        self.table.setColumnWidth(6, 120)
        layout.addWidget(self.table)

        self.refresh_data()

    def refresh_data(self):
        base_currency = self.db.get_setting("base_currency", "RUB")
        try:
            planned_income = float(self.db.get_setting("planned_monthly_income", "50000"))
        except ValueError:
            planned_income = 50000.0

        subs = self.db.get_subscriptions()
        self.table.setRowCount(len(subs))

        active_count = 0
        total_monthly_sum_base = 0.0

        for row_idx, s in enumerate(subs):
            # ID
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(s['id'])))
            
            # Название
            self.table.setItem(row_idx, 1, QTableWidgetItem(s['name']))
            
            # Категория
            cat_desc = f"{s['category_icon']} {s['category_name']}" if s['category_name'] else "Нет"
            self.table.setItem(row_idx, 2, QTableWidgetItem(cat_desc))

            # Стоимость
            self.table.setItem(row_idx, 3, QTableWidgetItem(f"{s['amount']:,.2f} {s['currency']}"))

            # Период
            period_str = "Ежемесячно" if s['period'] == 'monthly' else "Ежегодно"
            self.table.setItem(row_idx, 4, QTableWidgetItem(period_str))

            # Следующий платеж
            self.table.setItem(row_idx, 5, QTableWidgetItem(s['next_payment_date']))

            # Статус
            status_item = QTableWidgetItem()
            if s['is_active']:
                status_item.setText("Активна")
                status_item.setForeground(QColor("#00E676"))
                active_count += 1
                
                # Считаем сумму в месяц
                amount_base = self.db.convert_amount(s['amount'], s['currency'], base_currency)
                if s['period'] == 'yearly':
                    total_monthly_sum_base += (amount_base / 12.0)
                else:
                    total_monthly_sum_base += amount_base
            else:
                status_item.setText("Отключена")
                status_item.setForeground(QColor("#FF5252"))
                
            self.table.setItem(row_idx, 6, status_item)

        # Выводим инфо на карточки
        self.count_val.setText(str(active_count))
        self.sum_val.setText(f"{total_monthly_sum_base:,.2f} {base_currency}")
        
        # Доля от зарплаты
        if planned_income > 0:
            share = (total_monthly_sum_base / planned_income) * 100
            self.salary_val.setText(f"{share:.1f}%")
            if share >= 20:
                self.salary_val.setStyleSheet("color: #FF5252; font-size: 24px; font-weight: bold;")
            elif share >= 10:
                self.salary_val.setStyleSheet("color: #FF9800; font-size: 24px; font-weight: bold;")
            else:
                self.salary_val.setStyleSheet("color: #00E676; font-size: 24px; font-weight: bold;")
        else:
            self.salary_val.setText("0.0%")
            self.salary_val.setStyleSheet("color: #FFFFFF;")

    def add_subscription(self):
        dialog = SubscriptionDialog(self.db, parent=self)
        if dialog.exec() == SubscriptionDialog.Accepted:
            self.db.add_subscription(
                dialog.result_subscription.name,
                dialog.result_subscription.amount,
                dialog.result_subscription.currency,
                dialog.result_subscription.category_id,
                dialog.result_subscription.period,
                dialog.result_subscription.next_payment_date
            )
            self.refresh_data()
            self.data_changed.emit()

    def edit_subscription(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Редактирование", "Выберите подписку из таблицы.")
            return

        sub_id = int(self.table.item(row, 0).text())
        subs = self.db.get_subscriptions()
        target_sub_dict = next((s for s in subs if s['id'] == sub_id), None)
        
        if target_sub_dict:
            sub = Subscription(
                id=target_sub_dict['id'],
                name=target_sub_dict['name'],
                amount=target_sub_dict['amount'],
                currency=target_sub_dict['currency'],
                category_id=target_sub_dict['category_id'],
                period=target_sub_dict['period'],
                next_payment_date=target_sub_dict['next_payment_date'],
                is_active=target_sub_dict['is_active']
            )
            dialog = SubscriptionDialog(self.db, subscription=sub, parent=self)
            if dialog.exec() == SubscriptionDialog.Accepted:
                # Сохраняем состояние активности
                dialog.result_subscription.is_active = sub.is_active
                self.db.update_subscription(dialog.result_subscription)
                self.refresh_data()
                self.data_changed.emit()

    def delete_subscription(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Удаление", "Выберите подписку из таблицы.")
            return

        sub_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(self, "Удаление подписки", "Вы уверены, что хотите удалить эту подписку?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_subscription(sub_id):
                self.refresh_data()
                self.data_changed.emit()

    def toggle_subscription(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Статус подписки", "Выберите подписку из таблицы.")
            return

        sub_id = int(self.table.item(row, 0).text())
        subs = self.db.get_subscriptions()
        s_dict = next((s for s in subs if s['id'] == sub_id), None)
        
        if s_dict:
            sub = Subscription(
                id=s_dict['id'],
                name=s_dict['name'],
                amount=s_dict['amount'],
                currency=s_dict['currency'],
                category_id=s_dict['category_id'],
                period=s_dict['period'],
                next_payment_date=s_dict['next_payment_date'],
                is_active=1 if s_dict['is_active'] == 0 else 0
            )
            self.db.update_subscription(sub)
            self.refresh_data()
            self.data_changed.emit()
