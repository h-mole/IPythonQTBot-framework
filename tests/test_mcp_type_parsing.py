"""
测试使用 MCP 包的类型解析机制
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_qt.ipython_llm_bridge import Agent, LLMConfig

def test_mcp_type_parsing():
    """测试 MCP 类型解析功能"""
    print("\n" + "=" * 60)
    print("测试 MCP 类型解析机制")
    print("=" * 60)
    
    # 创建一个简单的测试函数，带有类型注解
    def test_function(name: str, age: int, score: float, active: bool) -> str:
        """
        测试函数
        
        Args:
            name: 姓名
            age: 年龄
            score: 分数
            active: 是否激活
            
        Returns:
            str: 结果
        """
        return f"{name}, {age}, {score}, {active}"
    
    # 创建 Agent（不需要真实的 API Key，只测试类型解析）
    try:
        # 模拟一个插件管理器
        class MockPluginManager:
            def get_all_methods(self, include_extra_data=False):
                return [{
                    "name": "test.func",
                    "extra_data": {"enable_mcp": True}
                }]
            
            def get_method(self, full_name):
                return test_function
        
        agent = Agent(plugin_manager=MockPluginManager())
        
        # 测试工具转换
        tools = agent._build_mcp_tools()
        
        print(f"\n成功转换了 {len(tools)} 个工具")
        
        if tools:
            tool = tools[0]
            print(f"\n工具名称：{tool['function']['name']}")
            print(f"工具描述：{tool['function']['description']}")
            print(f"\n参数定义:")
            for param_name, param_info in tool['function']['parameters']['properties'].items():
                print(f"  - {param_name}: {param_info['type']}")
                print(f"    描述：{param_info['description']}")
            
            print(f"\n必填参数：{tool['function']['parameters']['required']}")
            
            # 验证类型是否正确转换
            expected_types = {
                "name": "string",
                "age": "integer",
                "score": "number",
                "active": "boolean"
            }
            
            print("\n类型验证:")
            all_correct = True
            for param_name, expected_type in expected_types.items():
                actual_type = tool['function']['parameters']['properties'][param_name]['type']
                is_correct = actual_type == expected_type
                status = "✓" if is_correct else "✗"
                print(f"  {status} {param_name}: {actual_type} (期望：{expected_type})")
                if not is_correct:
                    all_correct = False
            
            if all_correct:
                print("\n✓ 所有类型都正确转换！MCP 类型解析机制工作正常")
            else:
                print("\n✗ 部分类型转换不正确")
                
    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()


def test_docstring_extraction():
    """测试文档字符串提取"""
    print("\n" + "=" * 60)
    print("测试文档字符串提取")
    print("=" * 60)
    
    def documented_function(param1: str, param2: int = 10) -> str:
        """
        这是一个有完整文档的函数
        
        Args:
            param1: 第一个参数，很重要
            param2: 第二个参数，有默认值
            
        Returns:
            str: 返回结果
        """
        return f"{param1}, {param2}"
    
    class MockPluginManager:
        def get_all_methods(self, include_extra_data=False):
            return [{"name": "test.doc_func", "extra_data": {"enable_mcp": True}}]
        
        def get_method(self, full_name):
            return documented_function
    
    try:
        agent = Agent(plugin_manager=MockPluginManager())
        tools = agent._build_mcp_tools()
        
        if tools:
            tool = tools[0]
            print(f"\n函数描述：{tool['function']['description']}")
            print(f"\n参数描述:")
            for param_name, param_info in tool['function']['parameters']['properties'].items():
                print(f"  - {param_name}: {param_info['description']}")
            
            # 验证是否从 docstring 中提取了描述
            has_good_description = "第一个参数" in tool['function']['parameters']['properties']['param1']['description']
            if has_good_description:
                print("\n✓ 成功从文档字符串提取参数描述")
            else:
                print("\n⚠ 未能从文档字符串提取描述（可能使用了基础实现）")
                
    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_mcp_type_parsing()
    test_docstring_extraction()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)
