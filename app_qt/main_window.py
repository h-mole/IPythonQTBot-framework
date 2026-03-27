"""
IPythonQTBot - PySide6 版本
迁移自 helperscript.py
"""

import sys
import os
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenuBar,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QListWidget,
    QGroupBox,
    QFrame,
    QSplitter,
    QSystemTrayIcon,
    QMenu,
    QToolBar,
    QSizePolicy,
    QMessageBox,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QAction
from PySide6.QtCore import Signal

# 导入标签页模块
from app_qt.ipython_console_tab import IPythonConsoleTab
# 导入自定义标题栏
from app_qt.widgets.custom_titlebar import CustomTitleBar
# 导入主题管理器
from app_qt.widgets.theme_manager import get_theme_manager
# 导入设置面板
from app_qt.widgets.settings_panel import SettingsDialog, UnconfiguredDialog, check_and_show_unconfigured_dialog
from app_qt.i18n import _

# 任务管理器已迁移到插件


class QuickAssistant(QMainWindow):
    """IPythonQTBot主窗口"""

    def __init__(self):
        super().__init__()

        # 设置窗口为无边框
        self.setWindowFlags(Qt.FramelessWindowHint)
        # 允许窗口缩放
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # 窗口设置
        self.setWindowTitle("IPythonQTBot")
        self.setGeometry(100, 100, 900, 600)
        
        # 加载样式表
        self._load_stylesheets()

        # 剪贴板历史记录
        self.clipboard_history = []
        self.max_clipboard_history = 50
        
        # 窗口拖动调整大小相关
        self._drag_pos = None
        self._drag_edge = None
        self._resize_margin = 5  # 边缘检测区域宽度
        
        # 设置对话框引用
        self.settings_dialog = None
        self.unconfigured_dialog = None

        # 先加载插件（在主线程中）
        self._load_plugins_before_ui()

        # 创建界面组件
        self.create_widgets()

        # 系统托盘
        self.tray_icon = None
        self.create_tray()

    def _load_plugins_before_ui(self):
        """在创建 UI 之前加载插件（确保在主线程中）"""
        try:
            from app_qt.plugin_manager import get_plugin_manager

            # 获取插件管理器实例
            plugin_manager = get_plugin_manager()

            # 设置主窗口引用（此时 notebook 还未创建）
            plugin_manager.set_main_window(self, None, None)

            # 加载所有插件（在主线程中）
            plugin_manager.load_plugins()

            print("[MainWindow] 插件预加载完成")

        except Exception as e:
            print(f"[MainWindow] 插件预加载失败：{e}")
            import traceback

            traceback.print_exc()

    def _load_stylesheets(self):
        """加载样式表"""
        try:
            # 使用主题管理器加载样式到整个应用
            theme_manager = get_theme_manager()
            app = QApplication.instance()
            if app:
                theme_manager.apply_theme(app, "light")  # 应用到整个应用
            print(f"[MainWindow] 已应用 {theme_manager.get_current_theme()} 主题")
        except Exception as e:
            print(f"[MainWindow] 加载样式表失败：{e}")
            import traceback
            traceback.print_exc()
    
    def toggle_theme(self):
        """切换主题（在浅色和深色之间切换）"""
        from app_qt.widgets.theme_manager import get_theme_manager
        manager = get_theme_manager()
        current_theme = manager.get_current_theme()
        new_theme = "dark" if current_theme == "light" else "light"
        self.set_theme(new_theme)

    def set_theme(self, theme_name: str):
        """设置指定主题
        
        Args:
            theme_name: "light" 或 "dark"
        """
        from app_qt.widgets.theme_manager import get_theme_manager
        
        app = QApplication.instance()
        if not app:
            return
        
        manager = get_theme_manager()
        current_theme = manager.get_current_theme()
        
        # 如果主题没有变化，不执行操作
        if current_theme == theme_name:
            return
        
        # 应用新主题
        manager.apply_theme(app, theme_name)
        print(f"[MainWindow] 主题已切换为：{theme_name}")
        
        # 更新菜单选中状态
        self._update_theme_menu_check_state()
        
        # 刷新所有顶层窗口的样式
        self._refresh_styles_for_theme_change()
        
        # 同步更新 IPython 控制台主题
        if hasattr(self, 'ipython_console') and self.ipython_console:
            self.ipython_console.set_theme(theme_name)

    def _on_theme_action_triggered(self, action):
        """主题菜单项被触发时调用
        
        Args:
            action: 被触发的 QAction
        """
        if action == self.light_theme_action:
            self.set_theme("light")
        elif action == self.dark_theme_action:
            self.set_theme("dark")

    def _update_theme_menu_check_state(self):
        """更新主题菜单的选中状态"""
        from app_qt.widgets.theme_manager import get_theme_manager
        
        manager = get_theme_manager()
        current_theme = manager.get_current_theme()
        
        # 更新菜单项的选中状态（blockSignals 防止触发信号导致循环）
        self.light_theme_action.blockSignals(True)
        self.dark_theme_action.blockSignals(True)
        
        self.light_theme_action.setChecked(current_theme == "light")
        self.dark_theme_action.setChecked(current_theme == "dark")
        
        self.light_theme_action.blockSignals(False)
        self.dark_theme_action.blockSignals(False)

    def _refresh_styles_for_theme_change(self):
        """主题切换后刷新所有控件样式
        
        Qt 的样式表机制需要手动触发刷新才能看到主题变化效果。
        通过遍历所有顶层窗口并调用 unpolish/polish 来强制刷新样式。
        """
        app = QApplication.instance()
        if not app:
            return
        
        # 获取所有顶层窗口并刷新样式
        for window in app.topLevelWidgets():
            if window.isVisible():
                # 递归刷新窗口及其所有子控件
                self._recursive_refresh_style(window)
        
        print(f"[MainWindow] 样式刷新完成")

    def _recursive_refresh_style(self, widget):
        """递归刷新控件及其子控件的样式"""
        # 刷新当前控件
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
        
        # 递归刷新子控件
        for child in widget.findChildren(QWidget):
            child.style().unpolish(child)
            child.style().polish(child)
            child.update()
    
    def _create_menubar(self):
        """创建菜单栏"""
        
        # 创建菜单栏
        menubar = QMenuBar(self)
        menubar.setStyleSheet("background-color: transparent; border: none;")
        
        # 创建菜单按钮
        # self.view_menu_btn = QPushButton("🌓 查看")
        # self.view_menu_btn.setObjectName("menuButton")
        # self.view_menu_btn.setMenu(menubar)
        
        # # 设置按钮大小策略 - 根据内容调整大小
        # self.view_menu_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        # menubar_layout.addWidget(self.view_menu_btn)
        
        # 添加拉伸因子，让菜单栏不会占据整个宽度
        # menubar_layout.addStretch()
        self.menu_bar = menubar
        
        # 视图菜单
        self.view_menu = QMenu(_("👁️ View"), self)
        menubar.addMenu(self.view_menu)
        
        # 视图菜单 - 主题子菜单
        self.theme_menu = QMenu(_("🌓 Theme"), self)
        self.view_menu.addMenu(self.theme_menu)
        
        # 创建 QActionGroup 实现互斥选择
        from PySide6.QtGui import QActionGroup
        self.theme_action_group = QActionGroup(self)
        self.theme_action_group.setExclusive(True)
        
        # 浅色主题选项（带选择标记）
        self.light_theme_action = QAction(_("☀️ Light Theme"), self)
        self.light_theme_action.setCheckable(True)
        self.theme_action_group.addAction(self.light_theme_action)
        self.theme_menu.addAction(self.light_theme_action)
        
        # 深色主题选项（带选择标记）
        self.dark_theme_action = QAction(_("🌙 Dark Theme"), self)
        self.dark_theme_action.setCheckable(True)
        self.theme_action_group.addAction(self.dark_theme_action)
        self.theme_menu.addAction(self.dark_theme_action)
        
        # 连接 QActionGroup 的 triggered 信号（使用 triggered 而不是 toggled 避免重复触发）
        self.theme_action_group.triggered.connect(self._on_theme_action_triggered)
        
        # 初始化主题菜单的选中状态
        self._update_theme_menu_check_state()
        
        # 编辑菜单
        self.edit_menu = QMenu(_("✏️ Edit"), self)
        menubar.addMenu(self.edit_menu)
        
        # 编辑菜单 - 清空剪贴板
        self.clear_clipboard_action = QAction(_("🗑️ Clear Clipboard"), self)
        self.clear_clipboard_action.setToolTip(_("Clear clipboard history"))
        self.clear_clipboard_action.triggered.connect(self.clear_clipboard_history)
        self.edit_menu.addAction(self.clear_clipboard_action)
        
        # 帮助菜单
        self.help_menu = QMenu(_("ℹ️ Help"), self)
        menubar.addMenu(self.help_menu)
        
        # 帮助菜单 - 关于
        self.about_action = QAction(_("ℹ️ About"), self)
        self.about_action.setToolTip(_("About IPythonQTBot"))
        self.about_action.triggered.connect(self.show_about)
        self.help_menu.addAction(self.about_action)
                
        # 工具菜单 - 设置
        self.tools_menu = QMenu(_("🔧 Tools"), self)
        menubar.addMenu(self.tools_menu)
                
        # 工具菜单 - 设置
        self.settings_action = QAction(_("⚙️ Settings"), self)
        self.settings_action.setToolTip(_("Open system settings panel"))
        self.settings_action.setShortcut("Ctrl+,")  # Ctrl+逗号快捷键
        self.settings_action.triggered.connect(self.open_settings_panel)
        self.tools_menu.addAction(self.settings_action)
        
        # 工具菜单 - 分隔线
        self.tools_menu.addSeparator()
        
        # 工具菜单 - 重新加载插件子菜单
        self.reload_plugins_menu = QMenu(_("🔄 Reload Plugins"), self)
        self.tools_menu.addMenu(self.reload_plugins_menu)
        
        # 初始化插件重载菜单
        self._init_reload_plugins_menu()
        
        # self.
        
        # 添加到主布局
        main_layout = self.centralWidget().layout()
        if main_layout: 
            main_layout.insertWidget(1, self.menu_bar)
    
    def clear_clipboard_history(self):
        """清空剪贴板历史"""
        self.clipboard_history.clear()
        self.last_clipboard = ""
        print("[MainWindow] 剪贴板历史已清空")
        
        # 显示提示
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, _("Information"), _("Clipboard history cleared!"))
    
    def show_about(self):
        """显示关于对话框"""
        from PySide6.QtWidgets import QMessageBox
        about_text = f"""
        <h2>🛠️ IPythonQTBot</h2>
        <p><b>{_('Version:')}</b> v1.0.0</p>
        <p><b>{_('Modern UI Design')}</b></p>
        <hr/>
        <p>{_('Features:')}</p>
        <ul>
            <li>✅ {_('Custom borderless title bar')}</li>
            <li>✅ {_('Light/Dark theme switching')}</li>
            <li>✅ {_('IPython console integration')}</li>
            <li>✅ {_('MCP tools management')}</li>
            <li>✅ {_('Variable watcher')}</li>
            <li>✅ {_('Plugin system support')}</li>
        </ul>
        <hr/>
        <p style="color: #666;">{_('Modern UI design for consistent visual experience')}</p>
        """
        QMessageBox.about(self, _("About IPythonQTBot"), about_text)
    
    def update_status(self, status: str, color: str = "#4caf50"):
        """更新状态栏提示"""
        # 可以通过状态栏或其他方式显示状态
        pass

    def create_widgets(self):
        """构建主界面"""
        # 创建中央控件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        central_widget.setLayout(main_layout)

        # 添加自定义标题栏
        self.title_bar = CustomTitleBar(
            parent=self,
            title="IPythonQTBot",
            icon="🛠️"
        )
        main_layout.addWidget(self.title_bar)
        
        # 创建菜单栏 (标题栏下方)
        self._create_menubar()
        
        # 添加菜单栏到布局
        # 注意：QMainWindow 的 menuBar() 会自动添加到顶部，不需要手动添加到布局

        # 创建内容容器
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(10, 10, 10, 10)
        content_layout.setSpacing(10)
        content_widget.setLayout(content_layout)
        
        main_layout.addWidget(content_widget, 1)  # stretch=1 让内容区域占据剩余空间

        # 创建标签页控件
        self.notebook = QTabWidget()
        self.notebook.setObjectName("mainTabWidget")  # 用于样式定位
        content_layout.addWidget(self.notebook)
        
        # 第一标签页：IPython 控制台
        self.ipython_console = IPythonConsoleTab()
        self.notebook.addTab(self.ipython_console, _("🐍 IPythonBot"))
        
        # 同步控制台主题（确保与当前应用主题一致）
        from app_qt.widgets.theme_manager import get_theme_manager
        current_theme = get_theme_manager().get_current_theme()
        self.ipython_console.set_theme(current_theme)
        
        # 更新插件管理器的 notebook 引用（此时已创建）
        from app_qt.plugin_manager import get_plugin_manager

        plugin_manager = get_plugin_manager()
        plugin_manager.set_main_window(self, self.notebook, None)
        
        # 检查配置状态，如果未配置则显示提示
        self._check_initial_configuration()



        # 启动剪贴板监控
        self.clipboard_timer = QTimer()
        self.clipboard_timer.timeout.connect(self.check_clipboard)
        self.clipboard_timer.start(1000)  # 每 1 秒检查一次
        self.last_clipboard = ""

    def on_clipboard_update(self, text):
        """剪贴板更新回调"""
        pass

    def check_clipboard(self):
        """检查剪贴板变化"""
        try:
            import pyperclip

            current = pyperclip.paste()
            if current and current != self.last_clipboard:
                self.last_clipboard = current
                # 添加到文本处理标签页的历史记录
                self.text_helper.add_to_clipboard_history(current)
        except:
            pass

    def create_tray(self):
        """创建系统托盘图标"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        # 创建图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(240, 240, 240))
        painter = QPainter(pixmap)
        painter.setBrush(QColor(30, 144, 255))
        painter.drawRect(10, 10, 44, 44)
        painter.setBrush(QColor(240, 240, 240))
        painter.drawRect(15, 15, 34, 34)
        painter.end()

        icon = QIcon(pixmap)

        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))
        self.tray_icon.setToolTip("IPythonQTBot")

        # 创建托盘菜单
        tray_menu = QMenu()

        show_action = QAction(_("Show Main Window"), self)
        show_action.triggered.connect(self.show_window)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = QAction(_("Quit"), self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def tray_activated(self, reason):
        """托盘图标激活事件"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

    def show_window(self):
        """显示主窗口"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        """关闭窗口事件"""
        # 隐藏而不是退出
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

    def quit_app(self):
        """完全退出程序"""
        if self.tray_icon:
            self.tray_icon.hide()
        QApplication.quit()
    
    def _check_initial_configuration(self):
        """检查初始配置状态，如果未配置则显示提示"""
        try:
            # 使用全局 settings 实例
            from app_qt.configs import settings as global_settings
            
            if not check_and_show_unconfigured_dialog(global_settings, self):
                # 如果未配置，自动打开设置面板
                QTimer.singleShot(500, self.open_settings_panel)  # 延迟 500ms 打开
        except Exception as e:
            print(f"[MainWindow] 检查配置状态失败：{e}")
            import traceback
            traceback.print_exc()
    
    def _init_reload_plugins_menu(self):
        """初始化重新加载插件菜单"""
        # 清空现有菜单项
        self.reload_plugins_menu.clear()
        
        # 先断开之前的 aboutToShow 信号连接，避免重复连接导致卡顿
        try:
            self.reload_plugins_menu.aboutToShow.disconnect(self._update_reload_plugins_menu)
        except (TypeError, RuntimeError):
            # 没有之前的连接时会抛出异常，忽略即可
            pass
        
        # 重新加载全部插件选项
        reload_all_action = QAction(_("🔄 Reload All Plugins"), self)
        reload_all_action.setToolTip(_("Reload all enabled plugins"))
        reload_all_action.triggered.connect(self._reload_all_plugins)
        self.reload_plugins_menu.addAction(reload_all_action)
        
        self.reload_plugins_menu.addSeparator()
        
        # 获取插件管理器
        from app_qt.plugin_manager import get_plugin_manager
        plugin_manager = get_plugin_manager()
        
        # 为每个已加载的插件添加菜单项
        reloadable_plugins = plugin_manager.get_reloadable_plugins()
        
        if reloadable_plugins:
            for plugin_name in sorted(reloadable_plugins):
                # 获取插件信息
                plugin_info = plugin_manager.get_plugin_info(plugin_name)
                version = plugin_info.get("version", "unknown") if plugin_info else "unknown"
                
                action = QAction(f"🔄 {plugin_name} (v{version})", self)
                action.setToolTip(_("Reload plugin: {}").format(plugin_name))
                # 使用 lambda 捕获 plugin_name
                action.triggered.connect(lambda checked, name=plugin_name: self._reload_single_plugin(name))
                self.reload_plugins_menu.addAction(action)
        else:
            # 没有可重载的插件
            no_plugins_action = QAction(_("(No loaded plugins)"), self)
            no_plugins_action.setEnabled(False)
            self.reload_plugins_menu.addAction(no_plugins_action)
        
        # 连接菜单的 aboutToShow 信号，在菜单显示前更新列表
        self.reload_plugins_menu.aboutToShow.connect(self._update_reload_plugins_menu)
    
    def _update_reload_plugins_menu(self):
        """更新重新加载插件菜单（动态刷新插件列表）"""
        self._init_reload_plugins_menu()
    
    def _reload_single_plugin(self, plugin_name: str):
        """重新加载单个插件"""
        from app_qt.plugin_manager import get_plugin_manager
        from PySide6.QtWidgets import QMessageBox
        
        plugin_manager = get_plugin_manager()
        
        # 显示确认对话框
        reply = QMessageBox.question(
            self,
            _("Confirm Reload"),
            _("Are you sure you want to reload plugin '{}' ?\n\n").format(plugin_name)
            + _("Note: This will temporarily remove all plugin functions and reinitialize."),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            print(f"[MainWindow] 用户确认重新加载插件：{plugin_name}")
            success = plugin_manager.reload_plugin(plugin_name)
            
            if success:
                QMessageBox.information(
                    self,
                    _("Reload Successful"),
                    _("Plugin '{}' has been successfully reloaded!").format(plugin_name)
                )
            else:
                QMessageBox.critical(
                    self,
                    _("Reload Failed"),
                    _("Plugin '{}' reload failed! Please check console logs for details.").format(plugin_name)
                )
    
    def _reload_all_plugins(self):
        """重新加载所有插件"""
        from app_qt.plugin_manager import get_plugin_manager
        from PySide6.QtWidgets import QMessageBox
        
        plugin_manager = get_plugin_manager()
        reloadable_plugins = plugin_manager.get_reloadable_plugins()
        
        if not reloadable_plugins:
            QMessageBox.information(
                self,
                _("Information"),
                _("No plugins are currently loaded.")
            )
            return
        
        # 显示确认对话框
        reply = QMessageBox.question(
            self,
            _("Confirm Reload All"),
            _("Are you sure you want to reload all plugins ?\n\n")
            + f"{len(reloadable_plugins)} plugins: {', '.join(reloadable_plugins)}\n\n"
            + _("Note: This will temporarily remove all plugin functions and reinitialize."),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            print(f"[MainWindow] 用户确认重新加载所有插件")
            
            success_count = 0
            failed_plugins = []
            
            for plugin_name in reloadable_plugins:
                print(f"[MainWindow] 正在重新加载：{plugin_name}")
                if plugin_manager.reload_plugin(plugin_name):
                    success_count += 1
                else:
                    failed_plugins.append(plugin_name)
            
            # 显示结果
            if success_count == len(reloadable_plugins):
                QMessageBox.information(
                    self,
                    _("Reload Complete"),
                    _("All {} plugins have been successfully reloaded!").format(success_count)
                )
            else:
                QMessageBox.warning(
                    self,
                    _("Partial Reload Failed"),
                    _("Success: {} plugins Failed: {} plugins Failed plugins: {}").format(
                        success_count, len(failed_plugins), ', '.join(failed_plugins))
                )

    def open_settings_panel(self):
        """打开设置面板"""
        try:
            from app_qt.configs import settings as global_settings
            
            # 如果对话框已经存在，直接显示
            if self.settings_dialog and self.settings_dialog.isVisible():
                self.settings_dialog.raise_()
                self.settings_dialog.activateWindow()
                return
            
            # 创建新的设置对话框
            self.settings_dialog = SettingsDialog(global_settings, self)
            
            # 显示对话框（模态）
            self.settings_dialog.exec()
            
            print("[MainWindow] 设置对话框已关闭")
            
        except Exception as e:
            print(f"[MainWindow] 打开设置对话框失败：{e}")
            import traceback
            traceback.print_exc()
            
            # 显示错误提示
            QMessageBox.critical(
                self,
                _("Error"),
                _("Cannot open settings dialog: {}").format(str(e))
            )
    
    def _get_edge_position(self, pos):
        """获取鼠标位置对应的边缘方向"""
        rect = self.geometry()
        x, y = pos.x(), pos.y()
        
        # 检测四个角
        if x <= self._resize_margin and y <= self._resize_margin:
            return Qt.TopEdge | Qt.LeftEdge
        elif x >= rect.width() - self._resize_margin and y <= self._resize_margin:
            return Qt.TopEdge | Qt.RightEdge
        elif x <= self._resize_margin and y >= rect.height() - self._resize_margin:
            return Qt.BottomEdge | Qt.LeftEdge
        elif x >= rect.width() - self._resize_margin and y >= rect.height() - self._resize_margin:
            return Qt.BottomEdge | Qt.RightEdge
        
        # 检测四条边
        if y <= self._resize_margin:
            return Qt.TopEdge
        elif y >= rect.height() - self._resize_margin:
            return Qt.BottomEdge
        if x <= self._resize_margin:
            return Qt.LeftEdge
        elif x >= rect.width() - self._resize_margin:
            return Qt.RightEdge
        
        return None
    
    def _update_cursor(self, pos):
        """根据鼠标位置更新光标样式"""
        edge = self._get_edge_position(pos)
        
        if edge is None:
            self.setCursor(Qt.ArrowCursor)
        elif edge == (Qt.TopEdge | Qt.LeftEdge) or edge == (Qt.BottomEdge | Qt.RightEdge):
            self.setCursor(Qt.SizeFDiagCursor)
        elif edge == (Qt.TopEdge | Qt.RightEdge) or edge == (Qt.BottomEdge | Qt.LeftEdge):
            self.setCursor(Qt.SizeBDiagCursor)
        elif edge in (Qt.TopEdge, Qt.BottomEdge):
            self.setCursor(Qt.SizeVerCursor)
        elif edge in (Qt.LeftEdge, Qt.RightEdge):
            self.setCursor(Qt.SizeHorCursor)
    
    def mouseMoveEvent(self, event):
        """鼠标移动事件"""
        if event.buttons() == Qt.LeftButton and self._drag_edge:
            # 正在拖动边缘调整大小
            delta = event.globalPos() - self._drag_pos
            rect = self.geometry()
            
            if self._drag_edge & Qt.LeftEdge:
                rect.setX(rect.x() + delta.x())
                rect.setWidth(rect.width() - delta.x())
            if self._drag_edge & Qt.RightEdge:
                rect.setWidth(rect.width() + delta.x())
            if self._drag_edge & Qt.TopEdge:
                rect.setY(rect.y() + delta.y())
                rect.setHeight(rect.height() - delta.y())
            if self._drag_edge & Qt.BottomEdge:
                rect.setHeight(rect.height() + delta.y())
            
            self.setGeometry(rect)
            self._drag_pos = event.globalPos()
        # elif event.buttons() == Qt.LeftButton and self._drag_pos:
        #     # 如果event是titleBar
        #     if self.ev
        #     # 拖动窗口
        #     self.move(event.globalPos() - self._drag_pos)
        else:
            # 更新光标样式
            self._update_cursor(event.pos())
    
    def mousePressEvent(self, event):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            edge = self._get_edge_position(event.pos())
            if edge:
                # 开始拖动边缘调整大小
                self._drag_edge = edge
                self._drag_pos = event.globalPos()
            else:
                # 开始拖动窗口
                self._drag_pos = event.globalPos()
                self._drag_edge = None
    
    def mouseReleaseEvent(self, event):
        """鼠标释放事件"""
        self._drag_pos = None
        self._drag_edge = None
    
    def leaveEvent(self, event):
        """鼠标离开事件"""
        self.setCursor(Qt.ArrowCursor)

window = None  # 声明全局变量
# def main():
#     """主函数"""
#     global window
#     app = QApplication(sys.argv)
    
#     # 初始化 i18n
#     from app_qt.i18n import init_i18n
#     init_i18n()

#     # 设置应用信息
#     app.setApplicationName("IPythonQTBot")
#     app.setOrganizationName("IPythonQTBot")

#     window = QuickAssistant()
#     window.show()

#     # 初始隐藏到托盘
#     window.hide()

#     sys.exit(app.exec())


# if __name__ == "__main__":
#     main()
