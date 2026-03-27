"""
快速笔记插件 - 支持树状结构管理的笔记编辑器
重构版本 - 组件化架构
功能：
1. 文本编辑器（支持查找、替换）
2. 树状结构笔记管理
3. 本地文件夹同步存储
4. 创建、编辑、删除笔记和文件夹
5. 支持创建 agentskills-core 兼容的技能
"""

import os
import json
import re
import logging
from typing import Any
from pathlib import Path

logger = logging.getLogger(__name__)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QLabel,
    QMessageBox,
    QToolBar,
    QFileDialog,
    QGroupBox,
    QApplication,
    QFrame,
    QInputDialog,
    QMenu,
    QDialog,
    QMenuBar,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QAction, QKeySequence, QTextCursor

# 导入配置
from app_qt.configs import PLUGIN_DATA_DIR
from app_qt.plugin_manager import PluginManager

# 导入组件
from .components.note_tree_widget import NoteTreeWidget
from .components.editor_widget import EditorToolbar, FindReplacePanel, TextEditorWidget
from .components.skill_creator import CreateSkillDialog

# Initialize plugin i18n
from app_qt.plugin_i18n import PluginI18n
_i18n = PluginI18n("quick_notes", Path(__file__).parent)
_ = _i18n.gettext

allowed_file_extensions = (".md", ".txt", ".py", ".json", ".csv")


class QuickNotesTab(QWidget):
    """快速笔记标签页"""

    def __init__(self):
        super().__init__()

        # 从配置获取笔记数据目录
        self.notes_dir = os.path.join(PLUGIN_DATA_DIR, "quick_notes")

        # 确保目录存在
        if not os.path.exists(self.notes_dir):
            os.makedirs(self.notes_dir)

        # skills 目录 - 用于创建 agentskills-core 兼容的技能
        self.skills_dir = os.path.join(self.notes_dir, "skills")
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir)

        # 当前打开的笔记路径
        self.current_note_path = None
        self.is_modified = False
        
        # 插件管理器引用
        self.plugin_manager: PluginManager = None
        
        self.init_ui()
        # 树在 init_ui 中已经加载，不需要再调用 load_note_tree()

    def init_ui(self):
        """初始化界面"""
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # 创建左右分割器
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ==================== 左侧：树状笔记管理组件 ====================
        self.note_tree = NoteTreeWidget(self.notes_dir, allowed_file_extensions)
        self.note_tree.setMinimumWidth(250)
        
        # 连接信号
        self.note_tree.note_clicked.connect(self.load_note_content)
        # refresh_requested 现在只用于通知，不触发树刷新
        self.note_tree.refresh_requested.connect(self.on_tree_operation_completed)
        # 创建技能请求信号
        self.note_tree.create_skill_requested.connect(self.create_skill_at_path)
        
        # 创建左侧布局（只包含树）
        left_container = QWidget()
        left_layout = QVBoxLayout()
        left_container.setLayout(left_layout)
        left_layout.addWidget(self.create_left_toolbar())
        left_layout.addWidget(self.note_tree)
        
        
        splitter.addWidget(left_container)

        # ==================== 右侧：编辑器区域 ====================
        right_widget = self.create_editor_area()
        splitter.addWidget(right_widget)

        # 设置分割器比例
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([250, 600])

        # 查找位置记录
        self.find_start_index = 0
        
        # 创建菜单栏
        self.create_menu_bar()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        # 获取主窗口的菜单栏
        main_window = self.window()
        if not main_window or not hasattr(main_window, 'menu_bar'):
            return
        
        menu_bar = main_window.menu_bar
        
        # 笔记操作菜单
        notes_menu = menu_bar.addMenu("📝 " + _("Notes"))
        
        # 新建笔记
        self.new_note_action = QAction("📄 " + _("New Note"), self)
        self.new_note_action.setShortcut(QKeySequence.New)
        self.new_note_action.triggered.connect(self.create_new_note)
        notes_menu.addAction(self.new_note_action)
        
        # 新建文件夹
        self.new_folder_action = QAction("📁 " + _("New Folder"), self)
        self.new_folder_action.triggered.connect(self.create_new_folder)
        notes_menu.addAction(self.new_folder_action)
        
        notes_menu.addSeparator()
        
        # 刷新
        self.refresh_action = QAction("🔄 " + _("Refresh"), self)
        self.refresh_action.setShortcut(QKeySequence.Refresh)
        self.refresh_action.triggered.connect(self.load_note_tree)
        notes_menu.addAction(self.refresh_action)
    
    def create_left_toolbar(self):
        """创建左侧工具栏"""
        tree_toolbar = QFrame()
        tree_toolbar_layout = QHBoxLayout()
        tree_toolbar.setLayout(tree_toolbar_layout)
        tree_toolbar.setFrameShape(QFrame.Shape.StyledPanel)
        tree_toolbar.setFrameShadow(QFrame.Shadow.Raised)
        
        # 树状标题
        tree_label = QLabel("📁 " + _("Note Manager"))
        tree_label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Bold))
        
        # 新建笔记按钮
        self.new_note_btn = QPushButton("📄")
        self.new_note_btn.setToolTip(_("New Note"))
        self.new_note_btn.clicked.connect(self.create_new_note)
        tree_toolbar_layout.addWidget(self.new_note_btn)

        # 新建文件夹按钮
        self.new_folder_btn = QPushButton("📁")
        self.new_folder_btn.setToolTip(_("New Folder"))
        self.new_folder_btn.clicked.connect(self.create_new_folder)
        tree_toolbar_layout.addWidget(self.new_folder_btn)

        # 删除按钮
        self.delete_btn = QPushButton("🗑️")
        self.delete_btn.setToolTip(_("Delete"))
        self.delete_btn.clicked.connect(self.delete_selected)
        tree_toolbar_layout.addWidget(self.delete_btn)

        # 刷新按钮
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip(_("Refresh"))
        self.refresh_btn.clicked.connect(self.load_note_tree)
        tree_toolbar_layout.addWidget(self.refresh_btn)
        
        # 创建技能按钮（新增功能）
        self.create_skill_btn = QPushButton("✨")
        self.create_skill_btn.setToolTip(_("Create Skill"))
        self.create_skill_btn.clicked.connect(self.create_new_skill)
        tree_toolbar_layout.addWidget(self.create_skill_btn)

        tree_toolbar_layout.addStretch()
        
        return tree_toolbar
    
    def create_editor_area(self):
        """创建编辑器区域"""
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        right_widget.setLayout(right_layout)

        # 编辑器工具栏组件
        self.editor_toolbar = EditorToolbar()
        self.editor_toolbar.save_requested.connect(self.save_current_note)
        self.editor_toolbar.find_requested.connect(self.show_find_dialog)
        self.editor_toolbar.replace_requested.connect(self.show_replace_dialog)
        right_layout.addWidget(self.editor_toolbar)

        # 文本编辑器组件
        self.editor = TextEditorWidget()
        self.editor.text_changed.connect(self.on_text_changed)
        self.editor.save_requested.connect(self.save_current_note)
        right_layout.addWidget(self.editor)
        
        # 创建编辑器快捷键
        self.create_editor_shortcuts()

        # 查找替换面板组件
        self.find_panel = FindReplacePanel()
        self.find_panel.find_next_requested.connect(self.find_next_with_term)
        self.find_panel.replace_one_requested.connect(self.replace_one_with_terms)
        self.find_panel.replace_all_requested.connect(self.replace_all_with_terms)
        self.find_panel.close_requested.connect(self.hide_find_panel)
        right_layout.addWidget(self.find_panel)
        
        return right_widget

    def load_note_tree(self):
        """手动刷新笔记树（仅刷新按钮调用）"""
        # 检查是否有未保存的修改
        if self.is_modified and self.current_note_path:
            reply = QMessageBox.question(
                self,
                _("Save Prompt"),
                _("Current note has unsaved changes, save?"),
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )

            if reply == QMessageBox.StandardButton.Save:
                self.save_current_note()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        self.note_tree.load_tree()
    
    def on_tree_operation_completed(self):
        """树操作完成后的处理（新建/删除/重命名等）"""
        # 文件系统监听会自动更新树节点
        # 此方法用于其他后续处理（如保持当前笔记打开状态）
        if self.current_note_path and os.path.exists(self.current_note_path):
            # 如果当前笔记仍然存在，确保编辑器状态正确
            pass  # 可以在这里添加额外的处理逻辑

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
            
            # 设置文本并调整语法高亮
            self.editor.set_syntax_by_filepath(file_path)
            self.editor.setPlainText(content)
            self.current_note_path = file_path
            
            # 更新工具栏路径显示和保存状态
            self.editor_toolbar.update_current_path(file_path, self.notes_dir)
            self.is_modified = False
            self.editor_toolbar.set_save_status(False)

            # 跳转后取消选中
            cursor = self.editor.textCursor()
            cursor.clearSelection()
            self.editor.setTextCursor(cursor)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法加载笔记：{str(e)}")

    def on_text_changed(self):
        """文本变化事件"""
        if not self.is_modified:
            self.is_modified = True
            self.editor_toolbar.set_save_status(True)

    def save_current_note(self):
        """保存当前笔记"""
        # 如果没有修改，直接返回
        if not self.is_modified:
            self.statusBar_show_message(_("Note already saved, no need to save again"))
            return

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
            self.editor_toolbar.set_save_status(False)
            self.statusBar_show_message(_("Note saved"))

        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to save note: {}") + str(e))

    def save_as_note(self):
        """另存为笔记"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            _("Save As"),
            self.notes_dir,
            _("Text Files (*") + "*.md, *.txt, *.py, *.json, *.csv);;" + _("All Files (*)")
        )

        if file_path:
            self.current_note_path = file_path
            self.save_current_note()
            # 文件系统监听会自动添加节点到树

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
        name, ok = QInputDialog.getText(self, _("New Note"), _("Enter note name:") + ":")
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
            QMessageBox.warning(self, _("Warning"), _("File with same name already exists!"))
            return

        # 创建空文件
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("")

            # 文件系统监听会自动添加节点到树
            # 直接打开新笔记
            self.load_note_content(file_path)
            self.editor.setFocus()

        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to create note: {}") + str(e))

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
        name, ok = QInputDialog.getText(self, _("New Folder"), _("Enter folder name:") + ":")
        if not ok or not name.strip():
            return

        folder_name = name.strip()
        folder_path = os.path.join(parent_path, folder_name)

        # 检查是否已存在
        if os.path.exists(folder_path):
            QMessageBox.warning(self, _("Warning"), _("Folder with same name already exists!"))
            return

        # 创建文件夹
        try:
            os.makedirs(folder_path)
            # 文件系统监听会自动添加节点到树

        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to create folder: {}") + str(e))

    def delete_selected(self):
        """删除选中的节点"""
        selected_items = self.note_tree.selectedItems()

        if not selected_items:
            QMessageBox.information(self, _("Info"), _("Please select an item to delete"))
            return

        item = selected_items[0]
        path = item.data(0, Qt.ItemDataRole.UserRole)

        if not path:
            return

        # 确认删除
        name = os.path.basename(path)
        reply = QMessageBox.warning(
            self,
            _("Confirm Delete"),
            _('Are you sure to delete "{}"?\nThis action cannot be undone!').format(name),
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
                # 更新工具栏路径显示和保存状态
                self.editor_toolbar.update_current_path(None, self.notes_dir)
                self.is_modified = False
                self.editor_toolbar.set_save_status(False)

            # 文件系统监听会自动移除节点

        except Exception as e:
            QMessageBox.critical(self, _("Error"), _("Failed to delete: {}") + str(e))

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
            # 文件系统监听会自动更新节点

            # 如果重命名的是当前打开的笔记，更新路径
            if old_path == self.current_note_path:
                self.current_note_path = new_path
                # 更新工具栏路径显示
                self.editor_toolbar.update_current_path(new_path, self.notes_dir)

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
        self.find_panel.find_input.setFocus()
        self.find_start_index = 0

    def show_replace_dialog(self):
        """显示替换面板"""
        self.find_panel.setVisible(True)
        self.find_panel.find_input.setFocus()
        self.find_start_index = 0

    def hide_find_panel(self):
        """隐藏查找面板"""
        self.find_panel.setVisible(False)
        self.editor.setFocus()
    
    def find_next_with_term(self, search_term):
        """使用指定的搜索词查找下一个"""
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
                QMessageBox.information(self, _("Find Complete"), _("'{}' not found").format(search_term))
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
    
    def replace_one_with_terms(self, search_term, replace_term):
        """使用指定的词替换一个匹配项"""
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
            self.find_next_with_term(search_term)
    
    def replace_all_with_terms(self, search_term, replace_term):
        """全部替换"""
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
    
    def create_new_skill(self):
        """创建新技能 - agentskills-core 兼容（工具栏按钮调用）"""
        # 获取当前选中的目录作为父路径
        selected_items = self.note_tree.selectedItems()
        parent_path = None
        
        if selected_items:
            selected_path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            # 如果是文件，取父目录
            if os.path.isfile(selected_path):
                parent_path = os.path.dirname(selected_path)
            else:
                parent_path = selected_path
        
        self._do_create_skill(parent_path)
    
    def create_skill_at_path(self, parent_path: str):
        """在指定路径创建技能（树组件信号调用）"""
        self._do_create_skill(parent_path)
    
    def _do_create_skill(self, parent_path: str = None):
        """实际执行创建技能"""
        # 确定技能目录
        if parent_path and os.path.isdir(parent_path):
            # 检查是否是 skills 目录或其子目录
            if parent_path == self.skills_dir or parent_path.startswith(self.skills_dir + os.sep):
                target_skills_dir = parent_path
            else:
                # 如果在其他目录，创建到 skills 根目录
                target_skills_dir = self.skills_dir
        else:
            target_skills_dir = self.skills_dir
        
        try:
            # 显示创建技能对话框
            dialog = CreateSkillDialog(self, skills_dir=target_skills_dir)
            
            if dialog.exec() == int(QDialog.DialogCode.Accepted):
                # 技能创建成功，文件系统监听会自动添加节点
                QMessageBox.information(
                    self, 
                    "成功", 
                    f"技能已创建！\n位置：{target_skills_dir}\n\n提示：技能文件夹可以在文件树中查看和管理。"
                )
        
        except Exception as e:
            logger.error(f"创建技能失败：{e}", exc_info=True)
            QMessageBox.critical(self, _("Error"), _("Failed to create skill: {}") + str(e))

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

        # 文件系统监听会自动添加节点到树
        self.load_note_content(file_path)

        return file_path

    def load_note_to_ipython_api(self, variable_name: str, path: str) -> str:
        """
        API: 加载笔记内容到IPython为一个字符串，变量名自拟。在不需要读取笔记全部内容，或需要将该内容加载到ipython使用时，推荐优先使用该方法

        Args:
            variable_name: str, 笔记内容保存的变量名
            path: 笔记文件路径(相对路径)

        Returns:
            str: 笔记文本内容，返回'success'表示成功加载到IPython，返回其他错误信息表示失败
        """
        content = self.load_note_api(path)
        method = self.plugin_manager.get_method("system.set_variable")
        if method:
            ret = method(variable_name, content)
            return "success" if ret else "set variable failed"
        else:
            return f"method not found for system.set_variable"
    
    def exec_note_in_ipython_api(self, path: str) -> dict:
        """
        API: 在IPython中执行记事本中保存的Python文件，返回执行结果

        Args:
            path: 文件路径(相对路径, 如scripts/demo.py)

        Returns:
            dict: {"success": bool, "output": str, "result": object, "error": str}
            success: 是否执行成功，output: print输出的内容，result: IPython代码块执行的返回值，error: 错误信息
        """
        path = os.path.join(self.notes_dir, path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"脚本文件不存在：{path}")
        if not path.endswith(".py"):
            return {"success": False,"error": f"invalid file type: {path} to execute in IPython"}
        method = self.plugin_manager.get_method("system.execute_code")
        if method:
            with open(path, "r", encoding="utf-8") as f:
                ret = method(f.read())
            return ret
        else:
            return {"success": False, "error": "method not found for system.execute_code"}

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
        if not relpath.lstrip("/\\").startswith(("scripts", "skills")):
            return False
    
        return True# return relpath.lstrip("/\\").startswith(("scripts",))

    def save_textfile_safe_api(self, path, content):
        """
        API: 保存文本文件, 目前仅允许操作scripts/下面的文件以及skills/../scripts/下面的文件。比如"scripts/demo.py", "skills/myskill/ability1/scripts/xx.py"是允许创建的, "abc/demo.py"就是不允许创建的

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

    def patch_textfile_safe_api(self, path: str, patch: str) -> str:
        """
        API: 安全地应用文本补丁，允许修改的文件也是scripts/下面的文件以及skills/../scripts/下面的文件
        
        接收 search...replace 格式的补丁，格式如下：
        <<<< SEARCH
        要搜索的内容
        ====
        替换后的内容
        >>>> REPLACE
        
        Args:
            path: str, 文件相对路径（只允许 scripts/ 和 skills/../scripts/ 下的文件）
            patch: str, 补丁内容（search...replace 格式）
        
        Returns:
            str: 操作结果状态信息
                - "success": 补丁应用成功
                - "path not allowed: {path}": 路径不允许
                - "file not found": 文件不存在
                - "patch format error": 补丁格式错误
                - "search content not found": 搜索内容在文件中未找到
                - "syntax error: {error}": Python 语法错误（仅对 .py 文件）
        """
        # 检查路径是否允许
        if not self._is_path_allowed(path):
            return f"path not allowed: {path}"
        
        # 构建完整路径
        full_path = os.path.join(self.notes_dir, path)
        
        # 检查文件是否存在
        if not os.path.exists(full_path):
            return "file not found"
        
        # 解析补丁 - 支持多个补丁块
        # 格式：<<<< SEARCH\n...\n====\n...\n>>>> REPLACE
        pattern = r'<<<<\s*SEARCH\s*\n(.*?)\n====\s*\n(.*?)\n>>>>\s*REPLACE'
        matches = list(re.finditer(pattern, patch, re.DOTALL))
        
        if not matches:
            return "patch format error: no valid patch blocks found"
        
        # 读取原文件内容
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return f"read file error: {e}"
        
        original_content = content
        applied_count = 0
        
        # 应用每个补丁块（从后往前应用，避免位置偏移问题）
        for match in reversed(matches):
            search_text = match.group(1)
            replace_text = match.group(2)
            
            # 检查搜索内容是否存在
            if search_text not in content:
                return f"search content not found: {repr(search_text[:50])}..."
            
            # 替换内容（只替换第一次出现）
            content = content.replace(search_text, replace_text, 1)
            applied_count += 1
        
        # 如果内容没有变化，说明补丁没有实际生效
        if content == original_content:
            return "patch had no effect"
        
        # 对于 .py 文件，检查语法
        if path.endswith('.py'):
            try:
                compile(content, full_path, 'exec')
            except SyntaxError as e:
                import traceback
                return traceback.format_exc()
        
        # 保存修改后的内容
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
        except Exception as e:
            return f"write file error: {e}"
        
        return f"success"

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

    def query_skills_api(self):
        """
        API: 查询技能名称

        Returns:
            str: 技能名称列表，多个技能名称用换行符分隔
        """
        skills_dir = self.skills_dir
        if not os.path.exists(skills_dir):
            return ""
        skills_list = os.listdir(skills_dir)
        return "\n".join(skills_list)
    
    def get_all_skills_summary_api(self) -> list[dict[str, Any]]:
        """
        API: 获取所有技能的概要信息（MCP 接口）
        
        Returns:
            list[dict]: 技能概要信息列表，每个包含:
                - name: 技能名称
                - description: 技能描述
                - path: 技能路径
                - has_scripts: 是否有 scripts 目录
                - has_references: 是否有 references 目录
                - has_assets: 是否有 assets 目录
                - version: 版本号
                - author: 作者
                - license: 许可证
        """
        from .utils.skill_format import SkillFormat
        
        # 扫描 skills 目录
        skills = SkillFormat.scan_skills_tree(self.skills_dir)
        
        # # 返回相对路径
        # for skill in skills:
        #     skill['path'] = os.path.relpath(skill['path'], self.notes_dir)
        
        return skills
    
    def get_skill_detail_api(self, skill_name: str) -> dict[str, Any]:
        """
        API: 获取单个技能的详细信息（MCP 接口）
        
        Args:
            skill_name: 技能名称（kebab-case 格式，如 "pdf-processing"）
            
        Returns:
            dict: 技能详细信息，包含:
                - name: 技能名称
                - description: 技能描述
                - path: 技能路径
                - metadata: 完整的 YAML 元数据
                - content: Markdown 正文内容
                - full_content: 完整内容（包含 frontmatter）
                - scripts: scripts 目录下的文件列表
                - references: references 目录下的文件列表
                - assets: assets 目录下的文件列表
                
        Raises:
            FileNotFoundError: 如果技能不存在
        """
        from .utils.skill_format import SkillFormat
        
        # 构建技能目录路径
        skill_dir = os.path.join(self.skills_dir, skill_name)
        
        if not os.path.exists(skill_dir):
            raise FileNotFoundError(f"技能不存在：{skill_name}")
        
        # 加载详细信息
        detail = SkillFormat.load_skill_detail(skill_dir)
        
        if not detail:
            raise FileNotFoundError(f"无法加载技能：{skill_name}")
        
        # 转换为相对路径
        detail['path'] = os.path.relpath(skill_dir, self.notes_dir)
        
        return detail

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

    def copy_file_api(self, source_path: str, target_path: str) -> str:
        """
        API: 复制文件到新路径

        Args:
            source_path: 源文件相对路径（相对于笔记目录）
            target_path: 目标文件相对路径（相对于笔记目录）

        Returns:
            str: 操作结果，"success"表示成功，其他为错误信息
        """
        import shutil
        
        full_source = os.path.join(self.notes_dir, source_path)
        full_target = os.path.join(self.notes_dir, target_path)
        
        # 检查源文件是否存在
        if not os.path.exists(full_source):
            return f"source file not found: {source_path}"
        
        # 只能复制文件
        if not os.path.isfile(full_source):
            return f"source is not a file: {source_path}"
        
        # 确保目标目录存在
        try:
            os.makedirs(os.path.dirname(full_target), exist_ok=True)
            shutil.copy2(full_source, full_target)
            
            # 文件系统监听会自动添加节点到树
            
            return "success"
        except Exception as e:
            return f"copy failed: {str(e)}"

    def backup_file_api(self, file_path: str, backup_name: str = None) -> str:
        """
        API: 备份文件到 backups 文件夹

        Args:
            file_path: 要备份的文件相对路径（相对于笔记目录）
            backup_name: 备份文件名（可选，默认在原文件名后加时间戳）

        Returns:
            str: 操作结果，"success"表示成功，其他为错误信息
        """
        import shutil
        from datetime import datetime
        
        full_source = os.path.join(self.notes_dir, file_path)
        
        # 检查源文件是否存在
        if not os.path.exists(full_source):
            return f"file not found: {file_path}"
        
        # 只能备份文件
        if not os.path.isfile(full_source):
            return f"not a file: {file_path}"
        
        # 创建 backups 目录
        backups_dir = os.path.join(self.notes_dir, "backups")
        os.makedirs(backups_dir, exist_ok=True)
        
        # 确定备份文件名
        original_name = os.path.basename(file_path)
        if backup_name:
            backup_filename = backup_name
        else:
            # 默认格式：原文件名_YYYYMMDD_HHMMSS.ext
            name, ext = os.path.splitext(original_name)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{name}_{timestamp}{ext}"
        
        full_backup = os.path.join(backups_dir, backup_filename)
        
        try:
            shutil.copy2(full_source, full_backup)
            return "success"
        except Exception as e:
            return f"backup failed: {str(e)}"

    def on_ipython_ready(self):
        """
        处理IPython就绪事件，在
        """
        logger.info("快速笔记插件正在加载IPython环境变量")
        data_file = os.path.join(self.notes_dir, "_env_.json")
        if not os.path.exists(data_file):
            with open(data_file, "w", encoding="utf-8") as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
        with open(data_file, "r", encoding="utf-8") as f:
            _env = json.load(f)
        set_variable_method = self.plugin_manager.get_method("system.set_variable")
        if set_variable_method:
            set_variable_method("_env_", _env)
        else:
            logger.warning("系统方法 'set_variable' 不存在，无法设置环境变量")
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

    plugin_manager.ipython_ready_signal.connect(notes_tab.on_ipython_ready)
    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "quick_notes", "create_note", notes_tab.create_note_api
    )
    plugin_manager.register_method("quick_notes", "load_note", notes_tab.load_note_api)
    plugin_manager.register_method(
        "quick_notes", "read_note", notes_tab.load_note_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", "load_note_to_ipython", notes_tab.load_note_to_ipython_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method("quick_notes", "save_note", notes_tab.save_note_api)
    plugin_manager.register_method(
        "quick_notes", "query_note_by_name", notes_tab.query_note_by_name_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", "query_notes_by_text", notes_tab.query_notes_by_text_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", "save_textfile_safe", notes_tab.save_textfile_safe_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", "patch_textfile_safe", notes_tab.patch_textfile_safe_api, extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", "exec_note_in_ipython", notes_tab.exec_note_in_ipython_api, extra_data={"enable_mcp": True}
    )
    
    # 注册技能相关的 MCP 接口
    plugin_manager.register_method(
        "quick_notes", 
        "get_all_skills_summary", 
        notes_tab.get_all_skills_summary_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", 
        "get_skill_detail", 
        notes_tab.get_skill_detail_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", 
        "query_skills", 
        notes_tab.query_skills_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", 
        "copy_file", 
        notes_tab.copy_file_api,
        extra_data={"enable_mcp": True}
    )
    plugin_manager.register_method(
        "quick_notes", 
        "backup_file", 
        notes_tab.backup_file_api,
        extra_data={"enable_mcp": True}
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
