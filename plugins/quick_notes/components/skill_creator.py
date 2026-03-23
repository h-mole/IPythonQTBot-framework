"""
快速笔记插件 - 技能创建工具
支持创建符合 agentskills-core 规范的技能文件夹
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QMessageBox,
    QGroupBox, QFileDialog
)
from PySide6.QtCore import Qt


class CreateSkillDialog(QDialog):
    """创建技能对话框"""
    
    def __init__(self, parent=None, skills_dir=None):
        super().__init__(parent)
        self.skills_dir = skills_dir
        self.setWindowTitle("创建新技能")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 技能基本信息
        info_group = QGroupBox("技能基本信息")
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)
        
        # 技能名称
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("技能名称:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如：pdf-processing")
        name_row.addWidget(self.name_input)
        info_layout.addLayout(name_row)
        
        # 技能描述
        desc_label = QLabel("技能描述:")
        info_layout.addWidget(desc_label)
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("描述技能的用途和使用时机...")
        self.desc_input.setMaximumHeight(100)
        info_layout.addWidget(self.desc_input)
        
        layout.addWidget(info_group)
        
        # SKILL.md 内容
        content_group = QGroupBox("SKILL.md 内容")
        content_layout = QVBoxLayout()
        content_group.setLayout(content_layout)
        
        content_label = QLabel("技能指令内容 (Markdown 格式):")
        content_layout.addWidget(content_label)
        
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("""# 技能名称

## 何时使用此技能
描述在什么情况下应该使用这个技能...

## 如何执行任务
1. 第一步...
2. 第二步...
3. ...

## 示例
提供一些使用示例...
""")
        content_layout.addWidget(self.content_input)
        
        layout.addWidget(content_group)
        
        # 按钮
        button_row = QHBoxLayout()
        button_row.addStretch()
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_btn)
        
        self.create_btn = QPushButton("创建")
        self.create_btn.clicked.connect(self.on_create)
        self.create_btn.setDefault(True)
        button_row.addWidget(self.create_btn)
        
        layout.addLayout(button_row)
    
    def on_create(self):
        """创建按钮点击事件"""
        skill_name = self.name_input.text().strip()
        skill_desc = self.desc_input.toPlainText().strip()
        skill_content = self.content_input.toPlainText().strip()
        
        # 验证输入
        if not skill_name:
            QMessageBox.warning(self, "警告", "请输入技能名称！")
            return
        
        if not skill_desc:
            QMessageBox.warning(self, "警告", "请输入技能描述！")
            return
        
        if not skill_content:
            QMessageBox.warning(self, "警告", "请输入技能指令内容！")
            return
        
        # 检查技能名称格式（kebab-case）
        import re
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', skill_name):
            QMessageBox.warning(
                self, "警告", 
                "技能名称必须是小写字母、数字和连字符，且不能以连字符开头或结尾！"
            )
            return
        
        # 确定技能目录
        if not self.skills_dir:
            QMessageBox.critical(self, "错误", "未指定 skills 目录路径！")
            return
        
        skill_folder_path = os.path.join(self.skills_dir, skill_name)
        
        # 检查是否已存在
        if os.path.exists(skill_folder_path):
            QMessageBox.warning(
                self, "警告", 
                f"技能文件夹已存在：{skill_folder_path}"
            )
            return
        
        try:
            # 创建技能文件夹
            os.makedirs(skill_folder_path, exist_ok=True)
            
            # 创建 SKILL.md 文件
            skill_md_content = f"""---
name: {skill_name}
description: {skill_desc}
---

{skill_content}
"""
            
            skill_md_path = os.path.join(skill_folder_path, "SKILL.md")
            with open(skill_md_path, "w", encoding="utf-8") as f:
                f.write(skill_md_content)
            
            QMessageBox.information(
                self, "成功", 
                f"技能创建成功！\n路径：{skill_folder_path}"
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "错误", 
                f"创建技能失败：{str(e)}"
            )
    
    def get_skill_info(self):
        """获取技能信息"""
        return {
            'name': self.name_input.text().strip(),
            'description': self.desc_input.toPlainText().strip(),
            'content': self.content_input.toPlainText().strip()
        }
