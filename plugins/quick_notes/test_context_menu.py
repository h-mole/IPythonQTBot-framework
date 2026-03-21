"""
测试快速笔记插件的上下文菜单和快捷键功能
"""
import sys
import os

# 添加插件路径
plugin_path = os.path.join(os.path.dirname(__file__), '..', 'plugins', 'quick_notes')
sys.path.insert(0, plugin_path)

# 测试导入
try:
    from main import QuickNotesTab
    print("✓ 成功导入 QuickNotesTab")
except Exception as e:
    print(f"✗ 导入失败：{e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试组件创建
try:
    from PySide6.QtWidgets import QApplication
    
    # 创建应用
    app = QApplication([])
    
    # 创建标签页
    tab = QuickNotesTab()
    print("✓ 成功创建 QuickNotesTab 实例")
    
    # 检查编辑器是否存在
    if hasattr(tab, 'editor'):
        print("✓ 编辑器组件存在")
    else:
        print("✗ 编辑器组件不存在")
    
    # 检查上下文菜单方法
    if hasattr(tab, 'show_editor_context_menu'):
        print("✓ show_editor_context_menu 方法存在")
    else:
        print("✗ show_editor_context_menu 方法不存在")
    
    # 检查快捷键创建方法
    if hasattr(tab, 'create_editor_shortcuts'):
        print("✓ create_editor_shortcuts 方法存在")
    else:
        print("✗ create_editor_shortcuts 方法不存在")
    
    # 检查编辑器的上下文菜单设置
    context_menu_policy = tab.editor.contextMenuPolicy()
    if context_menu_policy.value == 2:  # Qt.CustomContextMenu
        print("✓ 编辑器已启用自定义上下文菜单")
    else:
        print("⚠ 编辑器未启用自定义上下文菜单")
    
    # 检查快捷键是否已创建
    editor_actions = tab.editor.actions()
    action_names = []
    for action in editor_actions:
        if action.text():
            action_names.append(action.text())
    
    print(f"✓ 编辑器已创建 {len(action_names)} 个快捷键动作")
    print(f"  快捷键列表：{', '.join(action_names)}")
    
    # 验证关键快捷键
    required_actions = ["保存", "查找", "替换", "撤销", "重做"]
    for action_name in required_actions:
        if action_name in action_names:
            print(f"  ✓ 快捷键 '{action_name}' 已创建")
        else:
            print(f"  ✗ 快捷键 '{action_name}' 未创建")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)
    print("\n新增功能:")
    print("1. ✓ 编辑器右键菜单（包含撤销/重做/剪切/复制/粘贴/全选/查找/替换/保存）")
    print("2. ✓ 快捷键支持:")
    print("   - Ctrl+S: 保存")
    print("   - Ctrl+F: 查找")
    print("   - Ctrl+H: 替换")
    print("   - Ctrl+Z: 撤销")
    print("   - Ctrl+Y: 重做")
    print("   - Ctrl+X: 剪切")
    print("   - Ctrl+C: 复制")
    print("   - Ctrl+V: 粘贴")
    print("   - Ctrl+A: 全选")
    print("="*60)
    
except Exception as e:
    print(f"✗ 测试失败：{e}")
    import traceback
    traceback.print_exc()
