"""
Pandoc Utils Plugin - 提供 Pandoc 文档转换功能
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QFrame,
    QGroupBox,
    QMenuBar,
    QFileDialog,
    QMessageBox,
    QSplitter,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QAction, QKeySequence
import os
import tempfile
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app_qt.plugin_manager import PluginManager


class PandocUtilsWidget(QWidget):
    """Pandoc 文档转换功能组件（无 UI）"""

    def __init__(self, plugin_manager=None):
        super().__init__()
        self.plugin_manager: "PluginManager" = plugin_manager
        # 先复制内置模板，再初始化路径和加载模板列表
        self._copy_builtin_templates()
        self.template_path = None
        self.templates_dir = self._get_templates_dir()
        self.available_templates = self._load_available_templates()

    def _get_templates_dir(self):
        """获取模板目录路径"""
        # 数据文件夹/pandoc_utils/templates/docx
        base_dir = os.path.join(
            os.path.expanduser("~"), ".myhelper", "pandoc_utils", "templates", "docx"
        )
        # 确保目录存在
        os.makedirs(base_dir, exist_ok=True)
        return base_dir

    def _get_builtin_templates_dir(self):
        """获取内置模板目录路径（相对于 main.py）"""
        # 获取 main.py 所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # builtin_templates 目录
        builtin_dir = os.path.join(current_dir, "builtin_templates")
        return builtin_dir

    def _copy_builtin_templates(self):
        """
        复制内置模板到数据目录
        如果数据目录已有同名文件则跳过
        """
        import shutil

        builtin_dir = self._get_builtin_templates_dir()
        data_dir = os.path.join(
            os.path.expanduser("~"), ".myhelper", "pandoc_utils", "templates", "docx"
        )

        # 确保数据目录存在
        os.makedirs(data_dir, exist_ok=True)

        # 检查内置模板目录是否存在
        if not os.path.exists(builtin_dir):
            print(f"[PandocUtils] 内置模板目录不存在：{builtin_dir}")
            return

        # 遍历内置模板目录
        copied_count = 0
        skipped_count = 0
        error_count = 0

        for filename in os.listdir(builtin_dir):
            if filename.endswith(".docx"):
                src_path = os.path.join(builtin_dir, filename)
                dst_path = os.path.join(data_dir, filename)

                # 如果目标文件已存在，跳过
                if os.path.exists(dst_path):
                    print(f"[PandocUtils] 跳过已存在的模板：{filename}")
                    skipped_count += 1
                    continue

                try:
                    # 复制文件
                    shutil.copy2(src_path, dst_path)
                    print(f"[PandocUtils] 已复制内置模板：{filename}")
                    copied_count += 1
                except PermissionError as e:
                    print(f"[PandocUtils] 权限错误，无法复制 {filename}: {e}")
                    import traceback

                    traceback.print_exc()
                    error_count += 1
                except Exception as e:
                    print(f"[PandocUtils] 复制模板 {filename} 失败：{e}")
                    import traceback

                    traceback.print_exc()
                    error_count += 1

        # 打印统计信息
        total = copied_count + skipped_count + error_count
        if total > 0:
            print(
                f"[PandocUtils] 模板复制完成：共 {total} 个文件，成功复制 {copied_count} 个，跳过 {skipped_count} 个，错误 {error_count} 个"
            )

    def _load_available_templates(self):
        """加载可用的模板列表"""
        templates = {}
        if os.path.exists(self.templates_dir):
            for filename in os.listdir(self.templates_dir):
                if filename.endswith(".docx"):
                    template_name = filename[:-5]  # 去掉 .docx 后缀
                    template_path = os.path.join(self.templates_dir, filename)
                    templates[template_name] = template_path
        return templates

    def get_current_template_path(self):
        """获取当前选中的模板路径"""
        return self.template_path

    def set_template(self, template_name):
        """
        设置使用的模板

        Args:
            template_name: 模板名称（不带 .docx 后缀）

        Returns:
            bool: 是否设置成功
        """
        if template_name is None:
            self.template_path = None
            print("[PandocUtils] 已清除模板（使用默认样式）")
            return True

        if template_name in self.available_templates:
            self.template_path = self.available_templates[template_name]
            print(f"[PandocUtils] 已选择模板：{template_name}")
            return True
        else:
            print(f"[PandocUtils] 模板不存在：{template_name}")
            return False

    def list_templates(self):
        """
        列出所有可用模板

        Returns:
            list: 模板名称列表
        """
        return list(self.available_templates.keys())

    # ==================== API 接口方法（暴露给其他插件调用） ====================

    def convert_markdown_to_docx_api(
        self, markdown_text, template_path=None, output_dir=None
    ):
        """
        API: 将 Markdown 转换为 DOCX

        Args:
            markdown_text: Markdown 文本内容
            template_path: Word 模板路径（可选）
            output_dir: 输出目录（可选）

        Returns:
            dict: 包含成功状态和输出路径/错误信息
        """
        if not markdown_text or not markdown_text.strip():
            return {"success": False, "error": "输入文本为空"}

        try:
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            temp_md = os.path.join(temp_dir, "temp_document.md")

            # 确定输出目录
            if output_dir:
                out_dir = output_dir
            else:
                out_dir = os.path.join(temp_dir, "docx_output")

            # 确保输出目录存在
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

            # 写入 markdown 文件
            with open(temp_md, "w", encoding="utf-8") as f:
                f.write(markdown_text)

            # 构建 pandoc 命令
            cmd = ["pandoc", temp_md, "-o", os.path.join(out_dir, "document.docx")]

            # 如果指定了模板，添加模板参数
            if template_path and os.path.exists(template_path):
                cmd.extend(["--reference-doc=" + template_path])

            # 提取媒体文件
            cmd.append("--extract-media=.")

            # 执行转换
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            output_path = os.path.join(out_dir, "document.docx")

            return {
                "success": True,
                "output_path": output_path,
                "message": f"转换成功：{output_path}",
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"Pandoc 错误：{e.stderr if e.stderr else str(e)}"
            return {"success": False, "error": error_msg}
        except FileNotFoundError:
            return {
                "success": False,
                "error": "找不到 pandoc 程序，请确保已安装并添加到 PATH",
            }
        except Exception as e:
            return {"success": False, "error": f"转换失败：{str(e)}"}

    def convert_markdown_to_html_api(self, markdown_text, output_dir=None):
        """
        API: 将 Markdown 转换为 HTML

        Args:
            markdown_text: Markdown 文本内容
            output_dir: 输出目录（可选）

        Returns:
            dict: 包含成功状态和输出路径/错误信息
        """
        if not markdown_text or not markdown_text.strip():
            return {"success": False, "error": "输入文本为空"}

        try:
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            temp_md = os.path.join(temp_dir, "temp_document.md")

            # 确定输出目录
            if output_dir:
                out_dir = output_dir
            else:
                out_dir = os.path.join(temp_dir, "html_output")

            # 确保输出目录存在
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

            # 写入 markdown 文件
            with open(temp_md, "w", encoding="utf-8") as f:
                f.write(markdown_text)

            # 构建 pandoc 命令
            cmd = [
                "pandoc",
                temp_md,
                "-t",
                "html",
                "-o",
                os.path.join(out_dir, "document.html"),
                "--standalone",
            ]

            # 执行转换
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            output_path = os.path.join(out_dir, "document.html")

            return {
                "success": True,
                "output_path": output_path,
                "message": f"转换成功：{output_path}",
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"Pandoc 错误：{e.stderr if e.stderr else str(e)}"
            return {"success": False, "error": error_msg}
        except FileNotFoundError:
            return {
                "success": False,
                "error": "找不到 pandoc 程序，请确保已安装并添加到 PATH",
            }
        except Exception as e:
            return {"success": False, "error": f"转换失败：{str(e)}"}

    def convert_markdown_to_latex_api(self, markdown_text, output_dir=None):
        """
        API: 将 Markdown 转换为 LaTeX

        Args:
            markdown_text: Markdown 文本内容
            output_dir: 输出目录（可选）

        Returns:
            dict: 包含成功状态和输出路径/错误信息
        """
        if not markdown_text or not markdown_text.strip():
            return {"success": False, "error": "输入文本为空"}

        try:
            # 创建临时文件
            temp_dir = tempfile.gettempdir()
            temp_md = os.path.join(temp_dir, "temp_document.md")

            # 确定输出目录
            if output_dir:
                out_dir = output_dir
            else:
                out_dir = os.path.join(temp_dir, "latex_output")

            # 确保输出目录存在
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

            # 写入 markdown 文件
            with open(temp_md, "w", encoding="utf-8") as f:
                f.write(markdown_text)

            # 构建 pandoc 命令
            cmd = [
                "pandoc",
                temp_md,
                "-t",
                "latex",
                "-o",
                os.path.join(out_dir, "document.tex"),
                "--standalone",
            ]

            # 执行转换
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)

            output_path = os.path.join(out_dir, "document.tex")

            return {
                "success": True,
                "output_path": output_path,
                "message": f"转换成功：{output_path}",
            }

        except subprocess.CalledProcessError as e:
            error_msg = f"Pandoc 错误：{e.stderr if e.stderr else str(e)}"
            return {"success": False, "error": error_msg}
        except FileNotFoundError:
            return {
                "success": False,
                "error": "找不到 pandoc 程序，请确保已安装并添加到 PATH",
            }
        except Exception as e:
            return {"success": False, "error": f"转换失败：{str(e)}"}

    def convert_docx_to_markdown_api(self, docx_path):
        """
        API: 将 DOCX 转换为 Markdown

        Args:
            docx_path: DOCX 文件路径

        Returns:
            dict: 包含成功状态和 markdown 内容/错误信息
        """
        if not os.path.exists(docx_path):
            return {"success": False, "error": f"文件不存在：{docx_path}"}

        try:
            # 构建 pandoc 命令
            cmd = ["pandoc", docx_path, "-t", "markdown", "-o", "-"]

            # 执行转换，指定 encoding='utf-8'
            result = subprocess.run(
                cmd, check=True, capture_output=True, text=True, encoding="utf-8"
            )

            return {"success": True, "markdown": result.stdout, "message": "转换成功"}

        except subprocess.CalledProcessError as e:
            error_msg = f"Pandoc 错误：{e.stderr if e.stderr else str(e)}"
            return {"success": False, "error": error_msg}
        except UnicodeDecodeError:
            # 如果 UTF-8 失败，尝试系统默认编码
            try:
                result = subprocess.run(cmd, check=True, capture_output=True)
                return {
                    "success": True,
                    "markdown": result.stdout.decode("gbk", errors="ignore"),
                    "message": "转换成功",
                }
            except Exception as e2:
                return {"success": False, "error": f"解码失败：{str(e2)}"}
        except FileNotFoundError:
            return {
                "success": False,
                "error": "找不到 pandoc 程序，请确保已安装并添加到 PATH",
            }
        except Exception as e:
            return {"success": False, "error": f"转换失败：{str(e)}"}

    def is_pandoc_available_api(self):
        """
        API: 检查 Pandoc 是否可用

        Returns:
            bool: Pandoc 是否可用
        """
        try:
            result = subprocess.run(
                ["pandoc", "--version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def get_pandoc_version_api(self):
        """
        API: 获取 Pandoc 版本号

        Returns:
            str: Pandoc 版本号，如果不可用则返回 None
        """
        try:
            result = subprocess.run(
                ["pandoc", "--version"], capture_output=True, timeout=5, text=True
            )
            if result.returncode == 0:
                # 解析版本号
                lines = result.stdout.split("\n")
                if lines:
                    version_line = lines[0]
                    parts = version_line.split()
                    if len(parts) >= 2:
                        return parts[-1]
            return None
        except:
            return None

    def create_pandoc_menu(self):
        """
        创建 Pandoc 菜单

        Returns:
            bool: 是否创建成功
        """
        try:
            from PySide6.QtWidgets import (
                QMenu,
                QInputDialog,
                QListWidget,
                QDialog,
                QDialogButtonBox,
                QVBoxLayout,
            )
            from PySide6.QtGui import QAction, QKeySequence

            # 创建 Pandoc 菜单
            pandoc_menu = QMenu("&Pandoc")

            # 添加模板选择子菜单
            def create_template_submenu():
                """创建模板选择子菜单的处理函数"""
                templates = self.list_templates()
                current_template = self.get_current_template_path()
                current_name = None

                # 找出当前选中的模板名称
                if current_template:
                    for name, path in self.available_templates.items():
                        if path == current_template:
                            current_name = name
                            break

                # 创建对话框
                dialog = QDialog()
                dialog.setWindowTitle("选择Docx模板")
                layout = QVBoxLayout()

                # 创建列表
                template_list = QListWidget()
                template_list.addItems(templates if templates else ["（无可用模板）"])
                layout.addWidget(template_list)

                # 添加按钮
                buttons = QDialogButtonBox(
                    QDialogButtonBox.Ok | QDialogButtonBox.Cancel
                )
                buttons.accepted.connect(dialog.accept)
                buttons.rejected.connect(dialog.reject)
                layout.addWidget(buttons)

                dialog.setLayout(layout)

                # 如果当前有选中，设置为默认
                if current_name and current_name in templates:
                    template_list.setCurrentRow(templates.index(current_name))

                if dialog.exec() == QDialog.Accepted:
                    selected = template_list.currentItem()
                    if selected:
                        template_name = selected.text()
                        if template_name != "（无可用模板）":
                            self.set_template(template_name)
                            print(f"[PandocUtils] 已选择模板：{template_name}")
                        else:
                            self.set_template(None)

            # 添加菜单项
            template_action = QAction("选择模板...", pandoc_menu)
            template_action.setShortcut(QKeySequence("Ctrl+Alt+T"))
            template_action.triggered.connect(lambda: create_template_submenu())
            pandoc_menu.addAction(template_action)

            convert_to_docx_action = QAction("转换选中文本为 DOCX", pandoc_menu)
            convert_to_docx_action.setShortcut(QKeySequence("Ctrl+Alt+M"))
            convert_to_docx_action.triggered.connect(
                self.convert_markdown_to_docx
            )
            pandoc_menu.addAction(convert_to_docx_action)

            # 添加转为html的菜单项
            convert_to_html_action = QAction("转换选中文本为 HTML", pandoc_menu)
            convert_to_html_action.setShortcut(QKeySequence("Ctrl+Alt+H"))
            convert_to_html_action.triggered.connect(self.convert_markdown_to_html)
            pandoc_menu.addAction(convert_to_html_action)
            
            # 添加转为latex的菜单项
            convert_to_latex_action = QAction("转换选中文本为 LaTeX", pandoc_menu)
            convert_to_latex_action.setShortcut(QKeySequence("Ctrl+Alt+L"))
            convert_to_latex_action.triggered.connect(self.convert_markdown_to_latex)
            pandoc_menu.addAction(convert_to_latex_action)

            # 使用 text_helper 的 add_menu_to_menubar API 将菜单添加到菜单栏
            menu_added = False
            if self.plugin_manager and self.plugin_manager.is_plugin_loaded(
                "text_helper"
            ):
                add_menu = self.plugin_manager.get_method(
                    "text_helper.add_menu_to_menubar"
                )

                if add_menu:
                    success = add_menu(pandoc_menu)
                    if success:
                        print("[PandocUtils] 已成功创建 Pandoc 菜单")
                        menu_added = True
                    else:
                        print("[PandocUtils] 创建菜单失败（可能在无 UI 环境下运行）")
                else:
                    print(
                        "[PandocUtils] 警告：找不到 text_helper.add_menu_to_menubar 方法"
                    )
            else:
                print("[PandocUtils] 警告：text_helper 未加载，无法创建菜单")

            return menu_added

        except Exception as e:
            print(f"[PandocUtils] 创建菜单失败：{e}")
            import traceback

            traceback.print_exc()
            return False

    def convert_markdown_to_docx(self):
        """将 Markdown 转换为 Word 文档"""
        from PySide6.QtWidgets import QMessageBox

        get_text = self.plugin_manager.get_method("text_helper.get_text")
        print(get_text)  # 打印 get_text 方法
        content = get_text()
        if not content:
            return {"success": False, "error": "输入文本为空"}

        try:
            # 使用 API 方法进行转换
            result = self.convert_markdown_to_docx_api(
                content, template_path=self.template_path
            )

            if result["success"]:
                # 自动打开输出文件
                try:
                    os.startfile(result["output_path"])
                except:
                    pass
            else:
                # 显示错误信息
                error_msg = f"❌ 转换失败:\n\n{result['error']}"
                print(error_msg)
                QMessageBox.critical(self, "转换失败", result["error"])

        except Exception as e:
            error_msg = f"发生错误：{str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            return {"success": False, "error": error_msg}

        return result

    def convert_markdown_to_html(self):
        """将 Markdown 转换为 HTML"""
        from PySide6.QtWidgets import QMessageBox

        get_text = self.plugin_manager.get_method("text_helper.get_text")
        content = get_text()
        if not content:
            return {"success": False, "error": "输入文本为空"}

        try:
            # 使用 API 方法进行转换
            result = self.convert_markdown_to_html_api(content)

            if result["success"]:
                # 自动打开输出文件
                try:
                    os.startfile(result["output_path"])
                except:
                    pass
            else:
                # 显示错误信息
                error_msg = f"❌ 转换失败:\n\n{result['error']}"
                print(error_msg)
                QMessageBox.critical(self, "转换失败", result["error"])

        except Exception as e:
            error_msg = f"发生错误：{str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            return {"success": False, "error": error_msg}

        return result

    def convert_markdown_to_latex(self):
        """将 Markdown 转换为 LaTeX"""
        from PySide6.QtWidgets import QMessageBox

        get_text = self.plugin_manager.get_method("text_helper.get_text")
        content = get_text()
        if not content:
            return {"success": False, "error": "输入文本为空"}

        try:
            # 使用 API 方法进行转换
            result = self.convert_markdown_to_latex_api(content)

            if result["success"]:
                # 自动打开输出文件
                try:
                    os.startfile(result["output_path"])
                except:
                    pass
            else:
                # 显示错误信息
                error_msg = f"❌ 转换失败:\n\n{result['error']}"
                print(error_msg)
                QMessageBox.critical(self, "转换失败", result["error"])

        except Exception as e:
            error_msg = f"发生错误：{str(e)}"
            print(error_msg)
            QMessageBox.critical(self, "错误", error_msg)
            return {"success": False, "error": error_msg}

        return result

    def convert_docx_to_markdown_ui(self):
        """UI: 将 DOCX 转换为 Markdown"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择 DOCX 文件", "", "Word 文档 (*.docx);;所有文件 (*)"
        )

        if file_path:
            try:
                result = self.convert_docx_to_markdown_api(file_path)

                if result["success"]:
                    print(f"[PandocUtils] DOCX 已成功转换为 Markdown")
                    print(
                        result["markdown"][:200] + "..."
                        if len(result["markdown"]) > 200
                        else result["markdown"]
                    )
                else:
                    print(f"[PandocUtils] 转换失败：{result['error']}")
                    QMessageBox.critical(self, "转换失败", result["error"])

            except Exception as e:
                error_msg = f"发生错误：{str(e)}"
                print(error_msg)
                QMessageBox.critical(self, "错误", error_msg)


# ==================== 插件入口函数 ====================


def load_plugin(plugin_manager):
    """
    插件加载入口函数

    Args:
        plugin_manager: 插件管理器实例

    Returns:
        dict: 包含插件组件的字典
    """
    print("[PandocUtils] 正在加载 Pandoc 工具插件...")

    # 创建 widget 实例（无 UI），传入 plugin_manager
    pandoc_widget = PandocUtilsWidget(plugin_manager=plugin_manager)

    # 注册暴露的方法到全局域
    plugin_manager.register_method(
        "pandoc_utils",
        "convert_markdown_to_docx",
        pandoc_widget.convert_markdown_to_docx_api,
    )
    plugin_manager.register_method(
        "pandoc_utils",
        "convert_markdown_to_html",
        pandoc_widget.convert_markdown_to_html_api,
    )
    plugin_manager.register_method(
        "pandoc_utils",
        "convert_markdown_to_latex",
        pandoc_widget.convert_markdown_to_latex_api,
    )
    plugin_manager.register_method(
        "pandoc_utils",
        "convert_docx_to_markdown",
        pandoc_widget.convert_docx_to_markdown_api,
    )
    plugin_manager.register_method(
        "pandoc_utils", "is_pandoc_available", pandoc_widget.is_pandoc_available_api
    )
    plugin_manager.register_method(
        "pandoc_utils", "get_pandoc_version", pandoc_widget.get_pandoc_version_api
    )
    plugin_manager.register_method(
        "pandoc_utils", "list_templates", pandoc_widget.list_templates
    )
    plugin_manager.register_method(
        "pandoc_utils", "set_template", pandoc_widget.set_template
    )
    plugin_manager.register_method(
        "pandoc_utils", "get_template_path", pandoc_widget.get_current_template_path
    )

    # 创建 Pandoc 菜单
    menu_created = pandoc_widget.create_pandoc_menu()

    print("[PandocUtils] Pandoc 工具插件加载完成")
    return {
        "widget": pandoc_widget,
        "namespace": "pandoc_utils",
        "menu_created": menu_created,
    }


def unload_plugin(plugin_manager):
    """
    插件卸载回调

    Args:
        plugin_manager: 插件管理器实例
    """
    print("[PandocUtils] 正在卸载 Pandoc 工具插件...")
    # 清理资源、保存状态等
    print("[PandocUtils] Pandoc 工具插件卸载完成")
