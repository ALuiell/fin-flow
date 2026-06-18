import csv
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QLineEdit, QComboBox, QDateEdit,
                             QFileDialog, QMessageBox, QFrame)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor
from models import Transaction
from ui.dialogs import TransactionDialog
from ui.custom_widgets import CategoryFilterWidget, TagFilterWidget
from utils.analytics_helper import sort_transactions_by_selected_subcategories
from utils.formatting import format_money
from datetime import datetime

class TransactionsPage(QWidget):
    data_changed = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 1. Панель фильтров
        filter_card = QFrame()
        filter_card.setStyleSheet("background-color: #1E1E1E; border-radius: 8px; padding: 10px;")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(10, 10, 10, 10)
        filter_layout.setSpacing(10)

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по описанию или тегам...")
        self.search_input.textChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.search_input, stretch=2)

        # Фильтр категорий
        self.cat_filter = CategoryFilterWidget()
        self.cat_filter.setText("Все категории")
        self.cat_filter.dataChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.cat_filter, stretch=1)

        # Фильтр тегов
        self.tag_filter = TagFilterWidget(self.db)
        self.tag_filter.dataChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.tag_filter, stretch=1)

        # Фильтр счетов
        self.acc_filter = QComboBox()
        self.acc_filter.currentIndexChanged.connect(self.refresh_data)
        filter_layout.addWidget(self.acc_filter, stretch=1)

        # Дата с
        self.date_start = QDateEdit()
        self.date_start.setCalendarPopup(True)
        self.date_start.setDate(QDate.currentDate().addMonths(-3)) # по умолчанию за 3 мес.
        self.date_start.dateChanged.connect(self.refresh_data)
        filter_layout.addWidget(QLabel("С:"))
        filter_layout.addWidget(self.date_start)

        # Дата по
        self.date_end = QDateEdit()
        self.date_end.setCalendarPopup(True)
        self.date_end.setDate(QDate.currentDate().addDays(1)) # по завтрашний день
        self.date_end.dateChanged.connect(self.refresh_data)
        filter_layout.addWidget(QLabel("По:"))
        filter_layout.addWidget(self.date_end)

        layout.addWidget(filter_card)

        # 2. Кнопки действий
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("➕ Добавить операцию")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.clicked.connect(self.add_transaction)

        self.edit_btn = QPushButton("✏️ Изменить")
        self.edit_btn.setObjectName("SecondaryButton")
        self.edit_btn.clicked.connect(self.edit_transaction)

        self.del_btn = QPushButton("🗑️ Удалить")
        self.del_btn.setObjectName("DangerButton")
        self.del_btn.clicked.connect(self.delete_transaction)

        self.export_btn = QPushButton("📤 Экспорт в CSV")
        self.export_btn.setObjectName("SecondaryButton")
        self.export_btn.clicked.connect(self.export_to_csv)

        self.import_btn = QPushButton("📥 Импорт из CSV")
        self.import_btn.setObjectName("SecondaryButton")
        self.import_btn.clicked.connect(self.import_from_csv)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.edit_btn)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.import_btn)
        btn_layout.addWidget(self.export_btn)
        layout.addLayout(btn_layout)

        # 3. Таблица транзакций
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["ID", "Дата", "Категория", "Счет", "Описание", "Теги", "Сумма"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setColumnWidth(0, 50)  # ID
        self.table.setColumnWidth(1, 100) # Дата
        self.table.setColumnWidth(2, 170) # Категория
        self.table.setColumnWidth(3, 130) # Счет
        self.table.setColumnWidth(4, 240) # Описание
        self.table.setColumnWidth(5, 120) # Теги
        self.table.setColumnWidth(6, 120) # Сумма
        layout.addWidget(self.table)

        # Интерактивность
        self.table.itemDoubleClicked.connect(self.edit_transaction)

        from PySide6.QtGui import QKeySequence, QShortcut
        self.del_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), self.table)
        self.del_shortcut.setContext(Qt.WidgetShortcut)
        self.del_shortcut.activated.connect(self.delete_transaction)

        self.load_filters()
        self.refresh_data()

    def load_filters(self):
        # Отключаем сигналы временно
        try:
            self.cat_filter.dataChanged.disconnect(self.refresh_data)
            self.tag_filter.dataChanged.disconnect(self.refresh_data)
        except:
            pass
        self.acc_filter.blockSignals(True)

        self.cat_filter.clear()
        categories = self.db.get_categories()
        for cat in categories:
            self.cat_filter.addItem(cat.name, cat.id, cat.parent_id, cat.icon)

        self.tag_filter.refresh_tags()

        self.acc_filter.clear()
        self.acc_filter.addItem("Все счета", 0)
        for acc in self.db.get_accounts():
            self.acc_filter.addItem(acc.name, acc.id)

        self.cat_filter.dataChanged.connect(self.refresh_data)
        self.tag_filter.dataChanged.connect(self.refresh_data)
        self.acc_filter.blockSignals(False)

    def refresh_data(self, *args, **kwargs):
        search = self.search_input.text().strip()
        cat_ids = self.cat_filter.currentData()
        selected_subcategory_ids = self.cat_filter.currentSubcategoryData()
        tag_list = self.tag_filter.currentData()
        acc_id = self.acc_filter.currentData()
        start = self.date_start.date().toString("yyyy-MM-dd")
        end = self.date_end.date().toString("yyyy-MM-dd")

        acc_param = [acc_id] if acc_id != 0 else None
        search_param = search if search else None

        # Выполняем поиск по тегу, если строка начинается с #
        if search_param and search_param.startswith("#"):
            tag_list.append(search_param[1:])
            search_param = None

        txs = self.db.get_transactions(
            start_date=start,
            end_date=end,
            category_ids=cat_ids if cat_ids else None,
            account_ids=acc_param,
            tags=tag_list if tag_list else None
        )

        # Дополнительная ручная фильтрация по описанию, если поиск не по тегам
        if search_param:
            txs = [t for t in txs if search_param.lower() in (t['description'] or '').lower() or search_param.lower() in (t['category_name'] or '').lower()]

        txs = sort_transactions_by_selected_subcategories(txs, selected_subcategory_ids)

        self.table.setRowCount(len(txs))

        for row_idx, t in enumerate(txs):
            is_subcategory_match = bool(selected_subcategory_ids and t['category_id'] in selected_subcategory_ids)

            # ID
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(t['id'])))

            # Дата
            self.table.setItem(row_idx, 1, QTableWidgetItem(t['date']))

            # Категория
            if t['transfer_to_account_id']:
                cat_desc = f"🔄 Перевод"
            else:
                cat_desc = f"{t['category_icon']} {t['category_name']}"
            if is_subcategory_match:
                cat_desc = f"◆ {cat_desc}"
            category_item = QTableWidgetItem(cat_desc)
            if is_subcategory_match:
                font = category_item.font()
                font.setBold(True)
                category_item.setFont(font)
                category_item.setForeground(QColor("#FFFFFF"))
            self.table.setItem(row_idx, 2, category_item)

            # Счет
            if t['transfer_to_account_id']:
                acc_desc = f"{t['account_name']} ➔ {t['transfer_account_name']}"
            else:
                acc_desc = t['account_name']
            self.table.setItem(row_idx, 3, QTableWidgetItem(acc_desc))

            # Описание
            self.table.setItem(row_idx, 4, QTableWidgetItem(t['description'] or ""))

            # Теги
            self.table.setItem(row_idx, 5, QTableWidgetItem(t['tags'] or ""))

            # Сумма
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
            self.table.setItem(row_idx, 6, amount_item)

            if is_subcategory_match:
                highlight = QColor("#332245")
                for col in range(self.table.columnCount()):
                    item = self.table.item(row_idx, col)
                    if item:
                        item.setBackground(highlight)

    def add_transaction(self):
        dialog = TransactionDialog(self.db, parent=self)
        if dialog.exec() == TransactionDialog.Accepted:
            self.refresh_data()
            self.data_changed.emit()

    def edit_transaction(self, *args):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Редактирование", "Выберите транзакцию из таблицы.")
            return

        t_id = int(self.table.item(row, 0).text())

        # Загружаем модель транзакции из БД
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, amount, currency, category_id, account_id, transfer_to_account_id, date, description, tags FROM transactions WHERE id = ?", (t_id,))
            r = cursor.fetchone()
            if r:
                t = Transaction(r['id'], r['amount'], r['currency'], r['category_id'], r['account_id'], r['transfer_to_account_id'], r['date'], r['description'], r['tags'])
                dialog = TransactionDialog(self.db, transaction=t, parent=self)
                if dialog.exec() == TransactionDialog.Accepted:
                    self.refresh_data()
                    self.data_changed.emit()

    def delete_transaction(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Удаление", "Выберите транзакцию для удаления.")
            return

        t_id = int(self.table.item(row, 0).text())
        reply = QMessageBox.question(self, "Удаление", "Вы действительно хотите удалить эту транзакцию и вернуть баланс счета?",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.db.delete_transaction(t_id):
                self.refresh_data()
                self.data_changed.emit()

    def export_to_csv(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить отчет", "", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            txs = self.db.get_transactions()
            with open(file_path, mode='w', encoding='utf-8-sig', newline='') as file:
                writer = csv.writer(file)
                # Пишем заголовки
                writer.writerow(["Дата", "Тип", "Сумма", "Валюта", "Категория", "Счет", "Перевод на счет", "Описание", "Теги"])
                for t in txs:
                    t_type = "Перевод" if t['transfer_to_account_id'] else ("Доход" if t['category_type'] == 'income' else "Расход")
                    writer.writerow([
                        t['date'],
                        t_type,
                        t['amount'],
                        t['currency'],
                        t['category_name'] or "",
                        t['account_name'] or "",
                        t['transfer_account_name'] or "",
                        t['description'] or "",
                        t['tags'] or ""
                    ])
            QMessageBox.information(self, "Экспорт", "Данные успешно экспортированы.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка экспорта", f"Не удалось сохранить файл:\n{e}")

    def import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть отчет для импорта", "", "CSV Files (*.csv)")
        if not file_path:
            return

        try:
            with open(file_path, mode='r', encoding='utf-8-sig') as file:
                reader = csv.reader(file)
                header = next(reader)

                imported_count = 0

                # Кэшируем категории и счета для ускорения работы
                categories = {c.name.lower(): c for c in self.db.get_categories()}
                accounts = {a.name.lower(): a for a in self.db.get_accounts()}

                for row in reader:
                    if len(row) < 9:
                        continue

                    date_str, t_type, amount_str, currency, cat_name, acc_name, trans_acc_name, desc, tags = row

                    try:
                        amount = float(amount_str)
                    except ValueError:
                        continue

                    # Ищем или создаем счета
                    acc_name_l = acc_name.lower()
                    if acc_name_l not in accounts:
                        # Создаем новый счет с RUB по умолчанию
                        acc_id = self.db.add_account(acc_name, 0.0, "RUB", "#607D8B")
                        # Обновляем кэш
                        accounts = {a.name.lower(): a for a in self.db.get_accounts()}
                    else:
                        acc_id = accounts[acc_name_l].id

                    transfer_to_id = None
                    if t_type == "Перевод" and trans_acc_name:
                        trans_acc_name_l = trans_acc_name.lower()
                        if trans_acc_name_l not in accounts:
                            transfer_to_id = self.db.add_account(trans_acc_name, 0.0, "RUB", "#607D8B")
                            accounts = {a.name.lower(): a for a in self.db.get_accounts()}
                        else:
                            transfer_to_id = accounts[trans_acc_name_l].id

                    category_id = None
                    if t_type != "Перевод" and cat_name:
                        cat_name_l = cat_name.lower()
                        if cat_name_l not in categories:
                            # Создаем категорию
                            db_type = "income" if t_type == "Доход" else "expense"
                            category_id = self.db.add_category(cat_name, db_type, "📁", "#9E9E9E")
                            categories = {c.name.lower(): c for c in self.db.get_categories()}
                        else:
                            category_id = categories[cat_name_l].id

                    # Создаем транзакцию
                    t = Transaction(
                        id=None,
                        amount=amount,
                        currency=currency,
                        category_id=category_id,
                        account_id=acc_id,
                        transfer_to_account_id=transfer_to_id,
                        date=date_str,
                        description=desc,
                        tags=tags
                    )
                    self.db.add_transaction(t)
                    imported_count += 1

                QMessageBox.information(self, "Импорт", f"Успешно импортировано транзакций: {imported_count}")
                self.refresh_data()
                self.data_changed.emit()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", f"Не удалось импортировать файл:\n{e}")
