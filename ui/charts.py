import matplotlib
matplotlib.use('QtAgg')

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy
from PySide6.QtCore import Qt
import numpy as np

class BaseChartWidget(QWidget):
    def __init__(self, parent=None, create_layout=True):
        super().__init__(parent)
        self.fig = Figure(facecolor='#1E1E1E')
        self.fig.subplots_adjust(left=0.12, right=0.96, top=0.88, bottom=0.16)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1E1E1E')
        
        if create_layout:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.canvas)

        # Базовая настройка шрифтов и цветов осей
        self.text_color = '#E0E0E0'
        self.grid_color = '#2C2C2C'
        
    def _apply_dark_style(self):
        self.ax.tick_params(colors=self.text_color, labelsize=9)
        self.ax.xaxis.label.set_color(self.text_color)
        self.ax.yaxis.label.set_color(self.text_color)
        for spine in self.ax.spines.values():
            spine.set_color(self.grid_color)
        self.ax.grid(True, color=self.grid_color, linestyle='--', alpha=0.5)

class PieChartWidget(BaseChartWidget):
    """Круговая диаграмма расходов по категориям"""
    def __init__(self, parent=None):
        super().__init__(parent, create_layout=False)
        self.categories = []
        self.amounts = []
        self.colors = []
        self.base_currency = ""
        self.wedges = []
        self.pinned_index = None
        self.hover_index = None
        self.row_widgets = []
        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.35", fc="#2A2A2A", ec="#3A3A3A"),
            color=self.text_color,
            fontsize=9,
        )
        self.annotation.set_visible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(4)

        self.list_scroll = QScrollArea()
        self.list_scroll.setWidgetResizable(True)
        self.list_scroll.setMinimumWidth(190)
        self.list_scroll.setMaximumWidth(300)
        self.list_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.list_scroll.setWidget(self.list_container)

        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.list_scroll, stretch=1)
        layout.addWidget(self.canvas, stretch=2)

        self.canvas.mpl_connect("motion_notify_event", self._on_motion)
        self.canvas.mpl_connect("button_press_event", self._on_click)

    def _clear_list(self):
        while self.list_layout.count():
            child = self.list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.row_widgets = []

    def _format_amount(self, amount):
        return f"{amount:,.2f} {self.base_currency}"

    def _build_list(self):
        self._clear_list()
        for idx, (category, amount, color) in enumerate(zip(self.categories, self.amounts, self.colors)):
            row = QFrame()
            row.setObjectName("PieLegendRow")
            row.setStyleSheet("QFrame#PieLegendRow { background: transparent; border-radius: 6px; }")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(6, 5, 6, 5)
            row_layout.setSpacing(7)

            marker = QLabel("●")
            marker.setStyleSheet(f"color: {color}; font-size: 14px;")
            name = QLabel(category)
            name.setWordWrap(True)
            name.setStyleSheet("color: #E0E0E0;")
            amount_lbl = QLabel(self._format_amount(amount))
            amount_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            amount_lbl.setStyleSheet("color: #FFFFFF; font-weight: 600;")

            row_layout.addWidget(marker)
            row_layout.addWidget(name, stretch=1)
            row_layout.addWidget(amount_lbl)
            self.list_layout.addWidget(row)
            self.row_widgets.append(row)

        self.list_layout.addStretch()

    def _set_active_index(self, index):
        self.hover_index = index
        for idx, row in enumerate(self.row_widgets):
            if idx == index:
                row.setStyleSheet("QFrame#PieLegendRow { background: rgba(138, 43, 226, 0.22); border-radius: 6px; }")
            else:
                row.setStyleSheet("QFrame#PieLegendRow { background: transparent; border-radius: 6px; }")

        for idx, wedge in enumerate(self.wedges):
            wedge.set_alpha(1.0 if index is None or idx == index else 0.45)

    def _show_annotation(self, index, event=None):
        if index == self.hover_index and index is None and not self.annotation.get_visible():
            return
        if index == self.hover_index and index is not None and self.annotation.get_visible():
            return

        if index is None:
            self.annotation.set_visible(False)
            self._set_active_index(None)
            self.canvas.draw_idle()
            return

        total = sum(self.amounts) or 1
        amount = self.amounts[index]
        percent = amount / total * 100
        self.annotation.set_text(f"{self.categories[index]}\n{self._format_amount(amount)}\n{percent:.1f}%")
        if event and event.xdata is not None and event.ydata is not None:
            self.annotation.xy = (event.xdata, event.ydata)
        else:
            wedge = self.wedges[index]
            angle = np.deg2rad((wedge.theta1 + wedge.theta2) / 2)
            self.annotation.xy = (np.cos(angle) * 0.65, np.sin(angle) * 0.65)
        self.annotation.set_visible(True)
        self._set_active_index(index)
        self.canvas.draw_idle()

    def _event_index(self, event):
        if event.inaxes != self.ax:
            return None
        for idx, wedge in enumerate(self.wedges):
            contains, _ = wedge.contains(event)
            if contains:
                return idx
        return None

    def _on_motion(self, event):
        if self.pinned_index is not None:
            return
        self._show_annotation(self._event_index(event), event)

    def _on_click(self, event):
        index = self._event_index(event)
        if index is None or index == self.pinned_index:
            self.pinned_index = None
            self._show_annotation(None)
            return
        self.pinned_index = index
        self._show_annotation(index, event)

    def draw_chart(self, categories: list, amounts: list, colors: list, base_currency: str):
        self.ax.clear()
        self.categories = categories
        self.amounts = amounts
        self.colors = colors
        self.base_currency = base_currency
        self.wedges = []
        self.pinned_index = None
        self._build_list()

        self.annotation = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.35", fc="#2A2A2A", ec="#3A3A3A"),
            color=self.text_color,
            fontsize=9,
        )
        self.annotation.set_visible(False)

        if not amounts:
            self.ax.text(0.5, 0.5, 'Нет данных о тратах за этот период', 
                         color=self.text_color, ha='center', va='center', fontsize=12)
            self.ax.set_axis_off()
            self.canvas.draw_idle()
            return

        self.ax.set_axis_on()

        def autopct(percent):
            return f"{percent:.1f}%" if percent >= 3 else ""
        
        wedges, _, autotexts = self.ax.pie(
            amounts, 
            labels=None,
            colors=colors, 
            autopct=autopct,
            startangle=90,
            pctdistance=0.75,
            textprops={'color': self.text_color, 'fontsize': 9},
            wedgeprops=dict(width=0.4, edgecolor='#1E1E1E', linewidth=2)
        )
        self.wedges = wedges
        
        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_color('#FFFFFF')
            
        self.ax.set_title("Расходы по категориям", color=self.text_color, fontsize=12, fontweight='bold')
        self.canvas.draw_idle()

class CumulativeSpendChartWidget(BaseChartWidget):
    """Линейный график накопленных трат против идеального бюджета"""
    def draw_chart(self, days: list, actual_spend: list, ideal_spend: list, planned_spend: list):
        self.ax.clear()
        self.ax.set_axis_on()
        self._apply_dark_style()

        actual_values = np.array([np.nan if value is None else value for value in actual_spend], dtype=float)
        
        self.ax.plot(days, ideal_spend, color='#A0A0A0', linestyle='--', label='Идеальный темп', linewidth=1.5)
        self.ax.plot(days, actual_values, color='#8A2BE2', label='Фактические траты', linewidth=2.5)
        self.ax.plot(days, planned_spend, color='#00BCD4', label='Планируемые траты', linewidth=2.0)
        
        self.ax.fill_between(days, actual_values, color='#8A2BE2', alpha=0.1)
        
        self.ax.set_title("Накопленные траты за месяц", color=self.text_color, fontsize=12, fontweight='bold')
        self.ax.set_xlabel("День месяца", color=self.text_color)
        self.ax.set_ylabel("Сумма", color=self.text_color)
        self.ax.set_xlim(1, max(days) if days else 31)
        self.ax.set_xticks(days)
        self.ax.tick_params(axis='x', labelsize=7)
        self.ax.legend(facecolor='#1E1E1E', edgecolor=self.grid_color, labelcolor=self.text_color)
        
        self.canvas.draw_idle()

class MonthlyBarChartWidget(BaseChartWidget):
    """Столбчатый график сравнения месяцев за 6 месяцев"""
    def draw_chart(self, months: list, incomes: list, expenses: list):
        self.ax.clear()
        self.ax.set_axis_on()
        self._apply_dark_style()
        
        if not months:
            self.ax.text(0.5, 0.5, 'Нет исторических данных', 
                         color=self.text_color, ha='center', va='center', fontsize=12)
            self.ax.set_axis_off()
            self.canvas.draw_idle()
            return
            
        x = np.arange(len(months))
        width = 0.35
        
        # Столбцы доходов и расходов
        self.ax.bar(x - width/2, incomes, width, label='Доходы', color='#00E676')
        self.ax.bar(x + width/2, expenses, width, label='Расходы', color='#F44336')
        
        self.ax.set_title("Сравнение доходов и расходов", color=self.text_color, fontsize=12, fontweight='bold')
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(months, color=self.text_color)
        self.ax.legend(facecolor='#1E1E1E', edgecolor=self.grid_color, labelcolor=self.text_color)
        
        self.canvas.draw_idle()
