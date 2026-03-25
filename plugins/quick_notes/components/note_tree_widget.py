"""
快速笔记插件 - 笔记树组件
提供树状结构的笔记管理和导航功能
使用 watchdog 监听文件系统事件实现增量更新
"""

import os
import shutil
from PySide6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QMessageBox,
    QApplication, QStyle
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QKeySequence, QShortcut, QIcon

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
WATCHDOG_AVAILABLE = True


class FileSystemEventHandlerSignals(QObject):
    """文件系统事件处理器信号"""
    file_created = Signal(str)  # file_path
    file_deleted = Signal(str)  # file_path
    file_moved = Signal(str, str)  # src_path, dest_path
    dir_created = Signal(str)  # dir_path
    dir_deleted = Signal(str)  # dir_path
    dir_moved = Signal(str, str)  # src_path, dest_path


class QFileSystemEventHandler(FileSystemEventHandler):
    """Qt 友好的文件系统事件处理器"""
    
    def __init__(self, watch_path):
        super().__init__()
        self.signals = FileSystemEventHandlerSignals()
        self.watch_path = os.path.normpath(os.path.abspath(watch_path))
    
    def _normalize_path(self, path):
        """规范化路径"""
        return os.path.normpath(os.path.abspath(path))
    
    def _normalize_path(self, path):
        """规范化路径"""
        return os.path.normpath(os.path.abspath(path))
    
    def dispatch(self, event):
        """分发事件 - 重写以确保信号在主线程发射"""
        # 规范化路径
        src_path = self._normalize_path(event.src_path) if hasattr(event, 'src_path') else None
        dest_path = self._normalize_path(event.dest_path) if hasattr(event, 'dest_path') else None
        
        if event.event_type == 'created':
            if event.is_directory:
                print(f"[Watchdog] 目录创建: {src_path}")
                self.signals.dir_created.emit(src_path)
            else:
                print(f"[Watchdog] 文件创建: {src_path}")
                self.signals.file_created.emit(src_path)
        elif event.event_type == 'deleted':
            if event.is_directory:
                print(f"[Watchdog] 目录删除: {src_path}")
                self.signals.dir_deleted.emit(src_path)
            else:
                print(f"[Watchdog] 文件删除: {src_path}")
                self.signals.file_deleted.emit(src_path)
        elif event.event_type == 'moved':
            if event.is_directory:
                print(f"[Watchdog] 目录移动: {src_path} -> {dest_path}")
                self.signals.dir_moved.emit(src_path, dest_path)
            else:
                print(f"[Watchdog] 文件移动: {src_path} -> {dest_path}")
                self.signals.file_moved.emit(src_path, dest_path)
        elif event.event_type == 'modified':
            # 文件内容修改（不关心目录修改）
            if not event.is_directory:
                print(f"[Watchdog] 文件修改: {src_path}")
                # 可以在这里添加文件内容修改的通知
                pass


class FileSystemWatcher(QObject):
    """文件系统监视器"""
    
    def __init__(self, watch_path):
        super().__init__()
        # 规范化路径
        self.watch_path = os.path.normpath(os.path.abspath(watch_path))
        self.event_handler = QFileSystemEventHandler(self.watch_path)
        self.observer = Observer()
    
    def start(self):
        """开始监听"""
        if os.path.exists(self.watch_path):
            try:
                self.observer.schedule(self.event_handler, self.watch_path, recursive=True)
                self.observer.start()
                print(f"[NoteTree] 开始监听目录: {self.watch_path}")
            except Exception as e:
                print(f"[NoteTree] 启动监听失败: {e}")
        else:
            print(f"[NoteTree] 监听路径不存在: {self.watch_path}")
    
    def stop(self):
        """停止监听"""
        try:
            self.observer.stop()
            self.observer.join()
            print("[NoteTree] 停止文件系统监听")
        except Exception as e:
            print(f"[NoteTree] 停止监听失败: {e}")
    
    def get_signals(self):
        """获取信号对象"""
        return self.event_handler.signals


class NoteTreeWidget(QTreeWidget):
    """笔记树组件"""
    
    # 信号：笔记项被点击
    note_clicked = Signal(str)  # file_path
    
    # 信号：需要刷新树（手动刷新按钮触发）
    refresh_requested = Signal()
    
    # 信号：创建技能
    create_skill_requested = Signal(str)  # parent_path
    
    # 类级别的剪贴板，用于复制/粘贴文件
    _clipboard_path = None
    _clipboard_cut = False  # 标记是否为剪切操作
    
    def __init__(self, notes_dir, allowed_extensions):
        super().__init__()
        self.notes_dir = notes_dir
        self.allowed_extensions = allowed_extensions
        
        # 节点字典：key 为绝对路径，value 为 QTreeWidgetItem
        self._items_dict = {}
        
        # 图标缓存
        self._dir_icon = None
        self._dir_open_icon = None
        self._file_icon = None
        
        # 设置展开/折叠图标切换
        self.itemExpanded.connect(self._on_item_expanded)
        self.itemCollapsed.connect(self._on_item_collapsed)
        
        # 配置树的基本属性
        self.setHeaderLabel("笔记目录")
        self.setFont(self.font())
        self.itemClicked.connect(self.on_item_clicked)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        
        # 创建快捷键
        self._setup_shortcuts()
        
        # 规范化 notes_dir 路径
        self.notes_dir = os.path.normpath(os.path.abspath(notes_dir))
        
        # 初始化文件系统监视器
        self._watcher = FileSystemWatcher(self.notes_dir)
        signals = self._watcher.get_signals()
        signals.file_created.connect(self._on_file_created)
        signals.file_deleted.connect(self._on_file_deleted)
        signals.file_moved.connect(self._on_file_moved)
        signals.dir_created.connect(self._on_dir_created)
        signals.dir_deleted.connect(self._on_dir_deleted)
        signals.dir_moved.connect(self._on_dir_moved)
        print("[NoteTree] 文件系统事件信号已连接")
        
        # 加载树结构
        self.load_tree()
        
        # 启动文件系统监听
        self._watcher.start()
    
    def __del__(self):
        """析构时停止监听"""
        if hasattr(self, '_watcher'):
            self._watcher.stop()
    
    def _get_icons(self):
        """获取图标（延迟初始化）"""
        if self._dir_icon is None:
            self._dir_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirClosedIcon)
            self._dir_open_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
            self._file_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        return self._dir_icon, self._dir_open_icon, self._file_icon
    
    def _on_item_expanded(self, item):
        """节点展开时切换图标"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            _, dir_open_icon, _ = self._get_icons()
            item.setIcon(0, dir_open_icon)
    
    def _on_item_collapsed(self, item):
        """节点折叠时切换图标"""
        path = item.data(0, Qt.ItemDataRole.UserRole)
        if path and os.path.isdir(path):
            dir_icon, _, _ = self._get_icons()
            item.setIcon(0, dir_icon)
    
    def _on_refresh_button_clicked(self):
        """刷新按钮点击事件 - 唯一的手动刷新入口"""
        self.load_tree()
        self.refresh_requested.emit()
    
    def _setup_shortcuts(self):
        """设置键盘快捷键"""
        # F2 - 重命名
        rename_shortcut = QShortcut(QKeySequence("F2"), self)
        rename_shortcut.activated.connect(self.rename_selected)
        
        # Delete - 删除
        delete_shortcut = QShortcut(QKeySequence("Delete"), self)
        delete_shortcut.activated.connect(self.delete_selected_with_confirm)
        
        # Ctrl+C - 复制文件
        copy_shortcut = QShortcut(QKeySequence.Copy, self)
        copy_shortcut.activated.connect(self.copy_selected_file)
        
        # Ctrl+X - 剪切文件
        cut_shortcut = QShortcut(QKeySequence.Cut, self)
        cut_shortcut.activated.connect(self.cut_selected_file)
        
        # Ctrl+V - 粘贴文件
        paste_shortcut = QShortcut(QKeySequence.Paste, self)
        paste_shortcut.activated.connect(self.paste_file)
        
        # Ctrl+N - 新建笔记
        new_note_shortcut = QShortcut(QKeySequence.New, self)
        new_note_shortcut.activated.connect(self.context_new_note)
        
        # Ctrl+Shift+N - 新建文件夹
        new_folder_shortcut = QShortcut(QKeySequence("Ctrl+Shift+N"), self)
        new_folder_shortcut.activated.connect(self.context_new_folder)
        
        # Ctrl+Shift+S - 创建技能
        create_skill_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        create_skill_shortcut.activated.connect(self.context_create_skill)
        
        # F5 / Ctrl+R - 刷新
        refresh_shortcut = QShortcut(QKeySequence.Refresh, self)
        refresh_shortcut.activated.connect(self._on_refresh_button_clicked)
        # 备用刷新快捷键
        refresh_shortcut2 = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut2.activated.connect(self._on_refresh_button_clicked)
    
    # ========== 文件系统事件处理（增量更新） ==========
    
    def _on_file_created(self, file_path):
        """文件创建事件"""
        # 规范化路径
        file_path = os.path.normpath(os.path.abspath(file_path))
        
        # 检查扩展名是否允许
        if not file_path.lower().endswith(tuple(ext.lower() for ext in self.allowed_extensions)):
            print(f"[NoteTree] 忽略不支持的文件类型: {file_path}")
            return
        
        # 检查是否在笔记目录下
        if not file_path.startswith(self.notes_dir):
            print(f"[NoteTree] 忽略不在笔记目录下的文件: {file_path}")
            return
        
        print(f"[NoteTree] 处理文件创建: {file_path}")
        self._add_file_node(file_path)
    
    def _on_file_deleted(self, file_path):
        """文件删除事件"""
        file_path = os.path.normpath(os.path.abspath(file_path))
        print(f"[NoteTree] 处理文件删除: {file_path}")
        self._remove_node(file_path)
    
    def _on_file_moved(self, src_path, dest_path):
        """文件移动/重命名事件"""
        src_path = os.path.normpath(os.path.abspath(src_path))
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        print(f"[NoteTree] 处理文件移动: {src_path} -> {dest_path}")
        # 先删除旧节点
        self._remove_node(src_path)
        # 如果目标扩展名允许且仍在笔记目录下，添加新节点
        if dest_path.lower().endswith(tuple(ext.lower() for ext in self.allowed_extensions)):
            if dest_path.startswith(self.notes_dir):
                self._add_file_node(dest_path)
    
    def _on_dir_created(self, dir_path):
        """目录创建事件"""
        dir_path = os.path.normpath(os.path.abspath(dir_path))
        
        # 检查是否在笔记目录下
        if not dir_path.startswith(self.notes_dir):
            print(f"[NoteTree] 忽略不在笔记目录下的目录: {dir_path}")
            return
        
        print(f"[NoteTree] 处理目录创建: {dir_path}")
        self._add_dir_node(dir_path)
    
    def _on_dir_deleted(self, dir_path):
        """目录删除事件"""
        dir_path = os.path.normpath(os.path.abspath(dir_path))
        print(f"[NoteTree] 处理目录删除: {dir_path}")
        self._remove_node(dir_path)
    
    def _on_dir_moved(self, src_path, dest_path):
        """目录移动/重命名事件"""
        src_path = os.path.normpath(os.path.abspath(src_path))
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        print(f"[NoteTree] 处理目录移动: {src_path} -> {dest_path}")
        # 需要重新加载该目录及其子项
        self._remove_node(src_path)
        if dest_path.startswith(self.notes_dir):
            self._add_dir_with_children(dest_path)
    
    # ========== 增量节点操作方法 ==========
    
    def _get_parent_item(self, path):
        """获取指定路径的父节点"""
        parent_dir = os.path.dirname(path)
        if parent_dir == self.notes_dir or not parent_dir.startswith(self.notes_dir):
            return None  # 顶级节点
        return self._items_dict.get(parent_dir)
    
    def _add_file_node(self, file_path):
        """添加文件节点"""
        if file_path in self._items_dict:
            return  # 已存在
        
        _, _, file_icon = self._get_icons()
        file_name = os.path.basename(file_path)
        
        item = QTreeWidgetItem([file_name])
        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
        item.setIcon(0, file_icon)
        
        # 添加到父节点或作为顶级节点
        parent_item = self._get_parent_item(file_path)
        if parent_item:
            parent_item.addChild(item)
        else:
            self.addTopLevelItem(item)
        
        self._items_dict[file_path] = item
        print(f"[NoteTree] 添加文件节点: {file_path}")
    
    def _add_dir_node(self, dir_path):
        """添加目录节点"""
        if dir_path in self._items_dict:
            return  # 已存在
        
        dir_icon, _, _ = self._get_icons()
        dir_name = os.path.basename(dir_path)
        
        item = QTreeWidgetItem([dir_name])
        item.setData(0, Qt.ItemDataRole.UserRole, dir_path)
        item.setIcon(0, dir_icon)
        
        # 添加到父节点或作为顶级节点
        parent_item = self._get_parent_item(dir_path)
        if parent_item:
            parent_item.addChild(item)
        else:
            self.addTopLevelItem(item)
        
        self._items_dict[dir_path] = item
        print(f"[NoteTree] 添加目录节点: {dir_path}")
    
    def _add_dir_with_children(self, dir_path):
        """添加目录及其所有子项（用于移动后的恢复）"""
        dir_path = os.path.normpath(os.path.abspath(dir_path))
        
        if not os.path.exists(dir_path):
            print(f"[NoteTree] 目录不存在，跳过: {dir_path}")
            return
        
        # 添加目录本身
        self._add_dir_node(dir_path)
        
        # 递归添加所有子项
        try:
            for entry in os.scandir(dir_path):
                entry_path = os.path.normpath(os.path.abspath(entry.path))
                if entry.is_dir():
                    self._add_dir_with_children(entry_path)
                elif entry.is_file() and entry.name.lower().endswith(tuple(ext.lower() for ext in self.allowed_extensions)):
                    self._add_file_node(entry_path)
        except Exception as e:
            print(f"[NoteTree] 添加目录子项失败: {e}")
    
    def _remove_node(self, path):
        """移除节点及其所有子节点"""
        # 收集所有需要删除的节点（包括子节点）
        paths_to_remove = [p for p in self._items_dict.keys() if p == path or p.startswith(path + os.sep)]
        
        for p in paths_to_remove:
            item = self._items_dict.pop(p, None)
            if item:
                # 从父节点中移除
                parent = item.parent()
                if parent:
                    parent.removeChild(item)
                else:
                    # 顶级节点
                    index = self.indexOfTopLevelItem(item)
                    if index >= 0:
                        self.takeTopLevelItem(index)
        
        if paths_to_remove:
            print(f"[NoteTree] 移除节点: {path} 及 {len(paths_to_remove)-1} 个子项")
    
    def _rename_node(self, old_path, new_path):
        """重命名节点"""
        item = self._items_dict.pop(old_path, None)
        if item:
            self._items_dict[new_path] = item
            item.setData(0, Qt.ItemDataRole.UserRole, new_path)
            item.setText(0, os.path.basename(new_path))
            print(f"[NoteTree] 重命名节点: {old_path} -> {new_path}")
    
    # ========== 完整加载（手动刷新用） ==========
    
    def load_tree(self):
        """加载笔记树状结构（完整刷新）- 仅手动刷新按钮调用"""
        print("[NoteTree] 完整刷新树...")
        
        # 禁用 UI 更新以提高性能
        self.setUpdatesEnabled(False)
        try:
            self.clear()
            self._items_dict.clear()
            
            if not os.path.exists(self.notes_dir):
                print(f"[NoteTree] 笔记目录不存在: {self.notes_dir}")
                return
            
            # 缓存图标
            dir_icon, dir_open_icon, file_icon = self._get_icons()
            allowed_tuple = tuple(self.allowed_extensions)
            
            # 单次遍历：同时处理文件夹和文件节点
            for root, dirs, files in os.walk(self.notes_dir):
                # 跳过隐藏目录
                dirs[:] = sorted([d for d in dirs if not d.startswith(".")])
                
                # 规范化当前目录路径
                root = os.path.normpath(os.path.abspath(root))
                
                # 获取当前层级的相对路径
                rel_root = os.path.relpath(root, self.notes_dir)
                if rel_root == '.':
                    rel_root = ''
                
                # 创建子目录项
                for dir_name in dirs:
                    dir_path = os.path.normpath(os.path.abspath(os.path.join(root, dir_name)))
                    
                    item = QTreeWidgetItem([dir_name])
                    item.setData(0, Qt.ItemDataRole.UserRole, dir_path)
                    # 根据展开状态设置图标
                    if item.isExpanded():
                        item.setIcon(0, dir_open_icon)
                    else:
                        item.setIcon(0, dir_icon)
                    
                    self._items_dict[dir_path] = item
                    
                    # 找到父节点并添加
                    if rel_root:
                        parent_item = self._items_dict.get(root)
                        if parent_item:
                            parent_item.addChild(item)
                    else:
                        # 根目录下的直接子目录
                        self.addTopLevelItem(item)
                
                # 添加文件项
                for file_name in sorted(files):
                    if file_name.lower().endswith(tuple(ext.lower() for ext in allowed_tuple)):
                        file_path = os.path.normpath(os.path.abspath(os.path.join(root, file_name)))
                        
                        item = QTreeWidgetItem([file_name])
                        item.setData(0, Qt.ItemDataRole.UserRole, file_path)
                        item.setIcon(0, file_icon)
                        
                        self._items_dict[file_path] = item
                        
                        # 找到父节点并添加
                        if rel_root:
                            parent_item = self._items_dict.get(root)
                            if parent_item:
                                parent_item.addChild(item)
                        else:
                            # 根目录下的直接文件
                            self.addTopLevelItem(item)
            
            # 只展开第一层节点，不全部展开
            self.expandToDepth(0)
            print(f"[NoteTree] 树加载完成，共 {len(self._items_dict)} 个节点")
        finally:
            # 重新启用 UI 更新
            self.setUpdatesEnabled(True)
    
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
        new_note_action.setShortcut(QKeySequence.New)
        
        # 新建文件夹
        new_folder_action = menu.addAction("📁 新建文件夹")
        new_folder_action.triggered.connect(self.context_new_folder)
        new_folder_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        
        # 创建技能
        create_skill_action = menu.addAction("✨ 创建技能")
        create_skill_action.triggered.connect(self.context_create_skill)
        create_skill_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        
        menu.addSeparator()
        
        # 重命名
        rename_action = menu.addAction("✏️ 重命名")
        rename_action.triggered.connect(self.rename_selected)
        rename_action.setShortcut(QKeySequence("F2"))
        
        # 删除
        delete_action = menu.addAction("🗑️ 删除")
        delete_action.triggered.connect(self.delete_selected_with_confirm)
        delete_action.setShortcut(QKeySequence("Delete"))
        
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
            
            # 复制文件（用于粘贴）
            copy_file_action = menu.addAction("📄 复制")
            copy_file_action.triggered.connect(self.copy_selected_file)
            copy_file_action.setShortcut(QKeySequence.Copy)
            
            # 剪切文件
            cut_file_action = menu.addAction("✂️ 剪切")
            cut_file_action.triggered.connect(self.cut_selected_file)
            cut_file_action.setShortcut(QKeySequence.Cut)
        
        # 粘贴文件（无论是否有选中项都可以粘贴）
        if NoteTreeWidget._clipboard_path:
            paste_action = menu.addAction("📋 粘贴")
            paste_action.triggered.connect(self.paste_file)
            paste_action.setShortcut(QKeySequence.Paste)
        
        menu.addSeparator()
        
        # 在文件管理器中打开
        open_location_action = menu.addAction("📂 在文件管理器中打开")
        open_location_action.triggered.connect(self.open_in_explorer)
        
        # 手动刷新（保留）
        menu.addSeparator()
        refresh_action = menu.addAction("🔄 刷新")
        refresh_action.triggered.connect(self._on_refresh_button_clicked)
        refresh_action.setShortcut(QKeySequence.Refresh)
        
        menu.exec_(self.viewport().mapToGlobal(pos))
    
    def _copy_to_clipboard(self, text):
        """复制文本到剪贴板"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
    
    def copy_selected_file(self):
        """复制选中的文件到内部剪贴板"""
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "警告", "只能复制文件")
            return
        
        NoteTreeWidget._clipboard_path = path
        NoteTreeWidget._clipboard_cut = False
        QMessageBox.information(self, "成功", f"已复制文件：{os.path.basename(path)}")
    
    def cut_selected_file(self):
        """剪切选中的文件到内部剪贴板"""
        selected_items = self.selectedItems()
        if not selected_items:
            return
        
        path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
        if not path or not os.path.isfile(path):
            QMessageBox.warning(self, "警告", "只能剪切文件")
            return
        
        NoteTreeWidget._clipboard_path = path
        NoteTreeWidget._clipboard_cut = True
        QMessageBox.information(self, "成功", f"已剪切文件：{os.path.basename(path)}")
    
    def paste_file(self):
        """粘贴文件到当前选中的文件夹"""
        if not NoteTreeWidget._clipboard_path:
            return
        
        # 确定目标目录
        selected_items = self.selectedItems()
        if selected_items:
            target_path = selected_items[0].data(0, Qt.ItemDataRole.UserRole)
            # 如果是文件，取父目录
            if os.path.isfile(target_path):
                target_dir = os.path.dirname(target_path)
            else:
                target_dir = target_path
        else:
            target_dir = self.notes_dir
        
        source_path = NoteTreeWidget._clipboard_path
        file_name = os.path.basename(source_path)
        target_file_path = os.path.join(target_dir, file_name)
        
        # 检查目标是否已存在
        if os.path.exists(target_file_path):
            reply = QMessageBox.question(
                self,
                "确认覆盖",
                f'文件 "{file_name}" 已存在，是否覆盖？',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        try:
            if NoteTreeWidget._clipboard_cut:
                # 剪切操作：移动文件
                shutil.move(source_path, target_file_path)
                QMessageBox.information(self, "成功", f"已移动文件到：{target_dir}")
                # 清除剪贴板
                NoteTreeWidget._clipboard_path = None
                NoteTreeWidget._clipboard_cut = False
                # 文件系统监听会自动处理节点更新
            else:
                # 复制操作
                shutil.copy2(source_path, target_file_path)
                QMessageBox.information(self, "成功", f"已复制文件到：{target_dir}")
                # 文件系统监听会自动处理节点更新
            
            # 注意：不再手动调用 load_tree()，由文件系统监听处理
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"操作失败：{str(e)}")
    
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
            # 注意：不再手动调用 load_tree()，由文件系统监听处理节点更新
            # 发射刷新信号通知其他组件
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
        """创建新笔记 - 仅创建文件，不刷新树"""
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
        
        # 注意：不再调用 load_tree()，由文件系统监听自动添加节点
        
        return file_path
    
    def create_new_folder(self, name, parent_path=None):
        """创建新文件夹 - 仅创建文件夹，不刷新树"""
        if not parent_path:
            parent_path = self.notes_dir
        
        folder_path = os.path.join(parent_path, name.strip())
        
        # 检查是否已存在
        if os.path.exists(folder_path):
            raise FileExistsError(f"同名文件夹已存在：{folder_path}")
        
        # 创建文件夹
        os.makedirs(folder_path)
        
        # 注意：不再调用 load_tree()，由文件系统监听自动添加节点
        
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
    
    def context_create_skill(self):
        """上下文菜单 - 创建技能"""
        selected_items = self.selectedItems()
        
        if selected_items:
            parent_item = selected_items[0]
            parent_path = parent_item.data(0, Qt.ItemDataRole.UserRole)
            
            # 如果是文件，取父目录
            if os.path.isfile(parent_path):
                parent_path = os.path.dirname(parent_path)
        else:
            parent_path = self.notes_dir
        
        # 发射创建技能请求信号，通知主窗口处理
        self.create_skill_requested.emit(parent_path)
    
    def delete_selected(self):
        """删除选中的项目 - 仅删除，不刷新树"""
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
                shutil.rmtree(path)
            
            # 注意：不再调用 load_tree()，由文件系统监听自动移除节点
            
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
