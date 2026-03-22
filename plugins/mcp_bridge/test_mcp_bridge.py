"""
MCP Bridge 插件测试脚本
用于验证 MCP Bridge 插件的基本功能
"""

import sys
import os
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_qt.plugin_manager import get_plugin_manager


def test_plugin_load():
    """测试 1: 插件加载"""
    print("=" * 60)
    print("测试 1: 插件加载")
    print("=" * 60)
    
    pm = get_plugin_manager()
    
    try:
        result = pm.load_plugin("mcp_bridge")
        if result:
            print("✓ 插件加载成功")
            return True, pm
        else:
            print("✗ 插件加载失败")
            return False, None
    except Exception as e:
        print(f"✗ 插件加载异常：{e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_list_servers(pm):
    """测试 2: 列出已配置的服务器"""
    print("\n" + "=" * 60)
    print("测试 2: 列出已配置的服务器")
    print("=" * 60)
    
    try:
        servers = pm.get_method("mcp_bridge.list_servers")()
        print(f"已配置服务器 ({len(servers)} 个):")
        for server in servers:
            print(f"  - {server}")
        
        if servers:
            print("✓ 测试通过")
            return True
        else:
            print("⚠ 未配置任何服务器，请检查配置文件")
            return True
            
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_get_tools(pm):
    """测试 3: 获取工具列表"""
    print("\n" + "=" * 60)
    print("测试 3: 获取工具列表")
    print("=" * 60)
    
    try:
        # 等待几秒让服务器自动连接
        print("等待服务器连接...")
        import time
        time.sleep(3)
        
        tools = pm.get_method("mcp_bridge.get_mcp_tools")()
        print(f"获取到工具 ({len(tools)} 个):")
        
        for i, tool in enumerate(tools[:5], 1):  # 只显示前 5 个
            func_name = tool.get('function', {}).get('name', 'unknown')
            desc = tool.get('function', {}).get('description', '')[:50]
            print(f"  {i}. {func_name}: {desc}...")
        
        if len(tools) > 5:
            print(f"  ... 还有 {len(tools) - 5} 个工具")
        
        print("✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools_info(pm):
    """测试 4: 获取工具信息文本"""
    print("\n" + "=" * 60)
    print("测试 4: 获取工具信息文本")
    print("=" * 60)
    
    try:
        info = pm.get_method("mcp_bridge.get_tools_info")(detailed=False)
        print(info)
        print("✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def test_detailed_tools_info(pm):
    """测试 5: 获取详细工具信息"""
    print("\n" + "=" * 60)
    print("测试 5: 获取详细工具信息（仅前 2 个工具）")
    print("=" * 60)
    
    try:
        info = pm.get_method("mcp_bridge.get_tools_info")(detailed=True)
        # 只显示前两个工具的详细信息，避免输出太长
        lines = info.split('\n')
        if len(lines) > 30:
            print('\n'.join(lines[:30]))
            print(f"\n... 还有 {len(lines) - 30} 行")
        else:
            print(info)
        
        print("✓ 测试通过")
        return True
        
    except Exception as e:
        print(f"✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("MCP Bridge 插件测试套件")
    print("=" * 60)
    
    # 测试 1: 加载插件
    success, pm = test_plugin_load()
    if not success or pm is None:
        print("\n✗ 插件加载失败，后续测试无法继续")
        return
    
    # 测试 2: 列出服务器
    test_list_servers(pm)
    
    # 测试 3: 获取工具列表
    test_get_tools(pm)
    
    # 测试 4: 获取工具信息
    test_tools_info(pm)
    
    # 测试 5: 获取详细工具信息
    test_detailed_tools_info(pm)
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    
    # 提示
    print("\n提示:")
    print("1. 如果看到 '未配置任何服务器'，请编辑配置文件：~/IPythonQTBot/plugin_data/mcp_bridge/config.json")
    print("2. 如果工具数量为 0，请检查 MCP 服务器是否可连接")
    print("3. 查看 QUICKSTART.md 了解更多使用方法")


if __name__ == "__main__":
    main()
