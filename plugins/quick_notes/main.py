"""
快速笔记插件 - 支持树状结构管理的笔记编辑器
功能：
1. 文本编辑器（支持查找、替换）
2. 树状结构笔记管理
3. 本地文件夹同步存储
4. 创建、编辑、删除笔记和文件夹
"""

import os
import json
import re
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QInputDialog,
    QMessageBox,
    QToolBar,
    QFileDialog,
    QGroupBox,
    QFrame,
    QMenu,
    QStyle,
    QApplication,
)
from PySide6.QtCore import Qt, QTimer, QSignalMapper
from PySide6.QtGui import QFont, QAction, QTextCursor, QKeySequence, QIcon

# 导入配置
from app_qt.configs import PLUGIN_DATA_DIR
from app_qt.plugin_manager import PluginManager

allowed_file_extensions = (".md", ".txt", ".py", ".json")


class QuickNotesTab(QWidget):
    """快速笔记标签页"""

    def __init__(self):
        super().__init__()

        # 从配置获取笔记数据目录
        self.notes_dir = os.path.join(PLUGIN_DATA_DIR, "quick_notes")

        # 确保目录存在
        if not os.path.exists(self.notes_dir):
            os.makedirs(self.notes_dir)

        # 当前打开的笔记路径
        self.current_note_path = None
        self.is_modified = False

        # 插件管理器引用
        self.plugin_manager: PluginManager = None

        self.init_ui()
        self.load_note_tree()

    def init_ui(self):
        """初始化界面"""
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # 创建左右分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ==================== 左侧：树状笔记管理 ====================
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_widget.setLayout(left_layout)

        # 树状标题
        tree_label = QLabel("📁 笔记管理")
        tree_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        left_layout.addWidget(tree_label)

        # 树状工具栏
        tree_toolbar = QFrame()
        tree_toolbar_layout = QHBoxLayout()
        tree_toolbar.setLayout(tree_toolbar_layout)
        tree_toolbar.setFrameShape(QFrame.Shape.StyledPanel)
        tree_toolbar.setFrameShadow(QFrame.Shadow.Raised)

        # 新建笔记按钮
        self.new_note_btn = QPushButton("📄 新建笔记")
        self.new_note_btn.clicked.connect(self.create_new_note)
        tree_toolbar_layout.addWidget(self.new_note_btn)

        # 新建文件夹按钮
        self.new_folder_btn = QPushButton("📁 新建文件夹")
        self.new_folder_btn.clicked.connect(self.create_new_folder)
        tree_toolbar_layout.addWidget(self.new_folder_btn)

        # 删除按钮
        self.delete_btn = QPushButton("🗑️ 删除")
        self.delete_btn.clicked.connect(self.delete_selected)
        tree_toolbar_layout.addWidget(self.delete_btn)

        # 刷新按钮
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.load_note_tree)
        tree_toolbar_layout.addWidget(self.refresh_btn)

        tree_toolbar_layout.addStretch()
        left_layout.addWidget(tree_toolbar)

        # 树状控件
        self.note_tree = QTreeWidget()
        self.note_tree.setHeaderLabel("笔记目录")
        self.note_tree.setFont(QFont("Microsoft YaHei UI", 9))
        self.note_tree.itemClicked.connect(self.on_tree_item_clicked)
        self.note_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.note_tree.customContextMenuRequested.connect(self.show_context_menu)
        left_layout.addWidget(self.note_tree)

        splitter.addWidget(left_widget)

        # ==================== 右侧：编辑器区域 ====================
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        # 编辑器标题
        editor_label = QLabel("📝 编辑器")
        editor_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        right_layout.addWidget(editor_label)

        # 编辑器工具栏
        editor_toolbar = QFrame()
        editor_toolbar_layout = QHBoxLayout()
        editor_toolbar.setLayout(editor_toolbar_layout)
        editor_toolbar.setFrameShape(QFrame.Shape.StyledPanel)
        editor_toolbar.setFrameShadow(QFrame.Shadow.Raised)

        # 保存按钮
        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(self.save_current_note)
        editor_toolbar_layout.addWidget(self.save_btn)

        # 查找按钮
        self.find_btn = QPushButton("🔍 查找")
        self.find_btn.clicked.connect(self.show_find_dialog)
        editor_toolbar_layout.addWidget(self.find_btn)

        # 替换按钮
        self.replace_btn = QPushButton("🔄 替换")
        self.replace_btn.clicked.connect(self.show_replace_dialog)
        editor_toolbar_layout.addWidget(self.replace_btn)

        editor_toolbar_layout.addStretch()

        # 当前文件路径显示
        self.current_path_label = QLabel("")
        self.current_path_label.setFont(QFont("Consolas", 8))
        self.current_path_label.setStyleSheet("color: gray;")
        editor_toolbar_layout.addWidget(self.current_path_label)

        right_layout.addWidget(editor_toolbar)

        # 文本编辑器
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 10))
        self.editor.setPlaceholderText("在此输入笔记内容...")
        self.editor.textChanged.connect(self.on_text_changed)
        
        # 设置编辑器接受上下文菜单
        self.editor.setContextMenuPolicy(Qt.CustomContextMenu)
        self.editor.customContextMenuRequested.connect(self.show_editor_context_menu)
        
        # 创建编辑器的快捷键
        self.create_editor_shortcuts()
        
        right_layout.addWidget(self.editor)

        # 查找替换面板（默认隐藏）
        self.find_panel = QFrame()
        self.find_panel.setFrameShape(QFrame.Shape.StyledPanel)
        self.find_panel.setFrameShadow(QFrame.Shadow.Plain)
        find_layout = QVBoxLayout()
        self.find_panel.setLayout(find_layout)
        self.find_panel.setVisible(False)

        # 查找行
        find_row = QHBoxLayout()
        find_label = QLabel("查找:")
        find_row.addWidget(find_label)

        self.find_input = QLineEdit()
        self.find_input.returnPressed.connect(self.find_next)
        find_row.addWidget(self.find_input)

        self.find_next_btn = QPushButton("查找下一个")
        self.find_next_btn.clicked.connect(self.find_next)
        find_row.addWidget(self.find_next_btn)

        self.find_close_btn = QPushButton("关闭")
        self.find_close_btn.clicked.connect(self.hide_find_panel)
        find_row.addWidget(self.find_close_btn)

        find_layout.addLayout(find_row)

        # 替换行
        replace_row = QHBoxLayout()
        replace_label = QLabel("替换:")
        replace_row.addWidget(replace_label)

        self.replace_input = QLineEdit()
        replace_row.addWidget(self.replace_input)

        self.replace_one_btn = QPushButton("替换")
        self.replace_one_btn.clicked.connect(self.replace_one)
        replace_row.addWidget(self.replace_one_btn)

        self.replace_all_btn = QPushButton("全部替换")
        self.replace_all_btn.clicked.connect(self.replace_all)
        replace_row.addWidget(self.replace_all_btn)

        find_layout.addLayout(replace_row)

        right_layout.addWidget(self.find_panel)

        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([250, 600])

        # 查找位置记录
        self.find_start_index = 0

    def load_note_tree(self):
        """加载笔记树状结构"""
        self.note_tree.clear()

        if not os.path.exists(self.notes_dir):
            return

        # 遍历目录构建树
        for root, dirs, files in os.walk(self.notes_dir):
            # 跳过隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            level = root.replace(self.notes_dir, "").count(os.sep)
            indent = "" * level

            for dir_name in sorted(dirs):
                dir_path = os.path.join(root, dir_name)
                if not dir_name.startswith("."):
                    item = QTreeWidgetItem([dir_name])
                    item.setData(0, Qt.ItemDataRole.UserRole, dir_path)
                    item.setIcon(
                        0, self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
                    )  # 文件夹图标

                    if level == 0:
                        self.note_tree.addTopLevelItem(item)
                    else:
                        # 找到父节点并添加
                        parent_path = os.path.dirname(dir_path)
                        parent_items = self.note_tree.findItems(
                            os.path.basename(parent_path), Qt.MatchFlag.MatchContains
                        )
                        if parent_items:
                            parent_items[0].addChild(item)

            for file_name in sorted(files):
                if file_name.endswith(allowed_file_extensions):
                    file_path = os.path.join(root, file_name)
                    item = QTreeWidgetItem([file_name])
                    item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                    item.setIcon(
                        0, self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
                    )  # 文件图标

                    if level == 0:
                        self.note_tree.addTopLevelItem(item)
                    else:
                        # 找到父节点并添加
                        parent_items = self.note_tree.findItems(
                            os.path.basename(root), Qt.MatchFlag.MatchContains
                        )
                        if parent_items:
                            parent_items[0].addChild(item)

        self.note_tree.expandAll()

    def on_tree_item_clicked(self, item, column):
        """树节点点击事件"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)

        if not file_path or not os.path.isfile(file_path):
            return

        # 如果当前笔记有未保存的修改，提示保存
        if self.is_modified and self.current_note_path:
            reply = QMessageBox.question(
                self,
                "保存提示",
                "当前笔记有未保存的修改，是否保存？",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Save:
                self.save_current_note()
            elif reply == QMessageBox.StandardButton.Cancel:
                # 取消切换，重新选中原来的项
                self.load_note_content(self.current_note_path)
                return

        # 加载笔记内容
        self.load_note_content(file_path)

    def load_note_content(self, file_path):
        """加载笔记内容"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.editor.setPlainText(content)
            self.current_note_path = file_path
            self.current_path_label.setText(f"📄 {file_path}")
            self.is_modified = False

            # 跳转后取消选中
            cursor = self.editor.textCursor()
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载笔记：{str(e)}")

    def on_text_changed(self):
        """文本变化事件"""
        self.is_modified = True

    def save_current_note(self):
        """保存当前笔记"""
        if not self.current_note_path:
            # 如果没有路径，另存为
            self.save_as_note()
            return

        try:
            content = self.editor.toPlainText()

            # 确保目录存在
            os.makedirs(os.path.dirname(self.current_note_path), exist_ok=True)

            with open(self.current_note_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.is_modified = False
            self.statusBar_show_message("笔记已保存")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法保存笔记：{str(e)}")

    def save_as_note(self):
        """另存为笔记"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "另存为",
            self.notes_dir,
            "文本文件 (*".join(allowed_file_extensions) + ");;所有文件 (*)",
        )

        if file_path:
            self.current_note_path = file_path
            self.save_current_note()
            self.load_note_tree()

    def create_new_note(self):
        """创建新笔记"""
        # 获取选中的节点作为父节点
        selected_items = self.note_tree.selectedItems()

        if selected_items:
            parent_item = selected_items[0]
            parent_path = parent_item.data(0, Qt.ItemDataRole.UserRole)

            # 如果是文件，取父目录
            if os.path.isfile(parent_path):
                parent_path = os.path.dirname(parent_path)
        else:
            parent_path = self.notes_dir

        # 输入文件名
        name, ok = QInputDialog.getText(self, "新建笔记", "请输入笔记名称:")
        if not ok or not name.strip():
            return

        # 构建完整路径
        if not name.strip().endswith(allowed_file_extensions):
            file_name = f"{name.strip()}.md"
        else:
            file_name = name.strip()
        file_path = os.path.join(parent_path, file_name)

        # 检查是否已存在
        if os.path.exists(file_path):
            QMessageBox.warning(self, "警告", "同名文件已存在!")
            return

        # 创建空文件
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("")

            # 刷新树并打开新笔记
            self.load_note_tree()
            self.load_note_content(file_path)
            self.editor.setFocus()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建笔记：{str(e)}")

    def create_new_folder(self):
        """创建新文件夹"""
        selected_items = self.note_tree.selectedItems()

        if selected_items:
            parent_item = selected_items[0]
            parent_path = parent_item.data(0, Qt.ItemDataRole.UserRole)

            # 如果是文件，取父目录
            if os.path.isfile(parent_path):
                parent_path = os.path.dirname(parent_path)
        else:
            parent_path = self.notes_dir

        # 输入文件夹名
        name, ok = QInputDialog.getText(self, "新建文件夹", "请输入文件夹名称:")
        if not ok or not name.strip():
            return

        folder_name = name.strip()
        folder_path = os.path.join(parent_path, folder_name)

        # 检查是否已存在
        if os.path.exists(folder_path):
            QMessageBox.warning(self, "警告", "同名文件夹已存在!")
            return

        # 创建文件夹
        try:
            os.makedirs(folder_path)
            self.load_note_tree()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建文件夹：{str(e)}")

    def delete_selected(self):
        """删除选中的节点"""
        selected_items = self.note_tree.selectedItems()

        if not selected_items:
            QMessageBox.information(self, "提示", "请先选择要删除的项目")
            return

        item = selected_items[0]
        path = item.data(0, Qt.ItemDataRole.UserRole)

        if not path:
            return

        # 确认删除
        name = os.path.basename(path)
        reply = QMessageBox.warning(
            self,
            "确认删除",
            f'确定要删除 "{name}" 吗？\n此操作不可恢复!',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                import shutil

                shutil.rmtree(path)

            # 如果删除的是当前打开的笔记，清空编辑器
            if path == self.current_note_path:
                self.editor.clear()
                self.current_note_path = None
                self.current_path_label.setText("")
                self.is_modified = False

            self.load_note_tree()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法删除：{str(e)}")

    def show_context_menu(self, pos):
        """显示右键菜单"""
        from PySide6.QtGui import QContextMenuEvent

        menu = QMenu(self)

        rename_action = menu.addAction("重命名")
        rename_action.triggered.connect(self.rename_selected)

        open_location_action = menu.addAction("在文件管理器中打开")
        open_location_action.triggered.connect(self.open_in_explorer)

        menu.exec_(self.note_tree.viewport().mapToGlobal(pos))

    def rename_selected(self):
        """重命名选中的项目"""
        selected_items = self.note_tree.selectedItems()

        if not selected_items:
            return

        item = selected_items[0]
        old_path = item.data(0, Qt.ItemDataRole.UserRole)
        old_name = item.text(0)

        new_name, ok = QInputDialog.getText(
            self, "重命名", "请输入新名称:", text=old_name
        )

        if not ok or not new_name.strip() or new_name == old_name:
            return

        new_path = os.path.join(os.path.dirname(old_path), new_name.strip())

        try:
            os.rename(old_path, new_path)
            self.load_note_tree()

            # 如果重命名的是当前打开的笔记，更新路径
            if old_path == self.current_note_path:
                self.current_note_path = new_path
                self.current_path_label.setText(f"📄 {new_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法重命名：{str(e)}")

    def open_in_explorer(self):
        """在文件管理器中打开"""
        selected_items = self.note_tree.selectedItems()

        if not selected_items:
            return

        path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)

        if os.path.isfile(path):
            path = os.path.dirname(path)

        os.startfile(path)

    # ==================== 查找替换功能 ====================

    def show_find_dialog(self):
        """显示查找面板"""
        self.find_panel.setVisible(True)
        self.find_input.setFocus()
        self.find_start_index = 0

    def show_replace_dialog(self):
        """显示替换面板"""
        self.find_panel.setVisible(True)
        self.find_input.setFocus()
        self.find_start_index = 0

    def hide_find_panel(self):
        """隐藏查找面板"""
        self.find_panel.setVisible(False)
        self.editor.setFocus()

    def find_next(self):
        """查找下一个"""
        search_term = self.find_input.text()

        if not search_term:
            QMessageBox.warning(self, "提示", "请输入查找内容")
            return

        content = self.editor.toPlainText()

        # 从当前位置开始查找
        pos = content.find(search_term, self.find_start_index)

        if pos == -1:
            # 如果没找到，从头开始查找
            pos = content.find(search_term, 0)
            if pos == -1:
                QMessageBox.information(self, "查找完成", f"未找到 '{search_term}'")
                return

        # 计算结束位置
        end_pos = pos + len(search_term)

        # 高亮显示
        cursor = self.editor.textCursor()
        cursor.setPosition(pos)
        cursor.setPosition(end_pos, QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)

        # 滚动到找到的位置
        self.editor.ensureCursorVisible()

        # 更新下次查找起始位置
        self.find_start_index = end_pos

    def replace_one(self):
        """替换一个匹配项"""
        search_term = self.find_input.text()
        replace_term = self.replace_input.text()

        if not search_term:
            QMessageBox.warning(self, "提示", "请输入查找内容")
            return

        # 获取当前选中的文本
        cursor = self.editor.textCursor()
        selected_text = cursor.selectedText()

        if selected_text == search_term:
            # 替换选中的文本
            cursor.insertText(replace_term)
            self.editor.setTextCursor(cursor)
            self.find_start_index = cursor.position()
            self.is_modified = True
        else:
            # 如果没有选中或选中的不匹配，查找下一个
            self.find_next()

    def replace_all(self):
        """全部替换"""
        search_term = self.find_input.text()
        replace_term = self.replace_input.text()

        if not search_term:
            QMessageBox.warning(self, "提示", "请输入查找内容")
            return

        content = self.editor.toPlainText()
        count = content.count(search_term)

        if count == 0:
            QMessageBox.information(self, "替换完成", f"未找到 '{search_term}'")
            return

        # 全部替换
        new_content = content.replace(search_term, replace_term)
        self.editor.setPlainText(new_content)
        self.is_modified = True

        QMessageBox.information(self, "替换完成", f"已替换 {count} 处 '{search_term}'")
        self.find_start_index = 0

    def statusBar_show_message(self, message):
        """显示状态消息（简化版本）"""
        # 可以在未来添加状态栏
        print(f"状态：{message}")

    # ==================== 编辑器上下文菜单和快捷键 ====================

    def show_editor_context_menu(self, pos):
        """显示编辑器右键菜单"""
        menu = QMenu(self.editor)

        # 撤销/重做
        undo_action = menu.addAction("↶ 撤销")
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self.editor.undo)
        undo_action.setEnabled(self.editor.document().isUndoAvailable())

        redo_action = menu.addAction("↷ 重做")
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self.editor.redo)
        redo_action.setEnabled(self.editor.document().isRedoAvailable())

        menu.addSeparator()

        # 剪切/复制/粘贴
        cut_action = menu.addAction("✂ 剪切")
        cut_action.setShortcut(QKeySequence.Cut)
        cut_action.triggered.connect(self.editor.cut)
        cut_action.setEnabled(self.editor.textCursor().hasSelection())

        copy_action = menu.addAction("📋 复制")
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.editor.copy)
        copy_action.setEnabled(self.editor.textCursor().hasSelection())

        paste_action = menu.addAction("📌 粘贴")
        paste_action.setShortcut(QKeySequence.Paste)
        paste_action.triggered.connect(self.editor.paste)
        paste_action.setEnabled(not self.editor.toPlainText().strip() == "" or 
                               QApplication.clipboard().text() != "")

        menu.addSeparator()

        # 全选
        select_all_action = menu.addAction("☑ 全选")
        select_all_action.setShortcut(QKeySequence.SelectAll)
        select_all_action.triggered.connect(self.editor.selectAll)

        menu.addSeparator()

        # 查找/替换
        find_action = menu.addAction("🔍 查找")
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self.show_find_dialog)

        replace_action = menu.addAction("🔄 替换")
        replace_action.setShortcut(QKeySequence.Replace)
        replace_action.triggered.connect(self.show_replace_dialog)

        menu.addSeparator()

        # 保存
        save_action = menu.addAction("💾 保存")
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self.save_current_note)

        # 显示菜单
        menu.exec_(self.editor.viewport().mapToGlobal(pos))

    def create_editor_shortcuts(self):
        """创建编辑器快捷键"""
        # 保存快捷键
        save_shortcut = QAction("保存", self)
        save_shortcut.setShortcut(QKeySequence.Save)  # Ctrl+S
        save_shortcut.triggered.connect(self.save_current_note)
        self.editor.addAction(save_shortcut)

        # 查找快捷键
        find_shortcut = QAction("查找", self)
        find_shortcut.setShortcut(QKeySequence.Find)  # Ctrl+F
        find_shortcut.triggered.connect(self.show_find_dialog)
        self.editor.addAction(find_shortcut)

        # 替换快捷键
        replace_shortcut = QAction("替换", self)
        replace_shortcut.setShortcut(QKeySequence.Replace)  # Ctrl+H
        replace_shortcut.triggered.connect(self.show_replace_dialog)
        self.editor.addAction(replace_shortcut)

        # 撤销快捷键
        undo_shortcut = QAction("撤销", self)
        undo_shortcut.setShortcut(QKeySequence.Undo)  # Ctrl+Z
        undo_shortcut.triggered.connect(self.editor.undo)
        self.editor.addAction(undo_shortcut)

        # 重做快捷键
        redo_shortcut = QAction("重做", self)
        redo_shortcut.setShortcut(QKeySequence.Redo)  # Ctrl+Y 或 Ctrl+Shift+Z
        redo_shortcut.triggered.connect(self.editor.redo)
        self.editor.addAction(redo_shortcut)

    # ==================== API 接口方法（暴露给其他插件调用） ====================

    def create_note_api(self, name, folder=None):
        """
        API: 创建新笔记

        Args:
            name: 笔记名称
            folder: 所属文件夹路径（可选）

        Returns:
            str: 笔记完整路径
        """
        if folder:
            parent_path = os.path.join(self.notes_dir, folder)
        else:
            parent_path = self.notes_dir
        if not name.strip().endswith(allowed_file_extensions):
            file_name = f"{name.strip()}.md"
        file_path = os.path.join(parent_path, file_name)

        # 检查是否已存在
        if os.path.exists(file_path):
            raise FileExistsError(f"同名文件已存在：{file_path}")

        # 创建空文件
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("")

        # 刷新树并打开新笔记
        self.load_note_tree()
        self.load_note_content(file_path)

        return file_path

    def load_note_to_ipython_api(self, variable_name: str, path: str) -> str:
        """
        API: 加载笔记内容到IPython，变量名自拟。在不需要读取笔记全部内容，或需要将该内容加载到ipython使用时，推荐优先使用该方法

        Args:
            variable_name: str, 笔记内容保存的变量名
            path: 笔记文件路径(相对路径)

        Returns:
            str: 笔记文本内容，返回'success'表示成功加载到IPython，返回其他错误日志表示失败
        """
        content = self.load_note_api(path)
        method = self.plugin_manager.get_method("system.set_variable")
        if method:
            ret = method(variable_name, content)
            return "success" if ret else "set variable failed"
        else:
            return f"method not found for system.set_variable"

    def load_note_api(self, path):
        """
        API: 加载笔记内容

        Args:
            path: 笔记文件相对路径，如 "folder/notes.txt"

        Returns:
            str: 笔记文本内容
        """
        path = os.path.join(self.notes_dir, path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"笔记不存在：{path}")

        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        return content

    def save_note_api(self, path, content):
        """
        API: 保存笔记

        Args:
            path: 笔记文件路径
            content: 笔记内容

        Returns:
            bool: 保存是否成功
        """
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"保存笔记失败：{e}")
            return False

    def _is_path_allowed(self, relpath):
        return relpath.lstrip("/\\").startswith(("scripts",))

    def save_textfile_safe_api(self, path, content):
        """
        API: 保存文本文件,仅允许操作allow list路径下面的文件. 目前allow_list=["scripts"],比如"scripts/demo.py"是允许创建的, "abc/demo.py"就是不允许创建的

        Args:
            path: str, 文件相对路径
            content: str, 文件内容

        Returns:
            str: 保存是否成功,状态信息
        """
        if not self._is_path_allowed(path):
            return f"path not allowed: {path}"
        return (
            "success"
            if self.save_note_api(os.path.join(self.notes_dir, path), content)
            else "save failed"
        )

    def query_note_by_name_api(self, name_query: str):
        """
        API: 查询笔记名称

        Args:
            name_query: str 笔记名称查询字符串，模糊匹配

        Returns:
            str: 笔记相对路径，如果找到多个匹配项，则返回第一个匹配项的路径。若无匹配则为空字符串
        """
        for root, dirs, files in os.walk(self.notes_dir):
            for file in files:
                if file.find(name_query) != -1:
                    return os.path.relpath(os.path.join(root, file), self.notes_dir)
        return ""

    def query_notes_by_text_api(
        self,
        text_query: str,
        limit: int = 10,
        chunk_size: int = 1000,
        regex: bool = False,
        folder: str = "",
    ) -> list[tuple[str, str]]:
        """
        API: 全局查询笔记内容，支持正则表达式、限制条数和字符数，默认情况下不需要调整。

        Args:
            text_query: str 笔记内容查询字符串，模糊匹配
            limit: int = 10: 返回的结果条数限制
            chunk_size: int = 1000: 每个笔记块的字符数限制
            regex: bool = False: 是否使用正则表达式匹配,正则匹配时将直接用正则匹配,否则文本将被以空格切分后按照or的逻辑匹配返回.
            folder: str = "": 查询的文件夹相对路径,如"scripts/",默认为空,则从根目录开始查询

        Returns:
            list[tuple[str, str]]: 笔记的相对路径和内容的列表
        """
        ret = []
        count = 0

        if folder != "":
            folder_path = os.path.join(self.notes_dir, folder)
            if not os.path.exists(folder_path):
                raise FileNotFoundError(f"查询文件夹不存在：{folder_path}")
        else:
            folder_path = self.notes_dir
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                # 如果已经达到限制，提前退出
                if count >= limit:
                    break

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    position = -1
                    # 检查内容是否包含查询文本（模糊匹配）
                    if regex:
                        searched = re.search(text_query, content)
                        if searched:
                            position = searched.start()
                    else:
                        text_query_words = text_query.split()
                        position = any(content.find(word) != -1 for word in text_query_words)
                    if position != -1:
                        chunk_start = max(0, position - chunk_size // 2)
                        chunk_end = min(len(content), position + chunk_size // 2)
                        # 获取相对路径
                        rel_path = os.path.relpath(file_path, self.notes_dir)
                        ret.append((rel_path, content[chunk_start:chunk_end]))
                        count += 1

                except Exception as e:
                    # 跳过读取失败的文件
                    print(f"[Quick Notes] 读取文件失败 {file_path}: {e}")
                    continue

            # 外层循环也需要检查是否已经达到限制
            if count >= limit:
                break

        return ret


# ==================== 插件入口函数 ====================


def load_plugin(plugin_manager: "PluginManager"):
    """
    插件加载入口函数

    Args:
        plugin_manager: 插件管理器实例

    Returns:
        dict: 包含插件组件的字典
    """
    print("[QuickNotes] 正在加载快速笔记插件...")

    # 创建标签页实例
    notes_tab = QuickNotesTab()
    notes_tab.plugin_manager = plugin_manager

    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "quick_notes", "create_note", notes_tab.create_note_api
    )
    plugin_manager.register_method("quick_notes", "load_note", notes_tab.load_note_api)
    plugin_manager.register_method(
        "quick_notes", "load_note_to_ipython", notes_tab.load_note_to_ipython_api
    )
    plugin_manager.register_method("quick_notes", "save_note", notes_tab.save_note_api)
    plugin_manager.register_method(
        "quick_notes", "query_note_by_name", notes_tab.query_note_by_name_api
    )
    plugin_manager.register_method(
        "quick_notes", "query_notes_by_text", notes_tab.query_notes_by_text_api
    )
    plugin_manager.register_method(
        "quick_notes", "save_textfile_safe", notes_tab.save_textfile_safe_api
    )

    # 添加到标签页（由插件管理器统一管理）
    plugin_manager.add_plugin_tab("quick_notes", "📝 快速笔记", notes_tab, position=2)

    print("[QuickNotes] 快速笔记插件加载完成")
    return {"tab": notes_tab, "namespace": "quick_notes"}


def unload_plugin(plugin_manager):
    """
    插件卸载回调

    Args:
        plugin_manager: 插件管理器实例
    """
    print("[QuickNotes] 正在卸载快速笔记插件...")
    # 清理资源、保存状态等
    print("[QuickNotes] 快速笔记插件卸载完成")
