from PySide6.QtWidgets import (QComboBox, QLineEdit, QWidget, QHBoxLayout,
                             QVBoxLayout, QLabel, QPushButton, QFrame, QMenu,
                             QWidgetAction, QListWidget, QListWidgetItem,
                             QTreeView, QAbstractItemView, QInputDialog,
                             QMessageBox)
from PySide6.QtCore import Qt, Signal, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem


class CheckableComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.empty_text = "Все..."
        self.no_items_text = "Нет данных"
        self.setLineEdit(QLineEdit())
        self.lineEdit().setReadOnly(True)
        self.lineEdit().setText(self.empty_text)
        self.lineEdit().setStyleSheet("QLineEdit { border: none; background: transparent; padding-left: 5px; color: #FFFFFF; }")
        self.setMinimumHeight(38)
        self.view().pressed.connect(self.handle_item_pressed)
        self.setModel(QStandardItemModel(self))
        self.model().dataChanged.connect(self.update_display_text)
        self._changed = False

    def setDisplayTexts(self, empty_text: str, no_items_text: str):
        self.empty_text = empty_text
        self.no_items_text = no_items_text
        self.update_display_text()

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
        self.setEnabled(True)
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

        if self.count() == 0:
            self.lineEdit().setText(self.no_items_text)
            self.setEnabled(False)
        elif not selected_texts:
            self.lineEdit().setText(self.empty_text)
            self.setEnabled(True)
        elif len(selected_texts) == 1:
            self.lineEdit().setText(selected_texts[0])
            self.setEnabled(True)
        else:
            self.lineEdit().setText(f"Выбрано: {len(selected_texts)}")
            self.setEnabled(True)


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
                self.db.add_tag(text)
                add_tag_item(text, True)
            menu.close()

        create_btn.clicked.connect(create_new)

        menu.exec(self.select_btn.mapToGlobal(self.select_btn.rect().bottomLeft()))


class TagFilterWidget(QPushButton):
    dataChanged = Signal()

    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self._checked_tags = set()
        self._all_tags = []
        self.setObjectName("SecondaryButton")
        self.setStyleSheet("text-align: left; padding: 8px 12px; background-color: #222222; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF;")
        self.setText("Все теги")
        self.clicked.connect(self.show_popup)
        self.refresh_tags()

    def refresh_tags(self):
        self._all_tags = self.db.get_all_tags()
        self._checked_tags = {tag for tag in self._checked_tags if tag in self._all_tags}
        self._update_text()

    def clear(self):
        self._checked_tags.clear()
        self.refresh_tags()

    def currentData(self):
        return sorted(self._checked_tags)

    def _update_text(self):
        if not self._all_tags:
            self.setText("Теги не созданы")
        elif not self._checked_tags:
            self.setText("Все теги")
        elif len(self._checked_tags) == 1:
            self.setText(f"#{next(iter(self._checked_tags))}")
        else:
            self.setText(f"Выбрано: {len(self._checked_tags)}")

    def _create_tag(self, list_widget=None):
        text, ok = QInputDialog.getText(self, "Создать тег", "Название тега:")
        if not ok:
            return
        tag = text.strip().lstrip("#").strip()
        if not tag:
            return
        if "," in tag:
            QMessageBox.warning(self, "Тег", "Название тега не должно содержать запятую.")
            return

        self.db.add_tag(tag)
        self.refresh_tags()
        if list_widget is not None and tag not in {
            list_widget.item(i).data(Qt.UserRole) for i in range(list_widget.count())
        }:
            self._add_list_item(list_widget, tag, False)
        self.dataChanged.emit()

    def _add_list_item(self, list_widget, tag, checked):
        item = QListWidgetItem(f"#{tag}")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        item.setData(Qt.UserRole, tag)
        list_widget.addItem(item)

    def show_popup(self):
        self.refresh_tags()

        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2A2A2A; border: 1px solid #3A3A3A; border-radius: 8px; }")

        widget_action = QWidgetAction(menu)
        container = QWidget()
        container.setMinimumWidth(max(300, self.width()))
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        list_widget = QListWidget()
        list_widget.setStyleSheet("QListWidget { background: transparent; border: none; }")
        list_widget.setMinimumHeight(140)
        list_widget.setMaximumHeight(260)

        if self._all_tags:
            for tag in self._all_tags:
                self._add_list_item(list_widget, tag, tag in self._checked_tags)
            layout.addWidget(list_widget)
        else:
            empty_label = QLabel("Тегов пока нет. Создайте тег, чтобы потом выбирать его в операциях.")
            empty_label.setWordWrap(True)
            empty_label.setStyleSheet("color: #A0A0A0; padding: 8px;")
            layout.addWidget(empty_label)

        create_btn = QPushButton("➕ Создать тег")
        create_btn.setObjectName("PrimaryButton")
        layout.addWidget(create_btn)

        widget_action.setDefaultWidget(container)
        menu.addAction(widget_action)

        def on_hide():
            if not self._all_tags:
                return
            new_tags = set()
            for i in range(list_widget.count()):
                item = list_widget.item(i)
                if item.checkState() == Qt.Checked:
                    new_tags.add(item.data(Qt.UserRole))
            if new_tags != self._checked_tags:
                self._checked_tags = new_tags
                self._update_text()
                self.dataChanged.emit()

        def on_create():
            self._create_tag(list_widget)
            menu.close()

        menu.aboutToHide.connect(on_hide)
        create_btn.clicked.connect(on_create)
        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

class CategorySelectorWidget(QPushButton):
    currentTextChanged = Signal(str)
    currentIndexChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SecondaryButton")
        self.setStyleSheet("text-align: left; padding: 8px 12px; background-color: #222222; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF;")
        self.setText("Выберите категорию...")

        self.categories_data = []
        self._current_data = None
        self.clicked.connect(self.show_popup)

    def clear(self):
        self.categories_data = []
        self._current_data = None
        self.setText("Выберите категорию...")

    def addItem(self, text, userData=None, parent_id=None, icon=""):
        self.categories_data.append({
            'text': text,
            'id': userData,
            'parent_id': parent_id,
            'icon': icon
        })

    def currentData(self):
        return self._current_data

    def findData(self, data):
        for i, cat in enumerate(self.categories_data):
            if cat['id'] == data:
                return i
        return -1

    def setCurrentIndex(self, index):
        if 0 <= index < len(self.categories_data):
            self._current_data = self.categories_data[index]['id']
            item_text = self.categories_data[index]['text']
            icon = self.categories_data[index].get('icon', '')
            display_text = f"{icon} {item_text}".strip()
            self.setText(display_text)
            self.currentIndexChanged.emit(index)
            self.currentTextChanged.emit(self.text())

    def setCurrentText(self, text):
        pass # Optional implementation if needed

    def show_popup(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2A2A2A; border: 1px solid #3A3A3A; border-radius: 8px; }")

        widget_action = QWidgetAction(menu)
        container = QWidget()
        container.setMinimumWidth(max(400, self.width()))
        vlay = QVBoxLayout(container)
        vlay.setContentsMargins(8, 8, 8, 8)

        search_input = QLineEdit()
        search_input.setPlaceholderText("Поиск категории...")
        search_input.setStyleSheet("background-color: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 6px; padding: 6px;")
        vlay.addWidget(search_input)

        tree_widget = QTreeView()
        tree_widget.setHeaderHidden(True)
        tree_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tree_widget.setStyleSheet("QTreeView { background: transparent; border: none; outline: none; } QTreeView::item { padding: 6px; } QTreeView::item:hover { background-color: #3A3A3A; border-radius: 4px; } QTreeView::item:selected { background-color: #8A2BE2; border-radius: 4px; }")
        tree_widget.setIndentation(20)
        tree_widget.setMinimumHeight(350)
        tree_widget.setExpandsOnDoubleClick(True)

        model = QStandardItemModel()

        # Build tree
        parents = {}
        # First pass: parents
        for cat in self.categories_data:
            if cat['parent_id'] is None:
                display_text = f"{cat.get('icon', '')} {cat['text']}".strip()
                item = QStandardItem(display_text)
                item.setData(cat['id'], Qt.UserRole)
                parents[cat['id']] = item
                model.appendRow(item)

        # Second pass: children
        for cat in self.categories_data:
            if cat['parent_id'] is not None:
                display_text = f"{cat.get('icon', '')} {cat['text'].replace('↳', '').strip()}".strip()
                item = QStandardItem(display_text)
                item.setData(cat['id'], Qt.UserRole)
                parent_item = parents.get(cat['parent_id'])
                if parent_item:
                    parent_item.appendRow(item)
                else:
                    model.appendRow(item)

        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setRecursiveFilteringEnabled(True)

        tree_widget.setModel(proxy)
        tree_widget.collapseAll() # Start collapsed to save space
        vlay.addWidget(tree_widget)

        widget_action.setDefaultWidget(container)
        menu.addAction(widget_action)

        search_input.textChanged.connect(proxy.setFilterFixedString)

        # Expand all if search is active, otherwise collapse
        def on_search(text):
            if text:
                tree_widget.expandAll()
            else:
                tree_widget.collapseAll()
        search_input.textChanged.connect(on_search)

        def on_clicked(index):
            source_index = proxy.mapToSource(index)
            item = model.itemFromIndex(source_index)
            self._current_data = item.data(Qt.UserRole)
            self.setText(item.text())
            menu.close()
            for i, cat in enumerate(self.categories_data):
                if cat['id'] == self._current_data:
                    self.currentIndexChanged.emit(i)
                    self.currentTextChanged.emit(self.text())
                    break

        tree_widget.clicked.connect(on_clicked)

        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))

class CategoryFilterWidget(QPushButton):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SecondaryButton")
        self.setStyleSheet("text-align: left; padding: 8px 12px; background-color: #222222; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF;")
        self.setText("Все категории")

        self.categories_data = []
        self._checked_ids = set()
        self.clicked.connect(self.show_popup)

    def clear(self):
        self.categories_data = []
        self._checked_ids.clear()
        self.setText("Все категории")

    def addItem(self, text, userData=None, parent_id=None, icon=""):
        self.categories_data.append({
            'text': text,
            'id': userData,
            'parent_id': parent_id,
            'icon': icon
        })

    def currentData(self):
        return list(self._checked_ids)

    def currentSubcategoryData(self):
        return [
            cat['id'] for cat in self.categories_data
            if cat['parent_id'] is not None and cat['id'] in self._checked_ids
        ]

    def _children_for(self, parent_id):
        return [cat['id'] for cat in self.categories_data if cat['parent_id'] == parent_id]

    def _parent_for(self, cat_id):
        for cat in self.categories_data:
            if cat['id'] == cat_id:
                return cat['parent_id']
        return None

    def _update_text(self):
        if not self._checked_ids:
            self.setText("Все категории")
            return

        selected_texts = []
        for cat in self.categories_data:
            if cat['id'] in self._checked_ids:
                selected_texts.append(cat['text'])

        if len(selected_texts) == 1:
            self.setText(selected_texts[0])
        else:
            self.setText(f"Выбрано: {len(selected_texts)}")

    def show_popup(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { background-color: #2A2A2A; border: 1px solid #3A3A3A; border-radius: 8px; }")

        widget_action = QWidgetAction(menu)
        container = QWidget()
        container.setMinimumWidth(max(400, self.width()))
        vlay = QVBoxLayout(container)
        vlay.setContentsMargins(8, 8, 8, 8)

        search_input = QLineEdit()
        search_input.setPlaceholderText("Поиск категории...")
        search_input.setStyleSheet("background-color: #1E1E1E; border: 1px solid #3A3A3A; border-radius: 6px; padding: 6px;")
        vlay.addWidget(search_input)

        tree_widget = QTreeView()
        tree_widget.setHeaderHidden(True)
        tree_widget.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tree_widget.setStyleSheet("QTreeView { background: transparent; border: none; outline: none; } QTreeView::item { padding: 6px; } QTreeView::item:hover { background-color: #3A3A3A; border-radius: 4px; }")
        tree_widget.setIndentation(20)
        tree_widget.setMinimumHeight(350)
        tree_widget.setExpandsOnDoubleClick(True)

        model = QStandardItemModel()
        item_by_id = {}

        parents = {}
        for cat in self.categories_data:
            if cat['parent_id'] is None:
                display_text = f"{cat.get('icon', '')} {cat['text']}".strip()
                item = QStandardItem(display_text)
                item.setData(cat['id'], Qt.UserRole)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if cat['id'] in self._checked_ids else Qt.Unchecked)
                parents[cat['id']] = item
                item_by_id[cat['id']] = item
                model.appendRow(item)

        for cat in self.categories_data:
            if cat['parent_id'] is not None:
                display_text = f"{cat.get('icon', '')} {cat['text'].replace('↳', '').strip()}".strip()
                item = QStandardItem(display_text)
                item.setData(cat['id'], Qt.UserRole)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if cat['id'] in self._checked_ids else Qt.Unchecked)
                item_by_id[cat['id']] = item
                parent_item = parents.get(cat['parent_id'])
                if parent_item:
                    parent_item.appendRow(item)
                else:
                    model.appendRow(item)

        proxy = QSortFilterProxyModel()
        proxy.setSourceModel(model)
        proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        proxy.setRecursiveFilteringEnabled(True)

        tree_widget.setModel(proxy)
        tree_widget.collapseAll()
        vlay.addWidget(tree_widget)

        widget_action.setDefaultWidget(container)
        menu.addAction(widget_action)

        search_input.textChanged.connect(proxy.setFilterFixedString)

        def on_search(text):
            if text:
                tree_widget.expandAll()
            else:
                tree_widget.collapseAll()
        search_input.textChanged.connect(on_search)

        syncing = {"active": False}
        last_model_toggle = {"cat_id": None}

        def set_item_checked(cat_id, checked):
            item = item_by_id.get(cat_id)
            if item:
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

        def apply_checked_ids_to_model():
            syncing["active"] = True
            try:
                for cat_id in item_by_id:
                    set_item_checked(cat_id, cat_id in self._checked_ids)
            finally:
                syncing["active"] = False

        def apply_toggle(cat_id, checked):
            parent_id = self._parent_for(cat_id)
            if checked:
                self._checked_ids.add(cat_id)
                if parent_id is not None:
                    self._checked_ids.add(parent_id)
            else:
                self._checked_ids.discard(cat_id)
                if parent_id is None:
                    for child_id in self._children_for(cat_id):
                        self._checked_ids.discard(child_id)

            apply_checked_ids_to_model()
            self._update_text()
            self.dataChanged.emit()

        def on_item_changed(item):
            if syncing["active"]:
                return
            cat_id = item.data(Qt.UserRole)
            if cat_id is None:
                return
            last_model_toggle["cat_id"] = cat_id
            apply_toggle(cat_id, item.checkState() == Qt.Checked)

        def on_clicked(index):
            source_index = proxy.mapToSource(index)
            item = model.itemFromIndex(source_index)
            cat_id = item.data(Qt.UserRole)

            if last_model_toggle["cat_id"] == cat_id:
                last_model_toggle["cat_id"] = None
                return

            new_state = Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked
            apply_toggle(cat_id, new_state == Qt.Checked)

        model.itemChanged.connect(on_item_changed)
        tree_widget.clicked.connect(on_clicked)

        menu.exec(self.mapToGlobal(self.rect().bottomLeft()))
