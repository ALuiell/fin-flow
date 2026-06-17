from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QFrame, QGridLayout, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from database.db_manager import DBManager
from utils.analytics_helper import get_analytics_summary, get_days_in_month
from ui.charts import PieChartWidget, CumulativeSpendChartWidget, MonthlyBarChartWidget
from datetime import datetime, date

class AnalyticsPage(QWidget):
    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        # Нам нужен прокручиваемый экран, так как графиков много
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        container = QWidget()
        scroll.setWidget(container)
        
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # 1. Верхний блок: Карточки с инсайтами и прогнозами
        insights_layout = QHBoxLayout()
        insights_layout.setSpacing(15)

        # Прогноз расходов
        self.prog_card = QFrame()
        self.prog_card.setObjectName("CardFrame")
        prog_lay = QVBoxLayout(self.prog_card)
        prog_title = QLabel("Прогноз трат на конец месяца")
        prog_title.setObjectName("CardTitle")
        self.prog_value = QLabel("0.00 RUB")
        self.prog_value.setObjectName("CardValue")
        self.prog_desc = QLabel("На основе темпа за этот месяц")
        self.prog_desc.setStyleSheet("color: #888888; font-size: 11px;")
        prog_lay.addWidget(prog_title)
        prog_lay.addWidget(self.prog_value)
        prog_lay.addWidget(self.prog_desc)
        insights_layout.addWidget(self.prog_card)

        # Средний чек
        self.avg_card = QFrame()
        self.avg_card.setObjectName("CardFrame")
        avg_lay = QVBoxLayout(self.avg_card)
        avg_title = QLabel("Средний чек покупки")
        avg_title.setObjectName("CardTitle")
        self.avg_value = QLabel("0.00 RUB")
        self.avg_value.setObjectName("CardValue")
        self.avg_desc = QLabel("Всего транзакций: 0")
        self.avg_desc.setStyleSheet("color: #888888; font-size: 11px;")
        avg_lay.addWidget(avg_title)
        avg_lay.addWidget(self.avg_value)
        avg_lay.addWidget(self.avg_desc)
        insights_layout.addWidget(self.avg_card)

        # Самый дорогой день недели
        self.day_card = QFrame()
        self.day_card.setObjectName("CardFrame")
        day_lay = QVBoxLayout(self.day_card)
        day_title = QLabel("Пиковый день трат")
        day_title.setObjectName("CardTitle")
        self.day_value = QLabel("Воскресенье")
        self.day_value.setObjectName("CardValue")
        self.day_value.setStyleSheet("color: #FF5252;")
        self.day_desc = QLabel("0.00 RUB")
        self.day_desc.setStyleSheet("color: #888888; font-size: 11px;")
        day_lay.addWidget(day_title)
        day_lay.addWidget(self.day_value)
        day_lay.addWidget(self.day_desc)
        insights_layout.addWidget(self.day_card)

        main_layout.addLayout(insights_layout)

        # 2. Блок графиков (Grid)
        charts_layout = QGridLayout()
        charts_layout.setSpacing(15)

        # 2.1 Круговой график категорий расходов
        self.pie_widget = PieChartWidget()
        self.pie_widget.setMinimumHeight(320)
        pie_card = QFrame()
        pie_card.setObjectName("CardFrame")
        pie_lay = QVBoxLayout(pie_card)
        pie_lay.addWidget(self.pie_widget)
        charts_layout.addWidget(pie_card, 0, 0)

        # 2.2 График кумулятивного расхода (идеальный темп трат)
        self.cum_widget = CumulativeSpendChartWidget()
        self.cum_widget.setMinimumHeight(320)
        cum_card = QFrame()
        cum_card.setObjectName("CardFrame")
        cum_lay = QVBoxLayout(cum_card)
        cum_lay.addWidget(self.cum_widget)
        charts_layout.addWidget(cum_card, 0, 1)

        # 2.3 Столбчатый график сравнения месяцев
        self.bar_widget = MonthlyBarChartWidget()
        self.bar_widget.setMinimumHeight(320)
        bar_card = QFrame()
        bar_card.setObjectName("CardFrame")
        bar_lay = QVBoxLayout(bar_card)
        bar_lay.addWidget(self.bar_widget)
        charts_layout.addWidget(bar_card, 1, 0, 1, 2) # растягиваем на две колонки

        main_layout.addLayout(charts_layout)

        # Главный макет страницы
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self.refresh_data()

    def refresh_data(self):
        base_currency = self.db.get_setting("base_currency", "RUB")
        
        # 1. Загружаем инсайты
        summary = get_analytics_summary(self.db)
        
        # Обновляем виджеты инсайтов
        self.prog_value.setText(f"{summary['projected_expense']:,.2f} {base_currency}")
        
        # Сравнение с прошлым месяцем
        diff = summary['diff_percent']
        if diff > 0:
            self.prog_desc.setText(f"📈 На {diff}% БОЛЬШЕ трат, чем в прошлом месяце")
            self.prog_desc.setStyleSheet("color: #FF5252; font-size: 11px;")
        elif diff < 0:
            self.prog_desc.setText(f"📉 На {abs(diff)}% МЕНЬШЕ трат, чем в прошлом месяце")
            self.prog_desc.setStyleSheet("color: #00E676; font-size: 11px;")
        else:
            self.prog_desc.setText("Траты на уровне прошлого месяца")
            self.prog_desc.setStyleSheet("color: #888888; font-size: 11px;")

        # Средний чек
        self.avg_value.setText(f"{summary['avg_check']:,.2f} {base_currency}")
        # Получаем количество операций
        today = date.today()
        start = f"{today.year}-{today.month:02d}-01"
        tx_count = len([t for t in self.db.get_transactions(start_date=start) if t['category_type'] == 'expense' and t['transfer_to_account_id'] is None])
        self.avg_desc.setText(f"Всего трат за месяц: {tx_count} шт.")

        # Пиковый день
        self.day_value.setText(summary['top_weekday'])
        self.day_desc.setText(f"Потрачено: {summary['top_weekday_sum']:,.2f} {base_currency}")

        # 2. Отрисовка графиков
        # 2.1 Круговой график
        self.draw_pie_chart(base_currency)
        
        # 2.2 График кумулятивного расхода
        self.draw_cumulative_chart(base_currency)

        # 2.3 Столбчатый график месяцев
        self.draw_monthly_bar_chart(base_currency)

    def draw_pie_chart(self, base_currency):
        today = date.today()
        start = f"{today.year}-{today.month:02d}-01"
        txs = self.db.get_transactions(start_date=start)
        
        cat_sums = {}
        cat_colors = {}
        for t in txs:
            if t['category_type'] == 'expense' and t['transfer_to_account_id'] is None:
                cat_name = t['category_name']
                amount_base = self.db.convert_amount(t['amount'], t['currency'], base_currency)
                cat_sums[cat_name] = cat_sums.get(cat_name, 0.0) + amount_base
                cat_colors[cat_name] = t['category_color'] or "#9E9E9E"
                
        categories = list(cat_sums.keys())
        amounts = list(cat_sums.values())
        colors = [cat_colors[name] for name in categories]
        
        self.pie_widget.draw_chart(categories, amounts, colors)

    def draw_cumulative_chart(self, base_currency):
        today = date.today()
        year, month = today.year, today.month
        days_in_month = get_days_in_month(year, month)
        
        start = f"{year}-{month:02d}-01"
        txs = self.db.get_transactions(start_date=start)
        
        # Собираем траты по дням
        daily_spends = {d: 0.0 for d in range(1, days_in_month + 1)}
        for t in txs:
            if t['category_type'] == 'expense' and t['transfer_to_account_id'] is None:
                t_date = datetime.strptime(t['date'], "%Y-%m-%d").date()
                amount_base = self.db.convert_amount(t['amount'], t['currency'], base_currency)
                daily_spends[t_date.day] += amount_base
                
        # Строим кумулятивную сумму
        actual_spend = []
        current_sum = 0.0
        # Для дней после сегодняшнего не рисуем линию, чтобы график обрывался на "сегодня"
        for d in range(1, days_in_month + 1):
            current_sum += daily_spends[d]
            if d <= today.day:
                actual_spend.append(current_sum)
            else:
                # Оставляем None для графиков в будущем
                break

        days_actual = list(range(1, len(actual_spend) + 1))
        
        # Идеальный темп
        try:
            planned_income = float(self.db.get_setting("planned_monthly_income", "50000"))
        except ValueError:
            planned_income = 50000.0
            
        days_all = list(range(1, days_in_month + 1))
        ideal_spend = [(planned_income / days_in_month) * d for d in days_all]
        
        self.cum_widget.draw_chart(days_actual, actual_spend, ideal_spend[:len(actual_spend)])

    def draw_monthly_bar_chart(self, base_currency):
        # Достаем последние 6 месяцев
        import calendar
        month_names = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
        
        today = date.today()
        months_data = []
        incomes = []
        expenses = []
        
        # Получаем данные за последние 6 месяцев в хронологическом порядке
        for i in range(5, -1, -1):
            m = today.month - i
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
                
            last_day = get_days_in_month(y, m)
            start = f"{y}-{m:02d}-01"
            end = f"{y}-{m:02d}-{last_day:02d}"
            
            txs = self.db.get_transactions(start_date=start, end_date=end)
            
            monthly_inc = 0.0
            monthly_exp = 0.0
            
            for t in txs:
                if t['transfer_to_account_id'] is not None:
                    continue
                amount_base = self.db.convert_amount(t['amount'], t['currency'], base_currency)
                if t['category_type'] == 'income':
                    monthly_inc += amount_base
                elif t['category_type'] == 'expense':
                    monthly_exp += amount_base
                    
            months_data.append(f"{month_names[m-1]} {y % 100}")
            incomes.append(monthly_inc)
            expenses.append(monthly_exp)
            
        self.bar_widget.draw_chart(months_data, incomes, expenses)
