"""
技能树加载示例 - 演示如何在实际场景中使用
"""

import sys
import os

# 添加正确的导入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'plugins', 'quick_notes'))

from utils.skill_format import SkillFormat


def example_1_basic_tree_loading():
    """示例 1: 基础技能树加载"""
    print("=" * 60)
    print("示例 1: 基础技能树加载")
    print("=" * 60)
    
    skills_dir = r"C:\Users\hzy\Programs\myhelper\.claude\skills"
    
    # 加载技能树
    tree = SkillFormat.scan_skills_tree(skills_dir)
    
    # 格式化为文本（适合发送给 LLM）
    text_output = SkillFormat.format_skills_tree_for_llm(tree)
    print("\n格式化输出:")
    print(text_output)
    
    return tree


def example_2_programmatic_access(tree):
    """示例 2: 编程方式访问技能树结构"""
    print("\n" + "=" * 60)
    print("示例 2: 编程方式访问技能树")
    print("=" * 60)
    
    def process_node(node, depth=0):
        """递归处理节点"""
        indent = "  " * depth
        
        if node["type"] == "group":
            print(f"{indent}📁 目录组：{node['name']}")
            print(f"{indent}   路径：{node['relative_path']}")
            print(f"{indent}   子节点数：{len(node.get('children', []))}")
            
            # 递归处理子节点
            for child in node.get("children", []):
                process_node(child, depth + 1)
        
        else:  # skill
            print(f"{indent}✅ 技能：{node['name']}")
            print(f"{indent}   描述：{node['description'][:60]}...")
            print(f"{indent}   路径：{node['relative_path']}")
            print(f"{indent}   有脚本：{node.get('has_scripts', False)}")
            if node.get('version'):
                print(f"{indent}   版本：v{node['version']}")
    
    for node in tree:
        process_node(node)


def example_3_filter_skills(tree):
    """示例 3: 过滤和搜索技能"""
    print("\n" + "=" * 60)
    print("示例 3: 搜索特定技能")
    print("=" * 60)
    
    def find_skills_by_keyword(tree_nodes, keyword):
        """根据关键词查找技能"""
        results = []
        
        for node in tree_nodes:
            if node["type"] == "skill":
                if keyword.lower() in node["name"].lower() or \
                   keyword.lower() in node["description"].lower():
                    results.append(node)
            elif node["type"] == "group":
                # 递归搜索子节点
                results.extend(find_skills_by_keyword(
                    node.get("children", []), keyword
                ))
        
        return results
    
    # 搜索包含 "git" 的技能
    keyword = "git"
    matches = find_skills_by_keyword(tree, keyword)
    
    print(f"\n找到 {len(matches)} 个包含 '{keyword}' 的技能:")
    for match in matches:
        print(f"  - {match['name']} ({match['relative_path']})")
        print(f"    {match['description'][:80]}...")


def example_4_build_context_for_llm(tree):
    """示例 4: 为 LLM 构建上下文信息"""
    print("\n" + "=" * 60)
    print("示例 4: 为 LLM 构建技能目录上下文")
    print("=" * 60)
    
    # 构建一个简洁的摘要
    def count_skills(tree_nodes):
        """统计技能数量"""
        count = 0
        for node in tree_nodes:
            if node["type"] == "skill":
                count += 1
            elif node["type"] == "group":
                count += count_skills(node.get("children", []))
        return count
    
    total_skills = count_skills(tree)
    total_groups = sum(1 for n in tree if n["type"] == "group")
    
    context = f"""
# 可用技能目录

系统中共有 **{total_skills}** 个技能，分布在 **{total_groups}** 个技能组中。

## 技能列表（带缩进显示层级）

```
{SkillFormat.format_skills_tree_for_llm(tree)}
```

## 使用说明

- 📁 表示技能组（目录）
- ✅ 表示带有 scripts 的技能
- 📄 表示纯文档技能
- 缩进表示层级关系

你可以根据用户请求选择合适的技能。例如:
- "如何使用 GitNexus?" -> 选择 `gitnexus-guide`
- "分析代码影响范围" -> 选择 `gitnexus-impact-analysis`
- "调试 bug" -> 选择 `gitnexus-debugging`
"""
    
    print(context)
    return context


if __name__ == "__main__":
    # 加载技能树
    tree = SkillFormat.scan_skills_tree(
        r"C:\Users\hzy\Programs\myhelper\.claude\skills"
    )
    
    # 运行示例
    example_1_basic_tree_loading()
    example_2_programmatic_access(tree)
    example_3_filter_skills(tree)
    example_4_build_context_for_llm(tree)
    
    print("\n" + "=" * 60)
    print("所有示例完成！")
    print("=" * 60)
