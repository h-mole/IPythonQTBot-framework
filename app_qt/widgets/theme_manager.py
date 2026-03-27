"""
主题管理器 - 支持浅色/深色主题切换
"""

import os
from typing import Optional
from PySide6.QtWidgets import QApplication


class ThemeManager:
    """主题管理器 - 单例模式"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if ThemeManager._initialized:
            return
        ThemeManager._initialized = True
        
        self.current_theme = "light"  # "light" or "dark"
        # qss 目录在 app_qt/qss,不是在 widgets/qss
        self.qss_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'qss')
        self.theme_cache = {}
        
    def get_qss_path(self, theme_name: str) -> dict:
        """获取主题样式表路径"""
        paths = {
            "light": {
                "colors": os.path.join(self.qss_dir, "colors.qss"),
                "common": os.path.join(self.qss_dir, "common.qss"),
                "titlebar": os.path.join(self.qss_dir, "titlebar.qss"),
            },
            "dark": {
                "colors": os.path.join(self.qss_dir, "colors.qss"),
                "common": os.path.join(self.qss_dir, "common.qss"),
                "titlebar": os.path.join(self.qss_dir, "titlebar.qss"),
                "dark_theme": os.path.join(self.qss_dir, "dark_theme.qss"),
            }
        }
        return paths.get(theme_name, paths["light"])
    
    def clear_cache(self):
        """清除主题缓存（用于开发时更新样式）"""
        self.theme_cache.clear()
        print("[ThemeManager] 主题缓存已清除")
    
    def reload_theme(self, widget, theme_name: str = None):
        """强制重新加载主题（忽略缓存）"""
        if theme_name is None:
            theme_name = self.current_theme
        self.clear_cache()
        self.apply_theme(widget, theme_name)
        print(f"[ThemeManager] 主题已重新加载：{theme_name}")
    
    def load_theme(self, theme_name: str) -> str:
        """加载主题样式表"""
        # 总是更新 current_theme，确保状态一致（即使使用缓存）
        self.current_theme = theme_name
        
        if theme_name in self.theme_cache:
            print(f"[ThemeManager] 使用缓存的主题：{theme_name}")
            return self.theme_cache[theme_name]
        
        qss_paths = self.get_qss_path(theme_name)
        combined_style = ""
        
        print(f"[ThemeManager] 加载主题：{theme_name}")
        print(f"[ThemeManager] QSS 目录：{self.qss_dir}")
        
        # 第一步：加载公共样式表（基础样式）
        common_path = qss_paths["common"]
        print(f"[ThemeManager] 加载公共样式：{common_path}")
        if os.path.exists(common_path):
            with open(common_path, 'r', encoding='utf-8') as f:
                combined_style += f.read()
                combined_style += "\n"
            print(f"[ThemeManager] 公共样式加载成功")
        else:
            print(f"[ThemeManager] 警告：公共样式文件不存在：{common_path}")
        
        # 第二步：加载颜色/组件样式类（覆盖公共样式中的定义）
        colors_path = qss_paths.get("colors")
        if colors_path and os.path.exists(colors_path):
            print(f"[ThemeManager] 加载组件样式类：{colors_path}")
            with open(colors_path, 'r', encoding='utf-8') as f:
                combined_style += f.read()
                combined_style += "\n"
            print(f"[ThemeManager] 组件样式类加载成功，长度：{len(combined_style)}")
        else:
            print(f"[ThemeManager] 警告：组件样式文件不存在：{colors_path}")
        
        # 加载标题栏样式
        titlebar_path = qss_paths.get("titlebar")
        if titlebar_path and os.path.exists(titlebar_path):
            print(f"[ThemeManager] 加载标题栏样式：{titlebar_path}")
            with open(titlebar_path, 'r', encoding='utf-8') as f:
                titlebar_style = f.read()
                combined_style += titlebar_style
                combined_style += "\n"
            print(f"[ThemeManager] 标题栏样式加载成功，总长度：{len(combined_style)}")
        else:
            print(f"[ThemeManager] 警告：标题栏样式文件不存在：{titlebar_path}")
        
        # 如果是深色主题，追加深色样式
        if theme_name == "dark":
            dark_path = qss_paths.get("dark_theme")
            if dark_path and os.path.exists(dark_path):
                print(f"[ThemeManager] 加载深色主题样式：{dark_path}")
                with open(dark_path, 'r', encoding='utf-8') as f:
                    dark_style = f.read()
                    combined_style += dark_style
                print(f"[ThemeManager] 深色主题样式加载成功，总长度：{len(combined_style)}")
            else:
                print(f"[ThemeManager] 警告：深色主题样式文件不存在：{dark_path}")
        
        # 缓存到内存
        self.theme_cache[theme_name] = combined_style
        self.current_theme = theme_name
        
        print(f"[ThemeManager] 主题加载完成，总样式表长度：{len(combined_style)}")
        
        return combined_style
    
    def apply_theme(self, widget, theme_name: str = "light"):
        """应用主题到指定控件"""
        style_sheet = self.load_theme(theme_name)
        # 如果是 QApplication，直接设置样式表
        if isinstance(widget, QApplication):
            widget.setStyleSheet(style_sheet)
        else:
            widget.setStyleSheet(style_sheet)
    
    def toggle_theme(self, widget):
        """切换主题"""
        new_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(widget, new_theme)
        return new_theme
    
    def get_current_theme(self) -> str:
        """获取当前主题"""
        return self.current_theme
    
    def is_dark_theme(self) -> bool:
        """是否为深色主题"""
        return self.current_theme == "dark"
    
    def is_light_theme(self) -> bool:
        """是否为浅色主题"""
        return self.current_theme == "light"


# 全局主题管理器实例
_global_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """获取全局主题管理器实例"""
    global _global_theme_manager
    if _global_theme_manager is None:
        _global_theme_manager = ThemeManager()
    return _global_theme_manager


def apply_theme_to_widget(widget, theme_name: str = "light"):
    """便捷函数：应用主题到控件"""
    manager = get_theme_manager()
    manager.apply_theme(widget, theme_name)


def toggle_theme(widget):
    """便捷函数：切换主题"""
    manager = get_theme_manager()
    return manager.toggle_theme(widget)
