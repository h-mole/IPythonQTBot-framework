"""
测试技能树状加载功能
"""

import sys
import os

# 添加插件路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'plugins', 'quick_notes'))

from utils.skill_format import SkillFormat


def test_skills_tree():
    """测试技能树扫描和格式化"""
    
    # 测试 1: 扫描 .claude/skills 目录
    print("=" * 60)
    print("测试 1: 扫描 .claude/skills 目录（嵌套技能组）")
    print("=" * 60)
    
    skills_base_dir = r"C:\Users\hzy\Programs\myhelper\.claude\skills"
    
    # 使用新的树状扫描方法
    tree_nodes = SkillFormat.scan_skills_tree(skills_base_dir)
    
    print(f"\n找到 {len(tree_nodes)} 个顶级节点:\n")
    
    # 格式化为 LLM 可读的文本格式
    formatted_text = SkillFormat.format_skills_tree_for_llm(tree_nodes)
    print(formatted_text)
    
    # 测试 2: 扫描 plugins/quick_notes/components 目录（如果存在技能）
    print("\n" + "=" * 60)
    print("测试 2: 扫描 plugins/quick_notes/components 目录")
    print("=" * 60)
    
    components_dir = r"C:\Users\hzy\Programs\myhelper\plugins\quick_notes\components"
    if os.path.exists(components_dir):
        component_tree = SkillFormat.scan_skills_tree(components_dir)
        if component_tree:
            print(f"\n找到 {len(component_tree)} 个节点:\n")
            print(SkillFormat.format_skills_tree_for_llm(component_tree))
        else:
            print("\n该目录下没有找到技能文件")
    else:
        print("\n目录不存在")
    
    # 测试 3: 对比旧版扁平化扫描
    print("\n" + "=" * 60)
    print("测试 3: 使用旧版扁平化扫描（向后兼容）")
    print("=" * 60)
    
    flat_skills = SkillFormat.scan_skills_directory(skills_base_dir)
    print(f"\n找到 {len(flat_skills)} 个技能（扁平列表）:")
    for skill in flat_skills:
        print(f"  - {skill['name']}: {skill['description'][:50]}")
    
    # 测试 4: 获取祖先路径
    print("\n" + "=" * 60)
    print("测试 4: 获取技能的祖先路径")
    print("=" * 60)
    
    test_paths = [
        "gitnexus/gitnexus-cli",
        "gitnexus/gitnexus-debugging",
    ]
    
    for path in test_paths:
        ancestors = SkillFormat.get_skill_ancestors(path)
        print(f"  {path} -> {ancestors}")


if __name__ == "__main__":
    test_skills_tree()
