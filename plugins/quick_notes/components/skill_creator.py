"""
快速笔记插件 - 技能创建工具
支持创建符合 agentskills-core 规范的技能文件夹
"""

import os
from pathlib import Path
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QTextEdit, QPushButton, QMessageBox,
    QGroupBox, QFileDialog
)
from PySide6.QtCore import Qt

# Initialize plugin i18n
from app_qt.plugin_i18n import PluginI18n
_i18n = PluginI18n("quick_notes", Path(__file__).parent.parent)
_ = _i18n.gettext


class CreateSkillDialog(QDialog):
    """创建技能对话框"""
    
    def __init__(self, parent=None, skills_dir=None):
        super().__init__(parent)
        self.skills_dir = skills_dir
        self.setWindowTitle(_("Create New Skill"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 技能基本信息
        info_group = QGroupBox(_("Skill Basic Info"))
        info_layout = QVBoxLayout()
        info_group.setLayout(info_layout)
        
        # 技能名称
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel(_("Skill Name:") + ":"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(_("e.g., pdf-processing"))
        name_row.addWidget(self.name_input)
        info_layout.addLayout(name_row)
        
        # 技能描述
        desc_label = QLabel(_("Skill Description:") + ":")
        info_layout.addWidget(desc_label)
        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText(_("Describe skill purpose and usage..."))
        self.desc_input.setMaximumHeight(100)
        info_layout.addWidget(self.desc_input)
        
        layout.addWidget(info_group)
        
        # SKILL.md 内容
        content_group = QGroupBox(_("SKILL.md Content"))
        content_layout = QVBoxLayout()
        content_group.setLayout(content_layout)
        
        content_label = QLabel(_("Skill Instructions (Markdown format):") + ":")
        content_layout.addWidget(content_label)
        
        self.content_input = QTextEdit()
        self.content_input.setPlaceholderText("""# Skill Name

## When to use this skill
Describe when to use this skill...

## How to execute tasks
1. First step...
2. Second step...
3. ...

## Examples
Provide usage examples...
""")
        content_layout.addWidget(self.content_input)
        
        layout.addWidget(content_group)
        
        # 按钮
        button_row = QHBoxLayout()
        button_row.addStretch()
        
        self.cancel_btn = QPushButton(_("Cancel"))
        self.cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_btn)
        
        self.create_btn = QPushButton(_("Create"))
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
            QMessageBox.warning(self, _("Warning"), _("Please enter skill name!"))
            return
        
        if not skill_desc:
            QMessageBox.warning(self, _("Warning"), _("Please enter skill description!"))
            return
        
        if not skill_content:
            QMessageBox.warning(self, _("Warning"), _("Please enter skill instructions!"))
            return
        
        # 检查技能名称格式（kebab-case）
        import re
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', skill_name):
            QMessageBox.warning(
                self, _("Warning"), 
                _("Skill name must be lowercase letters, numbers and hyphens, cannot start or end with hyphen!")
            )
            return
        
        # 确定技能目录
        if not self.skills_dir:
            QMessageBox.critical(self, _("Error"), _("Skills directory path not specified!"))
            return
        
        skill_folder_path = os.path.join(self.skills_dir, skill_name)
        
        # 检查是否已存在
        if os.path.exists(skill_folder_path):
            QMessageBox.warning(
                self, _("Warning"), 
                _("Skill folder already exists: {}").format(skill_folder_path)
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
                self, _("Success"), 
                _("Skill created successfully!\nPath: {}").format(skill_folder_path)
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, _("Error"), 
                _("Failed to create skill: {}") + str(e)
            )
    
    def get_skill_info(self):
        """获取技能信息"""
        return {
            'name': self.name_input.text().strip(),
            'description': self.desc_input.toPlainText().strip(),
            'content': self.content_input.toPlainText().strip()
        }
