"""
快速笔记插件 - 笔记树组件
提供树状结构的笔记管理和导航功能
"""

import os
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QMessageBox,
    QApplication, QStyle, QHBoxLayout, QWidget, QPushButton
)
from PySide6.QtCore import Qt, Signal


class NoteTreeWidget(QTreeWidget):
    """笔记树组件"""
    
    # 信号：笔记项被点击
    note_clicked = Signal(str)  # file_path
    
    # 信号：需要刷新树
    refresh_requested = Signal()
    
    def __init__(self, notes_dir, allowed_extensions):
        super().__init__()
        self.notes_dir = notes_dir
        self.allowed_extensions = allowed_extensions
        
        # 配置树的基本属性
        self.setHeaderLabel("笔记目录")
        self.setFont(self.font())
        self.itemClicked.connect(self.on_item_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # 创建刷新按钮（悬浮在右上角）
       
        # 加载树结构
        self.load_tree()
    
    def resizeEvent(self, event):
        """窗口大小改变事件 - 更新按钮位置"""
        super().resizeEvent(event)
       
    def _on_refresh_button_clicked(self):
        """刷新按钮点击事件"""
        self.load_tree()
        self.refresh_requested.emit()
    
    def load_tree(self):
        """加载笔记树状结构（支持无限层级）- 性能优化版"""
        # 禁用 UI 更新以提高性能
        self.setUpdatesEnabled(False)
        try:
            self.clear()
            
            if not os.path.exists(self.notes_dir):
                return
            
            # 缓存图标，避免重复获取
            dir_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
            file_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
            allowed_tuple = tuple(self.allowed_extensions)
            
            # 使用字典存储所有节点，key 为相对路径，value 为 QTreeWidgetItem
            items_dict = {}
            
            # 单次遍历：同时处理文件夹和文件节点
            for root, dirs, files in os.walk(self.notes_dir):
                # 跳过隐藏目录
                dirs[:] = sorted([d for d in dirs if not d.startswith(".")])
                
                # 获取当前层级的相对路径
                rel_root = os.path.relpath(root, self.notes_dir)
                if rel_root == '.':
                    rel_root = ''
                
                # 创建子目录项
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    rel_dir_path = os.path.relpath(dir_path, self.notes_dir)
                    
                    item = QTreeWidgetItem([dir_name])
                    item.setData(0, Qt.ItemDataRole.UserRole, dir_path)
                    item.setIcon(0, dir_icon)
                    
                    items_dict[rel_dir_path] = item
                    
                    # 找到父节点并添加
                    if rel_root:
                        parent_item = items_dict.get(rel_root)
                        if parent_item:
                            parent_item.addChild(item)
                    else:
                        # 根目录下的直接子目录
                        self.addTopLevelItem(item)
                
                # 添加文件项
                for file_name in sorted(files):
                    if file_name.endswith(allowed_tuple):
                        file_path = os.path.join(root, file_name)
                        
                        item = QTreeWidgetItem([file_name])
                        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                        item.setIcon(0, file_icon)
                        
                        # 找到父节点并添加
                        if rel_root:
                            parent_item = items_dict.get(rel_root)
                            if parent_item:
                                parent_item.addChild(item)
                        else:
                            # 根目录下的直接文件
                            self.addTopLevelItem(item)
            
            # 展开所有节点
            self.expandAll()
        finally:
            # 重新启用 UI 更新
            self.setUpdatesEnabled(True)
    
    def _find_parent_items(self, parent_name):
        """查找父节点"""
        return self.findItems(parent_name, Qt.MatchFlag.MatchContains)
    
    def on_item_clicked(self, item, column):
        """树节点点击事件"""
        file_path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if file_path and os.path.isfile(file_path):
            self.note_clicked.emit(file_path)
    
    def show_context_menu(self, pos):
        """显示右键菜单"""
        menu = QMenu(self)
        
        # 获取选中项的路径（如果有）
        selected_items = self.selectedItems()
        selected_path = None
        if selected_items:
            selected_path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        
        # 新建笔记
        new_note_action = menu.addAction("📄 新建笔记")
        new_note_action.triggered.connect(self.context_new_note)
        
        # 新建文件夹
        new_folder_action = menu.addAction("📁 新建文件夹")
        new_folder_action.triggered.connect(self.context_new_folder)
        
        menu.addSeparator()
        
        # 重命名
        rename_action = menu.addAction("✏️ 重命名")
        rename_action.triggered.connect(self.rename_selected)
        
        # 删除
        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(self.delete_selected_with_confirm)
        
        # 如果有选中项，添加复制路径选项
        if selected_path:
            menu.addSeparator()
            
            # 复制完整路径
            copy_full_path_action = menu.addAction("📋 复制完整路径")
            copy_full_path_action.triggered.connect(
                lambda: self._copy_to_clipboard(selected_path)
            )
            
            # 复制相对路径
            copy_rel_path_action = menu.addAction("📋 复制相对路径")
            copy_rel_path_action.triggered.connect(
                lambda: self._copy_to_clipboard(
                    os.path.relpath(selected_path, self.notes_dir)
                )
            )
        
        menu.addSeparator()
        
        # 在文件管理器中打开
        open_location_action = menu.addAction("📂 在文件管理器中打开")
        open_location_action.triggered.connect(self.open_in_explorer)
        
        menu.exec_(self.viewport().mapToGlobal(pos))
    
    def _copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def rename_selected(self):
        """重命名选中的项目"""
        selected_items = self.selectedItems()
        
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
            self.load_tree()
            
            # 发射刷新信号
            self.refresh_requested.emit()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法重命名：{str(e)}")
    
    def open_in_explorer(self):
        """在文件管理器中打开"""
        selected_items = self.selectedItems()
        
        if not selected_items:
            return
        
        path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        
        if os.path.isfile(path):
            path = os.path.dirname(path)
        
        os.startfile(path)
    
    def get_selected_path(self):
        """获取选中项的路径"""
        selected_items = self.selectedItems()
        if selected_items:
            return selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        return None
    
    def create_new_note(self, name, parent_path=None):
        """创建新笔记"""
        if not parent_path:
            parent_path = self.notes_dir
        
        # 构建完整路径
        if not name.strip().endswith(self.allowed_extensions):
            file_name = f"{name.strip()}.md"
        else:
            file_name = name.strip()
        file_path = os.path.join(parent_path, file_name)
        
        # 检查是否已存在
        if os.path.exists(file_path):
            raise FileExistsError(f"同名文件已存在：{file_path}")
        
        # 创建空文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("")
        
        # 刷新树
        self.load_tree()
        
        return file_path
    
    def create_new_folder(self, name, parent_path=None):
        """创建新文件夹"""
        if not parent_path:
            parent_path = self.notes_dir
        
        folder_path = os.path.join(parent_path, name.strip())
        
        # 检查是否已存在
        if os.path.exists(folder_path):
            raise FileExistsError(f"同名文件夹已存在：{folder_path}")
        
        # 创建文件夹
        os.makedirs(folder_path)
        
        # 刷新树
        self.load_tree()
        
        return folder_path
    
    def context_new_note(self):
        """上下文菜单 - 新建笔记"""
        selected_items = self.selectedItems()
        
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
        
        try:
            file_path = self.create_new_note(name.strip(), parent_path)
            # 发射刷新信号
            self.refresh_requested.emit()
            # 通知主窗口加载新笔记
            self.note_clicked.emit(file_path)
        except FileExistsError as e:
            QMessageBox.warning(self, "警告", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建笔记：{str(e)}")
    
    def context_new_folder(self):
        """上下文菜单 - 新建文件夹"""
        selected_items = self.selectedItems()
        
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
        
        try:
            folder_path = self.create_new_folder(name.strip(), parent_path)
            # 发射刷新信号
            self.refresh_requested.emit()
        except FileExistsError as e:
            QMessageBox.warning(self, "警告", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法创建文件夹：{str(e)}")
    
    def delete_selected(self):
        """删除选中的项目"""
        selected_items = self.selectedItems()
        
        if not selected_items:
            return None
        
        item = selected_items[0]
        path = item.data(0, Qt.ItemDataRole.UserRole)
        
        if not path:
            return None
        
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
            
            # 刷新树
            self.load_tree()
            
            return path
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法删除：{str(e)}")
            return None
    
    def delete_selected_with_confirm(self):
        """上下文菜单 - 删除（带确认对话框）"""
        selected_items = self.selectedItems()
        
        if not selected_items:
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
            deleted_path = self.delete_selected()
            if deleted_path:
                # 发射刷新信号
                self.refresh_requested.emit()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法删除：{str(e)}")
