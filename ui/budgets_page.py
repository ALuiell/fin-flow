from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QScrollArea, QProgressBar, 
                             QInputDialog, QMessageBox, QGridLayout)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from database.db_manager import DBManager
from datetime import date

class BudgetsPage(QWidget):
    data_changed = Signal()

    def __init__(self, db: DBManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # Заголовок
        header = QLabel("Месячные лимиты по категориям трат")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #FFFFFF;")
        main_layout.addWidget(header)

        # Прокручиваемая область с карточками категорий
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.scroll_content = QWidget()
        scroll.setWidget(self.scroll_content)
        
        self.grid = QGridLayout(self.scroll_content)
        self.grid.setSpacing(15)
        
        main_layout.addWidget(scroll)
        self.refresh_data()

    def refresh_data(self):
        # Очищаем сетку
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        current_month = date.today().strftime("%Y-%m")
        base_currency = self.db.get_setting("base_currency", "RUB")
        
        # Получаем установленные бюджеты
        budgets_list = self.db.get_budgets(current_month)
        # Индексируем их по category_id
        budgets = {b['category_id']: b for b in budgets_list}
        
        # Получаем все расходные категории
        all_categories = self.db.get_categories()
        expense_categories = [c for c in all_categories if c.type == 'expense']

        row, col = 0, 0
        for cat in expense_categories:
            card = QFrame()
            card.setObjectName("CardFrame")
            card.setMinimumWidth(260)
            
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 15, 15, 15)
            card_layout.setSpacing(10)

            # Верхняя строка: Иконка, Имя
            top_layout = QHBoxLayout()
            icon_lbl = QLabel(cat.icon or "📁")
            icon_lbl.setStyleSheet(f"font-size: 24px; padding: 4px; background-color: rgba(255,255,255,0.05); border-radius: 6px;")
            
            name_lbl = QLabel(cat.name)
            name_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #FFFFFF;")
            
            top_layout.addWidget(icon_lbl)
            top_layout.addWidget(name_lbl)
            top_layout.addStretch()
            
            # Кружок цвета категории
            color_dot = QLabel("●")
            color_dot.setStyleSheet(f"color: {cat.color}; font-size: 14px;")
            top_layout.addWidget(color_dot)
            
            card_layout.addLayout(top_layout)

            # Если бюджет установлен
            if cat.id in budgets:
                b = budgets[cat.id]
                limit = b['amount_limit']
                spent = b['spent']
                
                # Считаем процент расхода
                percent = int((spent / limit) * 100) if limit > 0 else 100
                percent_clamped = min(100, percent)
                
                info_lbl = QLabel(f"Лимит: {limit:,.0f} {b['currency']}")
                info_lbl.setStyleSheet("font-weight: bold; color: #A0A0A0;")
                
                spent_lbl = QLabel(f"Потрачено: {spent:,.2f} {b['currency']} ({percent}%)")
                
                # Прогресс-бар
                progress = QProgressBar()
                progress.setValue(percent_clamped)
                
                # Меняем цвет прогресс-бара в зависимости от перерасхода
                if percent >= 100:
                    progress.setStyleSheet("QProgressBar::chunk { background-color: #F44336; }") # Красный
                    spent_lbl.setStyleSheet("color: #F44336; font-weight: 600;")
                elif percent >= 80:
                    progress.setStyleSheet("QProgressBar::chunk { background-color: #FF9800; }") # Оранжевый
                    spent_lbl.setStyleSheet("color: #FF9800;")
                else:
                    progress.setStyleSheet("QProgressBar::chunk { background-color: #4CAF50; }") # Зеленый
                    spent_lbl.setStyleSheet("color: #E0E0E0;")
                
                card_layout.addWidget(info_lbl)
                card_layout.addWidget(progress)
                card_layout.addWidget(spent_lbl)

                # Кнопки редактирования/удаления
                btn_lay = QHBoxLayout()
                edit_btn = QPushButton("Изменить лимит")
                edit_btn.setObjectName("SecondaryButton")
                edit_btn.clicked.connect(lambda ch=False, cid=cat.id, lim=limit, cur=b['currency']: self.set_limit(cid, lim, cur))
                
                del_btn = QPushButton("Убрать")
                del_btn.setObjectName("DangerButton")
                del_btn.setStyleSheet("padding: 5px;")
                del_btn.clicked.connect(lambda ch=False, bid=b['id']: self.remove_budget(bid))
                
                btn_lay.addWidget(edit_btn, stretch=2)
                btn_lay.addWidget(del_btn, stretch=1)
                card_layout.addLayout(btn_lay)
            else:
                # Бюджет не установлен
                no_budget_lbl = QLabel("Лимит не установлен")
                no_budget_lbl.setStyleSheet("color: #666666; font-style: italic;")
                
                set_btn = QPushButton("Установить лимит")
                set_btn.setObjectName("PrimaryButton")
                set_btn.clicked.connect(lambda ch=False, cid=cat.id: self.set_limit(cid, 0, base_currency))
                
                card_layout.addWidget(no_budget_lbl)
                card_layout.addStretch()
                card_layout.addWidget(set_btn)

            self.grid.addWidget(card, row, col)
            col += 1
            if col > 2: # 3 карточки в ряд
                col = 0
                row += 1

    def set_limit(self, category_id: int, current_limit: float, currency: str):
        limit, ok = QInputDialog.getDouble(
            self, "Установка лимита", 
            "Введите месячный лимит трат для этой категории:", 
            current_limit, 0, 99999999, 2
        )
        if ok and limit > 0:
            current_month = date.today().strftime("%Y-%m")
            if self.db.add_or_update_budget(category_id, limit, currency, current_month):
                self.refresh_data()
                self.data_changed.emit()

    def remove_budget(self, budget_id: int):
        reply = QMessageBox.question(self, "Удаление лимита", "Вы уверены, что хотите удалить лимит трат?",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.delete_budget(budget_id):
                self.refresh_data()
                self.data_changed.emit()
