from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea,
    QSplitter, QPushButton, QButtonGroup, QDateEdit, QSizePolicy
)

from database.db_manager import DBManager
from ui.charts import PieChartWidget, CumulativeSpendChartWidget, MonthlyBarChartWidget
from utils.analytics_helper import (
    get_analytics_summary,
    get_days_in_month,
    get_period_bounds,
    build_cumulative_spend_series,
)


class AnalyticsPage(QWidget):
    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self._last_refresh_key = None
        self._last_cumulative_key = None
        self._last_bar_key = None
        self.init_ui()

    def init_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        scroll.setWidget(container)

        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        filter_card = QFrame()
        filter_card.setObjectName("CardFrame")
        filter_layout = QHBoxLayout(filter_card)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setSpacing(8)

        self.month_btn = QPushButton("Месяц")
        self.day_btn = QPushButton("День")
        for btn in (self.month_btn, self.day_btn):
            btn.setCheckable(True)
            btn.setObjectName("SecondaryButton")
            btn.setMinimumWidth(80)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.month_btn)
        self.mode_group.addButton(self.day_btn)
        self.month_btn.setChecked(True)
        self.mode_group.buttonClicked.connect(self.refresh_data)

        self.date_filter = QDateEdit()
        self.date_filter.setCalendarPopup(True)
        self.date_filter.setDate(QDate.currentDate())
        self.date_filter.dateChanged.connect(self.refresh_data)

        filter_layout.addWidget(QLabel("Период:"))
        filter_layout.addWidget(self.month_btn)
        filter_layout.addWidget(self.day_btn)
        filter_layout.addSpacing(10)
        filter_layout.addWidget(QLabel("Дата:"))
        filter_layout.addWidget(self.date_filter)
        filter_layout.addStretch()
        main_layout.addWidget(filter_card)

        self.insights_splitter = QSplitter(Qt.Horizontal)
        self.insights_splitter.setChildrenCollapsible(False)
        self.insights_splitter.addWidget(self._create_projection_card())
        self.insights_splitter.addWidget(self._create_avg_card())
        self.insights_splitter.addWidget(self._create_day_card())
        self.insights_splitter.setSizes([330, 330, 330])
        main_layout.addWidget(self.insights_splitter)

        self.charts_splitter = QSplitter(Qt.Vertical)
        self.charts_splitter.setChildrenCollapsible(False)

        top_charts = QSplitter(Qt.Horizontal)
        top_charts.setChildrenCollapsible(False)
        top_charts.addWidget(self._create_pie_card())
        top_charts.addWidget(self._create_cumulative_card())
        top_charts.setSizes([560, 500])

        self.charts_splitter.addWidget(top_charts)
        self.charts_splitter.addWidget(self._create_bar_card())
        self.charts_splitter.setSizes([380, 330])
        main_layout.addWidget(self.charts_splitter, stretch=1)

        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addWidget(scroll)

        self.refresh_data()

    def _create_projection_card(self):
        self.prog_card = QFrame()
        self.prog_card.setObjectName("CardFrame")
        self.prog_card.setMinimumSize(240, 120)
        self.prog_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(self.prog_card)
        self.prog_title = QLabel("Прогноз трат на конец месяца")
        self.prog_title.setObjectName("CardTitle")
        self.prog_title.setWordWrap(True)
        self.prog_value = QLabel("0.00 RUB")
        self.prog_value.setObjectName("CardValue")
        self.prog_value.setWordWrap(True)
        self.prog_desc = QLabel("На основе темпа за этот месяц")
        self.prog_desc.setWordWrap(True)
        self.prog_desc.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.prog_title)
        layout.addWidget(self.prog_value)
        layout.addWidget(self.prog_desc)
        layout.addStretch()
        return self.prog_card

    def _create_avg_card(self):
        self.avg_card = QFrame()
        self.avg_card.setObjectName("CardFrame")
        self.avg_card.setMinimumSize(220, 120)
        self.avg_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(self.avg_card)
        self.avg_title = QLabel("Средний чек покупки")
        self.avg_title.setObjectName("CardTitle")
        self.avg_title.setWordWrap(True)
        self.avg_value = QLabel("0.00 RUB")
        self.avg_value.setObjectName("CardValue")
        self.avg_value.setWordWrap(True)
        self.avg_desc = QLabel("Всего трат: 0 шт.")
        self.avg_desc.setWordWrap(True)
        self.avg_desc.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.avg_title)
        layout.addWidget(self.avg_value)
        layout.addWidget(self.avg_desc)
        layout.addStretch()
        return self.avg_card

    def _create_day_card(self):
        self.day_card = QFrame()
        self.day_card.setObjectName("CardFrame")
        self.day_card.setMinimumSize(220, 120)
        self.day_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(self.day_card)
        self.day_title = QLabel("Пиковый день трат")
        self.day_title.setObjectName("CardTitle")
        self.day_title.setWordWrap(True)
        self.day_value = QLabel("Нет данных")
        self.day_value.setObjectName("CardValue")
        self.day_value.setWordWrap(True)
        self.day_value.setStyleSheet("color: #FF5252;")
        self.day_desc = QLabel("0.00 RUB")
        self.day_desc.setWordWrap(True)
        self.day_desc.setStyleSheet("color: #888888; font-size: 11px;")
        layout.addWidget(self.day_title)
        layout.addWidget(self.day_value)
        layout.addWidget(self.day_desc)
        layout.addStretch()
        return self.day_card

    def _create_pie_card(self):
        pie_card = QFrame()
        pie_card.setObjectName("CardFrame")
        pie_card.setMinimumSize(500, 330)
        layout = QVBoxLayout(pie_card)
        layout.setContentsMargins(12, 12, 12, 12)
        self.pie_widget = PieChartWidget()
        layout.addWidget(self.pie_widget)
        return pie_card

    def _create_cumulative_card(self):
        cum_card = QFrame()
        cum_card.setObjectName("CardFrame")
        cum_card.setMinimumSize(400, 330)
        layout = QVBoxLayout(cum_card)
        layout.setContentsMargins(12, 12, 12, 12)
        self.cum_widget = CumulativeSpendChartWidget()
        layout.addWidget(self.cum_widget)
        return cum_card

    def _create_bar_card(self):
        bar_card = QFrame()
        bar_card.setObjectName("CardFrame")
        bar_card.setMinimumSize(600, 300)
        layout = QVBoxLayout(bar_card)
        layout.setContentsMargins(12, 12, 12, 12)
        self.bar_widget = MonthlyBarChartWidget()
        layout.addWidget(self.bar_widget)
        return bar_card

    def _selected_date(self):
        return self.date_filter.date().toPython()

    def _mode(self):
        return "day" if self.day_btn.isChecked() else "month"

    def refresh_data(self, *args, force=False, **kwargs):
        base_currency = self.db.get_setting("base_currency", "RUB")
        selected_date = self._selected_date()
        mode = self._mode()
        refresh_key = (
            self.db.revision,
            base_currency,
            selected_date.isoformat(),
            mode,
        )
        if not force and refresh_key == self._last_refresh_key:
            return
        self._last_refresh_key = refresh_key

        period_start, period_end = get_period_bounds(selected_date, mode)
        period_txs = self.db.get_transactions(start_date=period_start, end_date=period_end)

        summary = get_analytics_summary(
            self.db,
            selected_date,
            mode,
            transactions=period_txs,
            base_currency=base_currency,
        )
        self._update_cards(summary, base_currency, selected_date, mode)
        self.draw_pie_chart(base_currency, period_txs)
        self.draw_cumulative_chart(base_currency, selected_date, period_txs if mode == "month" else None)
        self.draw_monthly_bar_chart(base_currency, selected_date)

    def _update_cards(self, summary, base_currency, selected_date, mode):
        if mode == "day":
            self.prog_title.setText("Траты за выбранный день")
            self.prog_value.setText(f"{summary['total_expense']:,.2f} {base_currency}")
            self.prog_desc.setText(selected_date.strftime("%d.%m.%Y"))
            self.prog_desc.setStyleSheet("color: #888888; font-size: 11px;")
            self.avg_desc.setText(f"Всего трат за день: {summary['transaction_count']} шт.")
            self.day_title.setText("День недели")
        else:
            self.prog_title.setText("Прогноз трат на конец месяца")
            self.prog_value.setText(f"{summary['projected_expense']:,.2f} {base_currency}")
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
            self.avg_desc.setText(f"Всего трат за месяц: {summary['transaction_count']} шт.")
            self.day_title.setText("Пиковый день трат")

        self.avg_value.setText(f"{summary['avg_check']:,.2f} {base_currency}")
        self.day_value.setText(summary['top_weekday'])
        self.day_desc.setText(f"Потрачено: {summary['top_weekday_sum']:,.2f} {base_currency}")

    def draw_pie_chart(self, base_currency, txs):
        cat_sums = {}
        cat_colors = {}
        for t in txs:
            if t['category_type'] == 'expense' and t['transfer_to_account_id'] is None:
                cat_name = t['category_name'] or "Без категории"
                amount_base = self.db.convert_amount(t['amount'], t['currency'], base_currency)
                cat_sums[cat_name] = cat_sums.get(cat_name, 0.0) + amount_base
                cat_colors[cat_name] = t['category_color'] or "#9E9E9E"

        sorted_items = sorted(cat_sums.items(), key=lambda item: item[1], reverse=True)
        categories = [name for name, _ in sorted_items]
        amounts = [amount for _, amount in sorted_items]
        colors = [cat_colors[name] for name in categories]

        self.pie_widget.draw_chart(categories, amounts, colors, base_currency)

    def draw_cumulative_chart(self, base_currency, selected_date, month_txs=None):
        year, month = selected_date.year, selected_date.month
        chart_key = (self.db.revision, base_currency, year, month)
        if chart_key == self._last_cumulative_key:
            return
        self._last_cumulative_key = chart_key

        days_in_month = get_days_in_month(year, month)
        if month_txs is None:
            start = f"{year}-{month:02d}-01"
            end = f"{year}-{month:02d}-{days_in_month:02d}"
            month_txs = self.db.get_transactions(start_date=start, end_date=end)

        try:
            planned_income = float(self.db.get_setting("planned_monthly_income", "50000"))
        except ValueError:
            planned_income = 50000.0

        series = build_cumulative_spend_series(
            month_txs,
            self.db.get_subscriptions(),
            year,
            month,
            planned_income,
            self.db.convert_amount,
            base_currency,
        )
        self.cum_widget.draw_chart(
            series["days"],
            series["actual_spend"],
            series["ideal_spend"],
            series["planned_spend"],
        )

    def draw_monthly_bar_chart(self, base_currency, selected_date):
        chart_key = (self.db.revision, base_currency, selected_date.year, selected_date.month)
        if chart_key == self._last_bar_key:
            return
        self._last_bar_key = chart_key

        month_names = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
        months_data = []
        incomes = []
        expenses = []

        for i in range(5, -1, -1):
            m = selected_date.month - i
            y = selected_date.year
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

            months_data.append(f"{month_names[m - 1]} {y % 100}")
            incomes.append(monthly_inc)
            expenses.append(monthly_exp)

        self.bar_widget.draw_chart(months_data, incomes, expenses)
