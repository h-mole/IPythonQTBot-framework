"""
Skill Format Utility - 用于加载和解析 agentskills-core 兼容的技能文件

支持读取 SKILL.md 文件的 YAML frontmatter 和 Markdown 内容
提供技能概要信息和详细信息的提取功能
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    print("[提示] 未安装 PyYAML，将使用基础 YAML 解析")


class SkillFormat:
    """Skill 格式处理类"""
    
    @staticmethod
    def parse_yaml_frontmatter(content: str) -> Dict[str, Any]:
        """
        解析 YAML frontmatter
        
        Args:
            content: SKILL.md 文件完整内容
            
        Returns:
            解析后的元数据字典
        """
        # 匹配 YAML frontmatter (--- 之间的内容)
        match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if not match:
            return {}
        
        yaml_content = match.group(1)
        
        if YAML_AVAILABLE:
            try:
                result = yaml.safe_load(yaml_content)
                return result if isinstance(result, dict) else {}
            except Exception as e:
                print(f"[SkillFormat] YAML 解析失败：{e}")
                return {}
        else:
            # 基础 YAML 解析（仅支持简单键值对）
            return SkillFormat._parse_yaml_simple(yaml_content)
    
    @staticmethod
    def _parse_yaml_simple(yaml_content: str) -> Dict[str, Any]:
        """
        简单的 YAML 解析器（当 PyYAML 不可用时）
        
        Args:
            yaml_content: YAML 格式字符串
            
        Returns:
            解析后的字典
        """
        result = {}
        lines = yaml_content.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # 去除引号
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # 尝试转换类型
                if value.lower() == 'true':
                    value = True
                elif value.lower() == 'false':
                    value = False
                elif value.isdigit():
                    value = int(value)
                
                result[key] = value
        
        return result
    
    @staticmethod
    def get_skill_markdown_body(content: str) -> str:
        """
        获取 SKILL.md 的 Markdown 正文部分（去除 YAML frontmatter）
        
        Args:
            content: SKILL.md 文件完整内容
            
        Returns:
            Markdown 正文字符串
        """
        # 移除 YAML frontmatter
        match = re.match(r'^---\s*\n.*?\n---\s*\n', content, re.DOTALL)
        if match:
            return content[match.end():]
        return content
    
    @staticmethod
    def load_skill_summary(skill_dir: str) -> Optional[Dict[str, Any]]:
        """
        加载技能的概要信息（仅读取 name 和 description）
        
        Args:
            skill_dir: 技能文件夹路径
            
        Returns:
            包含技能概要信息的字典，如果加载失败则返回 None
            {
                "name": "skill-name",
                "description": "技能描述",
                "path": "skills/skill-name",
                "has_scripts": True/False,
                "has_references": True/False,
                "has_assets": True/False
            }
        """
        skill_file = os.path.join(skill_dir, "SKILL.md")
        
        if not os.path.exists(skill_file):
            print(f"[SkillFormat] 未找到 SKILL.md 文件：{skill_file}")
            return None
        
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = SkillFormat.parse_yaml_frontmatter(content)
            
            # 检查子目录
            has_scripts = os.path.exists(os.path.join(skill_dir, 'scripts'))
            has_references = os.path.exists(os.path.join(skill_dir, 'references'))
            has_assets = os.path.exists(os.path.join(skill_dir, 'assets'))
            
            return {
                "name": metadata.get('name', os.path.basename(skill_dir)),
                "description": metadata.get('description', '无描述'),
                "path": skill_dir,
                "has_scripts": has_scripts,
                "has_references": has_references,
                "has_assets": has_assets,
                "version": metadata.get('version', ''),
                "author": metadata.get('author', ''),
                "license": metadata.get('license', '')
            }
            
        except Exception as e:
            print(f"[SkillFormat] 加载技能概要失败：{skill_file}, 错误：{e}")
            return None
    
    @staticmethod
    def load_skill_detail(skill_dir: str) -> Optional[Dict[str, Any]]:
        """
        加载技能的详细信息（包括完整的 SKILL.md 内容）
        
        Args:
            skill_dir: 技能文件夹路径
            
        Returns:
            包含技能详细信息的字典，如果加载失败则返回 None
            {
                "name": "skill-name",
                "description": "技能描述",
                "path": "skills/skill-name",
                "metadata": {...},  # 完整的 YAML 元数据
                "content": "...",   # 完整的 Markdown 内容
                "scripts": [...],   # scripts 目录下的文件列表
                "references": [...], # references 目录下的文件列表
                "assets": [...]     # assets 目录下的文件列表
            }
        """
        skill_file = os.path.join(skill_dir, "SKILL.md")
        
        if not os.path.exists(skill_file):
            print(f"[SkillFormat] 未找到 SKILL.md 文件：{skill_file}")
            return None
        
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = SkillFormat.parse_yaml_frontmatter(content)
            markdown_body = SkillFormat.get_skill_markdown_body(content)
            
            # 获取子目录内容
            scripts = []
            references = []
            assets = []
            
            scripts_dir = os.path.join(skill_dir, 'scripts')
            if os.path.exists(scripts_dir):
                scripts = [f for f in os.listdir(scripts_dir) if os.path.isfile(os.path.join(scripts_dir, f))]
            
            references_dir = os.path.join(skill_dir, 'references')
            if os.path.exists(references_dir):
                references = [f for f in os.listdir(references_dir) if os.path.isfile(os.path.join(references_dir, f))]
            
            assets_dir = os.path.join(skill_dir, 'assets')
            if os.path.exists(assets_dir):
                assets = [f for f in os.listdir(assets_dir) if os.path.isfile(os.path.join(assets_dir, f))]
            
            return {
                "name": metadata.get('name', os.path.basename(skill_dir)),
                "description": metadata.get('description', '无描述'),
                "path": skill_dir,
                "metadata": metadata,
                "content": markdown_body,
                "full_content": content,  # 包含 frontmatter 的完整内容
                "scripts": scripts,
                "references": references,
                "assets": assets
            }
            
        except Exception as e:
            print(f"[SkillFormat] 加载技能详情失败：{skill_file}, 错误：{e}")
            return None
    
    @staticmethod
    def scan_skills_directory(skills_base_dir: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        """
        扫描技能目录，获取所有技能的概要信息（支持嵌套目录）
        
        Args:
            skills_base_dir: 技能根目录路径
            max_depth: 最大递归深度，默认 3 层
            
        Returns:
            技能概要信息列表（扁平化）
        """
        skills: List[Dict[str, Any]] = []
        
        if not os.path.exists(skills_base_dir):
            print(f"[SkillFormat] 技能目录不存在：{skills_base_dir}")
            return skills
        
        # 遍历技能目录
        for item in os.listdir(skills_base_dir):
            item_path = os.path.join(skills_base_dir, item)
            
            # 只处理目录
            if not os.path.isdir(item_path):
                continue
            
            # 检查是否有 SKILL.md 文件
            skill_file = os.path.join(item_path, "SKILL.md")
            if not os.path.exists(skill_file):
                continue
            
            # 加载技能概要
            summary = SkillFormat.load_skill_summary(item_path)
            if summary:
                skills.append(summary)
        
        return skills
    
    @staticmethod
    def scan_skills_tree(skills_base_dir: str, max_depth: int = 5) -> List[Dict[str, Any]]:
        """
        扫描技能目录，返回树状结构的技能信息（支持嵌套目录和缩进显示）
        
        Args:
            skills_base_dir: 技能根目录路径
            max_depth: 最大递归深度，默认 5 层
            
        Returns:
            树状结构的技能信息列表，每个节点包含：
            {
                "name": "技能/目录名",
                "type": "group" | "skill",  # group=目录组，skill=具体技能
                "level": 0,  # 层级（缩进级别）
                "relative_path": "相对于根目录的路径",
                "children": [...],  # 仅 group 类型有
                # 以下是 skill 类型的额外字段
                "description": "技能描述",
                "has_scripts": True/False,
                "has_references": True/False,
                "has_assets": True/False,
                "version": "版本号",
                "author": "作者",
                "license": "许可证"
            }
        """
        def scan_recursive(current_dir: str, current_level: int, base_dir: str) -> List[Dict[str, Any]]:
            """递归扫描目录"""
            result: List[Dict[str, Any]] = []
            
            if not os.path.exists(current_dir):
                return result
            
            # 达到最大深度则停止递归
            if current_level > max_depth:
                return result
            
            items = sorted(os.listdir(current_dir))
            
            for item in items:
                item_path = os.path.join(current_dir, item)
                relative_path = os.path.relpath(item_path, base_dir)
                
                # 跳过隐藏文件和__pycache__
                if item.startswith('__') or item.startswith('.'):
                    continue
                
                if os.path.isdir(item_path):
                    # 检查是否是技能目录（有 SKILL.md）
                    skill_file = os.path.join(item_path, "SKILL.md")
                    if os.path.exists(skill_file):
                        # 这是一个技能节点
                        summary = SkillFormat.load_skill_summary(item_path)
                        if summary:
                            node = {
                                "name": summary.get('name', item),
                                "type": "skill",
                                "level": current_level,
                                # "path": item_path,
                                "relative_path": relative_path,
                                "description": summary.get('description', '无描述'),
                                "has_scripts": summary.get('has_scripts', False),
                                "has_references": summary.get('has_references', False),
                                "has_assets": summary.get('has_assets', False),
                                "version": summary.get('version', ''),
                                "author": summary.get('author', ''),
                                "license": summary.get('license', '')
                            }
                            result.append(node)
                    else:
                        # 这是一个目录组节点
                        children = scan_recursive(item_path, current_level + 1, base_dir)
                        if children:  # 只有当子节点非空时才添加
                            node = {
                                "name": item,
                                "type": "group",
                                "level": current_level,
                                # "path": item_path,
                                "relative_path": relative_path,
                                "children": children
                            }
                            result.append(node)
            
            return result
        
        return scan_recursive(skills_base_dir, 0, skills_base_dir)
    
    @staticmethod
    def format_skills_tree_for_llm(tree_nodes: List[Dict[str, Any]], indent: str = "  ") -> str:
        """
        将技能树格式化为适合 LLM 阅读的文本格式（带缩进）
        
        Args:
            tree_nodes: 技能树节点列表
            indent: 每级缩进字符串，默认 2 个空格
            
        Returns:
            格式化的文本字符串
        """
        lines = []
        
        def format_node(node: Dict[str, Any], level: int):
            """格式化单个节点"""
            prefix = indent * level
            
            if node["type"] == "group":
                # 目录组
                lines.append(f"{prefix}📁 {node['name']} (技能组)")
                # 递归处理子节点
                for child in node.get("children", []):
                    format_node(child, level + 1)
            else:
                # 技能
                icon = "✅" if node.get("has_scripts") else "📄"
                desc = node.get('description', '无描述')[:50]  # 限制描述长度
                if len(node.get('description', '')) > 50:
                    desc += "..."
                
                extra_info = []
                if node.get('version'):
                    extra_info.append(f"v{node['version']}")
                if node.get('author'):
                    extra_info.append(node['author'])
                
                extra_str = f" [{', '.join(extra_info)}]" if extra_info else ""
                lines.append(f"{prefix}{icon} {node['name']}: {desc}{extra_str}")
        
        for node in tree_nodes:
            format_node(node, node["level"])
        
        return "\n".join(lines)
    
    @staticmethod
    def get_skill_ancestors(relative_path: str) -> List[str]:
        """
        获取技能的祖先路径（用于构建完整技能路径）
        
        Args:
            relative_path: 相对路径，如 "gitnexus/gitnexus-cli"
            
        Returns:
            祖先路径列表，如 ["gitnexus", "gitnexus-cli"]
        """
        from pathlib import Path
        parts = Path(relative_path).parts
        return list(parts)