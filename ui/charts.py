import matplotlib
matplotlib.use('QtAgg')

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QWidget, QVBoxLayout
import numpy as np

class BaseChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = Figure(facecolor='#1E1E1E', tight_layout=True)
        self.canvas = FigureCanvas(self.fig)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_facecolor('#1E1E1E')
        
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
    def draw_chart(self, categories: list, amounts: list, colors: list):
        self.ax.clear()
        if not amounts:
            self.ax.text(0.5, 0.5, 'Нет данных о тратах за этот период', 
                         color=self.text_color, ha='center', va='center', fontsize=12)
            self.ax.set_axis_off()
            self.canvas.draw()
            return

        self.ax.set_axis_on()
        
        # Нарисуем круговую диаграмму (donut chart для современного вида)
        wedges, texts, autotexts = self.ax.pie(
            amounts, 
            labels=categories, 
            colors=colors, 
            autopct='%1.1f%%', 
            startangle=90,
            pctdistance=0.75,
            textprops={'color': self.text_color, 'fontsize': 9},
            wedgeprops=dict(width=0.4, edgecolor='#1E1E1E', linewidth=2) # Donut style
        )
        
        # Сделаем проценты внутри жирными
        for autotext in autotexts:
            autotext.set_fontweight('bold')
            autotext.set_color('#FFFFFF')
            
        self.ax.set_title("Расходы по категориям", color=self.text_color, fontsize=12, fontweight='bold')
        self.canvas.draw()

class CumulativeSpendChartWidget(BaseChartWidget):
    """Линейный график накопленных трат против идеального бюджета"""
    def draw_chart(self, days: list, actual_spend: list, ideal_spend: list):
        self.ax.clear()
        self.ax.set_axis_on()
        self._apply_dark_style()
        
        # Отрисовка линий
        self.ax.plot(days, ideal_spend, color='#A0A0A0', linestyle='--', label='Идеальный темп', linewidth=1.5)
        self.ax.plot(days, actual_spend, color='#8A2BE2', label='Фактические траты', linewidth=2.5)
        
        # Заполнение под линиями для глубины
        self.ax.fill_between(days, actual_spend, color='#8A2BE2', alpha=0.1)
        
        self.ax.set_title("Накопленные траты за месяц", color=self.text_color, fontsize=12, fontweight='bold')
        self.ax.set_xlabel("День месяца", color=self.text_color)
        self.ax.set_ylabel("Сумма", color=self.text_color)
        self.ax.legend(facecolor='#1E1E1E', edgecolor=self.grid_color, labelcolor=self.text_color)
        
        self.canvas.draw()

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
            self.canvas.draw()
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
        
        self.canvas.draw()
