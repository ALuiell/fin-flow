from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QCalendarWidget, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFrame)
from PySide6.QtCore import Qt, QDate, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QTextCharFormat
from database.db_manager import DBManager
from utils.formatting import format_money
from datetime import datetime, date

class ExpenseCalendar(QCalendarWidget):
    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.base_currency = db.get_setting("base_currency", "RUB")
        self.expense_cache = {}
        
        # Month change signal
        self.currentPageChanged.connect(self.load_month_expenses)
        
        # Initial run
        self.load_month_expenses(self.yearShown(), self.monthShown())
        self.setStyleSheet("QCalendarWidget QAbstractItemView { font-size: 14px; }")
        self._apply_weekend_format()

    def _apply_weekend_format(self):
        weekend_format = QTextCharFormat()
        weekend_format.setForeground(QColor("#FF5252"))
        weekend_format.setFontPointSize(10)
        self.setWeekdayTextFormat(Qt.Saturday, weekend_format)
        self.setWeekdayTextFormat(Qt.Sunday, weekend_format)

    def load_month_expenses(self, year: int, month: int):
        self.expense_cache.clear()
        self.base_currency = self.db.get_setting("base_currency", "RUB")
        
        # Find the first and last day of the month
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        start_str = f"{year}-{month:02d}-01"
        end_str = f"{year}-{month:02d}-{last_day:02d}"
        
        # Get all transactions for the month
        txs = self.db.get_transactions(start_date=start_str, end_date=end_str)
        
        # Calculate the sum of expenses by day
        for t in txs:
            if t['transfer_to_account_id'] is not None:
                continue # Ignore internal transfers
            
            if t['category_type'] == 'expense':
                t_date = t['date'] # YYYY-MM-DD
                amount_base = self.db.convert_amount(t['amount'], t['currency'], self.base_currency)
                self.expense_cache[t_date] = self.expense_cache.get(t_date, 0.0) + amount_base
                
        self.updateCell(QDate(year, month, 1)) # Force redraw

    def paintCell(self, painter: QPainter, rect: QRect, qdate: QDate):
        # Draw the standard cell
        super().paintCell(painter, rect, qdate)
        
        # Format the date to check against the cache
        date_str = f"{qdate.year()}-{qdate.month():02d}-{qdate.day():02d}"
        
        if date_str in self.expense_cache:
            spent = self.expense_cache[date_str]
            if spent > 0:
                painter.save()
                
                # Text color for expenses (neon-red/pink)
                painter.setPen(QColor("#FF4D4D"))
                
                font = painter.font()
                font.setPointSize(8)
                font.setBold(True)
                painter.setFont(font)
                
                # Draw the expense amount at the bottom of the cell
                text_rect = QRect(rect.x(), rect.y() + rect.height() - 17, rect.width(), 15)
                
                # Format the amount to save space
                if spent >= 1000:
                    val_str = f"-{spent/1000:.1f}k"
                else:
                    val_str = f"-{int(spent)}"
                    
                painter.drawText(text_rect, Qt.AlignCenter, val_str)
                painter.restore()


class CalendarPage(QWidget):
    data_changed = Signal()

    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Calendar
        self.calendar = ExpenseCalendar(self.db, self)
        self.calendar.clicked.connect(self.on_date_selected)
        
        # Set the minimum size of the calendar
        self.calendar.setMinimumHeight(350)
        layout.addWidget(self.calendar, stretch=2)

        # Detail panel for transactions on the selected day
        details_card = QFrame()
        details_card.setObjectName("CardFrame")
        details_layout = QVBoxLayout(details_card)
        details_layout.setContentsMargins(15, 15, 15, 15)

        self.date_label = QLabel("Операции за день")
        self.date_label.setObjectName("CardTitle")
        details_layout.addWidget(self.date_label)

        self.tx_table = QTableWidget()
        self.tx_table.setColumnCount(4)
        self.tx_table.setHorizontalHeaderLabels(["Категория", "Счет", "Описание", "Сумма"])
        self.tx_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tx_table.setColumnWidth(0, 250)
        self.tx_table.setColumnWidth(1, 200)
        self.tx_table.setColumnWidth(2, 350)
        self.tx_table.setColumnWidth(3, 120)
        self.tx_table.verticalHeader().setVisible(False)
        self.tx_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tx_table.setSelectionBehavior(QTableWidget.SelectRows)
        details_layout.addWidget(self.tx_table)

        layout.addWidget(details_card, stretch=1)

        # Select current date by default
        self.on_date_selected(self.calendar.selectedDate())

    def refresh_data(self):
        # Update calendar
        self.calendar.load_month_expenses(self.calendar.yearShown(), self.calendar.monthShown())
        self.calendar.updateCells()
        # Update table for selected day
        self.on_date_selected(self.calendar.selectedDate())

    def on_date_selected(self, qdate: QDate):
        date_str = f"{qdate.year()}-{qdate.month():02d}-{qdate.day():02d}"
        self.date_label.setText(f"Операции за {qdate.toString('d MMMM yyyy')}")

        # Get transactions for the selected day
        txs = self.db.get_transactions(start_date=date_str, end_date=date_str)
        self.tx_table.setRowCount(len(txs))

        for row_idx, t in enumerate(txs):
            # Category
            if t['transfer_to_account_id']:
                cat_desc = f"🔄 Перевод на {t['transfer_account_name']}"
            else:
                cat_desc = f"{t['category_icon']} {t['category_name']}"
            self.tx_table.setItem(row_idx, 0, QTableWidgetItem(cat_desc))

            # Account
            self.tx_table.setItem(row_idx, 1, QTableWidgetItem(t['account_name']))

            # Description
            self.tx_table.setItem(row_idx, 2, QTableWidgetItem(t['description'] or ""))

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
