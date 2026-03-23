"""
测试技能加载 MCP 接口

测试两个主要功能:
1. get_all_skills_summary - 获取所有技能概要信息
2. get_skill_detail - 获取单个技能详细信息
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

def test_skill_format():
    """测试 skill_format 模块"""
    print("=" * 60)
    print("测试 1: SkillFormat 基础功能")
    print("=" * 60)
    
    from plugins.quick_notes.utils.skill_format import SkillFormat
    
    # 测试示例技能
    example_skill_path = os.path.join(
        os.path.dirname(__file__),
        "example_skill_template.md"
    )
    
    if os.path.exists(example_skill_path):
        with open(example_skill_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 测试 YAML frontmatter 解析
        metadata = SkillFormat.parse_yaml_frontmatter(content)
        print(f"\n✓ 成功解析 YAML frontmatter")
        print(f"  name: {metadata.get('name', 'N/A')}")
        print(f"  description: {metadata.get('description', 'N/A')[:50]}...")
        
        # 测试 Markdown 正文提取
        body = SkillFormat.get_skill_markdown_body(content)
        print(f"\n✓ 成功提取 Markdown 正文")
        print(f"  正文字符数：{len(body)}")
    else:
        print(f"\n⚠ 示例技能文件不存在：{example_skill_path}")


def test_scan_skills():
    """测试扫描技能目录"""
    print("\n" + "=" * 60)
    print("测试 2: 扫描技能目录")
    print("=" * 60)
    
    from app_qt.configs import PLUGIN_DATA_DIR
    from plugins.quick_notes.utils.skill_format import SkillFormat
    
    skills_dir = os.path.join(PLUGIN_DATA_DIR, "quick_notes", "skills")
    print(f"\n技能目录：{skills_dir}")
    
    if not os.path.exists(skills_dir):
        print(f"⚠ 技能目录不存在，将创建示例技能")
        os.makedirs(skills_dir, exist_ok=True)
        
        # 创建示例技能
        create_sample_skill(skills_dir)
    
    # 扫描技能
    skills = SkillFormat.scan_skills_directory(skills_dir)
    print(f"\n✓ 找到 {len(skills)} 个技能:")
    
    for i, skill in enumerate(skills, 1):
        print(f"\n  [{i}] {skill['name']}")
        print(f"      描述：{skill['description'][:60]}...")
        print(f"      路径：{skill['path']}")
        print(f"      版本：{skill.get('version', 'N/A')}")
        print(f"      作者：{skill.get('author', 'N/A')}")
        print(f"      资源：scripts={skill['has_scripts']}, references={skill['has_references']}, assets={skill['has_assets']}")


def create_sample_skill(skills_dir):
    """创建示例技能用于测试"""
    sample_skill_dir = os.path.join(skills_dir, "test-skill")
    os.makedirs(sample_skill_dir, exist_ok=True)
    
    skill_md = """---
name: test-skill
description: 这是一个测试技能，用于验证技能加载功能。
  当需要测试技能加载和 MCP 接口时使用。
license: MIT
metadata:
  author: test-user
  version: "1.0"
  created: 2026-03-23
---

# 测试技能

## 何时使用此技能

- 测试技能加载功能
- 验证 MCP 接口是否正常工作
- 演示技能格式

## 技能结构

这个技能包含:
- SKILL.md 文件 (本文件)
- scripts/ 目录 (包含测试脚本)
- references/ 目录 (包含参考资料)

## 示例

### 示例 1: 基本用法

这是一个示例代码块:

```python
def hello_world():
    print("Hello from test skill!")
```

## 注意事项

- 这只是一个测试技能
- 实际使用时请替换为真实的技能内容
"""
    
    with open(os.path.join(sample_skill_dir, "SKILL.md"), 'w', encoding='utf-8') as f:
        f.write(skill_md)
    
    # 创建 scripts 目录
    scripts_dir = os.path.join(sample_skill_dir, "scripts")
    os.makedirs(scripts_dir, exist_ok=True)
    with open(os.path.join(scripts_dir, "test.py"), 'w', encoding='utf-8') as f:
        f.write("# Test script\nprint('Hello')\n")
    
    # 创建 references 目录
    references_dir = os.path.join(sample_skill_dir, "references")
    os.makedirs(references_dir, exist_ok=True)
    with open(os.path.join(references_dir, "README.md"), 'w', encoding='utf-8') as f:
        f.write("# References\n\nThis is a reference document.\n")
    
    print(f"✓ 已创建示例技能：{sample_skill_dir}")


def test_mcp_interface():
    """测试 MCP 接口"""
    print("\n" + "=" * 60)
    print("测试 3: MCP 接口调用")
    print("=" * 60)
    
    try:
        from app_qt.configs import PLUGIN_DATA_DIR
        from plugins.quick_notes.main import QuickNotesTab
        from PySide6.QtWidgets import QApplication
        
        # 创建 QApplication (如果还没有)
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        
        # 创建 QuickNotesTab 实例进行测试
        notes_tab = QuickNotesTab()
        
        # 测试获取所有技能概要
        print("\n1. 测试 get_all_skills_summary 接口:")
        print("-" * 60)
        
        skills = notes_tab.get_all_skills_summary_api()
        print(f"✓ 成功调用 get_all_skills_summary")
        print(f"  返回技能数量：{len(skills)}")
        
        if skills:
            print(f"\n  技能列表:")
            for skill in skills:
                print(f"    - {skill['name']}: {skill['description'][:50]}...")
                print(f"      路径：{skill['path']}")
        
        # 测试获取技能详情
        print("\n2. 测试 get_skill_detail 接口:")
        print("-" * 60)
        
        if skills and len(skills) > 0:
            test_skill_name = skills[0]['name']
            print(f"  测试技能：{test_skill_name}")
            
            detail = notes_tab.get_skill_detail_api(test_skill_name)
            print(f"✓ 成功调用 get_skill_detail")
            print(f"  技能名称：{detail['name']}")
            print(f"  技能描述：{detail['description'][:60]}...")
            print(f"  元数据键：{list(detail['metadata'].keys())}")
            print(f"  Scripts 文件：{detail['scripts']}")
            print(f"  References 文件：{detail['references']}")
            print(f"  Assets 文件：{detail['assets']}")
            print(f"  内容长度：{len(detail['content'])} 字符")
        else:
            print("⚠ 没有可用的技能进行测试")
        
        print("\n✓ MCP 接口测试完成!")
        
    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()


def main():
    """主测试函数"""
    print("\n" + "=" * 70)
    print("技能加载 MCP 接口测试")
    print("=" * 70)
    
    try:
        # 测试 1: 基础功能
        test_skill_format()
        
        # 测试 2: 扫描技能
        test_scan_skills()
        
        # 测试 3: MCP 接口
        test_mcp_interface()
        
        print("\n" + "=" * 70)
        print("✓ 所有测试完成!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ 测试过程中发生错误：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
