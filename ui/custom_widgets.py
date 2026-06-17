from PySide6.QtWidgets import (QComboBox, QLineEdit, QWidget, QHBoxLayout, 
                             QVBoxLayout, QLabel, QPushButton, QFrame, QMenu, 
                             QWidgetAction, QListWidget, QListWidgetItem)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QStandardItemModel

class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineEdit(QLineEdit())
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setPlaceholderText("Все...")
        self.lineEdit().setStyleSheet("QLineEdit { border: none; background: transparent; padding-left: 5px; }")
        self.view().pressed.connect(self.handle_item_pressed)
        self.setModel(QStandardItemModel(self))
        self.model().dataChanged.connect(self.update_display_text)
        self._changed = False

    def handle_item_pressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.flags() & Qt.ItemIsUserCheckable:
            if item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
            self._changed = True

    def hidePopup(self):
        if not self._changed:
            super().hidePopup()
        self._changed = False

    def addItem(self, text, userData=None, checked=False):
        super().addItem(text, userData)
        item = self.model().item(self.count() - 1, 0)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        self.update_display_text()

    def clear(self):
        super().clear()
        self.update_display_text()

    def currentData(self):
        res = []
        for i in range(self.count()):
            item = self.model().item(i)
            if item.checkState() == Qt.Checked:
                data = super().itemData(i)
                if data is not None:
                    res.append(data)
        return res

    def update_display_text(self):
        selected_texts = []
        for i in range(self.count()):
            item = self.model().item(i)
            if item.checkState() == Qt.Checked:
                txt = item.text().strip()
                if txt.startswith("↳"):
                    txt = txt[1:].strip()
                selected_texts.append(txt)
                
        if not selected_texts:
            self.lineEdit().setText("")
        elif len(selected_texts) == 1:
            self.lineEdit().setText(selected_texts[0])
        else:
            self.lineEdit().setText(f"Выбрано: {len(selected_texts)}")


class TagSelector(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_tags = []
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        self.pills_layout = QHBoxLayout()
        self.pills_layout.setSpacing(5)
        
        self.select_btn = QPushButton("➕ Выбрать/Создать теги")
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.clicked.connect(self.show_popup)
        
        self.layout.addLayout(self.pills_layout)
        self.layout.addWidget(self.select_btn)
        
        self.refresh_pills()
        
    def refresh_pills(self):
        while self.pills_layout.count():
            child = self.pills_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        for tag in self.selected_tags:
            pill = QFrame()
            pill.setStyleSheet("background-color: #3A3A3A; border-radius: 6px; padding: 2px 6px;")
            pill_lay = QHBoxLayout(pill)
            pill_lay.setContentsMargins(4, 2, 4, 2)
            
            lbl = QLabel(f"#{tag}")
            lbl.setStyleSheet("color: #E0E0E0; border: none; font-weight: normal;")
            
            close_btn = QPushButton("✕")
            close_btn.setFixedSize(16, 16)
            close_btn.setStyleSheet("background: transparent; color: #A0A0A0; border: none; padding: 0px;")
            close_btn.clicked.connect(lambda checked=False, t=tag: self.remove_tag(t))
            
            pill_lay.addWidget(lbl)
            pill_lay.addWidget(close_btn)
            self.pills_layout.addWidget(pill)
            
        self.pills_layout.addStretch()

    def remove_tag(self, tag):
        if tag in self.selected_tags:
            self.selected_tags.remove(tag)
            self.refresh_pills()

    def set_tags(self, tags_str):
        if not tags_str:
            self.selected_tags = []
        else:
            self.selected_tags = [t.strip() for t in tags_str.split(',') if t.strip()]
        self.refresh_pills()

    def get_tags(self):
        return ", ".join(self.selected_tags)

    def show_popup(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2A2A2A; border: 1px solid #3A3A3A; border-radius: 8px; }")
        
        widget_action = QWidgetAction(menu)
        container = QWidget()
        container.setMinimumWidth(250)
        vlay = QVBoxLayout(container)
        
        search_input = QLineEdit()
        search_input.setPlaceholderText("Поиск или новый тег...")
        vlay.addWidget(search_input)
        
        list_widget = QListWidget()
        list_widget.setStyleSheet("QListWidget { background: transparent; border: none; }")
        list_widget.setMaximumHeight(200)
        
        def add_tag_item(t, checked=False):
            item = QListWidgetItem(f"#{t}")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            item.setData(Qt.UserRole, t)
            list_widget.addItem(item)

        all_tags = self.db.get_all_tags()
        for t in all_tags:
            add_tag_item(t, t in self.selected_tags)
            
        vlay.addWidget(list_widget)
        
        create_btn = QPushButton("➕ Создать новый")
        create_btn.setObjectName("PrimaryButton")
        vlay.addWidget(create_btn)
        
        widget_action.setDefaultWidget(container)
        menu.addAction(widget_action)
        
        def filter_list(text):
            text_l = text.lower()
            if text_l.startswith("#"):
                text_l = text_l[1:].strip()
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                item.setHidden(text_l not in item.data(Qt.UserRole).lower())
                
        search_input.textChanged.connect(filter_list)
        
        def on_hide():
            new_tags = []
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    new_tags.append(item.data(Qt.UserRole))
            self.selected_tags = new_tags
            self.refresh_pills()
            
        menu.aboutToHide.connect(on_hide)
        
        def create_new():
            text = search_input.text().strip()
            if text.startswith("#"):
                text = text[1:].strip()
            existing_tags = {
                list_widget.item(i).data(Qt.UserRole).lower()
                for i in range(list_widget.count())
            }
            if text and text.lower() not in existing_tags:
                add_tag_item(text, True)
            menu.close()
                
        create_btn.clicked.connect(create_new)
        
        menu.exec(self.select_btn.mapToGlobal(self.select_btn.rect().bottomLeft()))
