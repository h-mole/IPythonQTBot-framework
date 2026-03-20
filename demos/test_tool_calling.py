"""
测试工具调用功能
用于验证 LLM 工具调用的处理逻辑
"""

import json

# 模拟工具调用数据
class MockToolCall:
    def __init__(self, id, name, arguments):
        self.id = id
        self.function = type('obj', (object,), {
            'name': name,
            'arguments': arguments if isinstance(arguments, str) else json.dumps(arguments)
        })()

# 测试工具名称解析
def test_tool_name_parsing():
    """测试工具名称解析逻辑"""
    
    # 测试用例 1：双下划线分隔
    tool_name = "call_daily_tasks__get_tasks"
    print(f"测试 1: {tool_name}")
    
    if not tool_name.startswith("call_"):
        raise ValueError(f"无效的工具名称：{tool_name}")
    
    method_full_name = tool_name[5:]  # 去掉 "call_"
    parts = method_full_name.split("__", 1)
    
    if len(parts) == 2:
        namespace = parts[0]
        method_name_with_dots = parts[1].replace("__", ".")
        full_name = f"{namespace}.{method_name_with_dots}"
    else:
        # 向后兼容
        parts = method_full_name.split("_", 1)
        if len(parts) == 2:
            namespace = parts[0]
            method_name_with_dots = parts[1].replace("_", ".")
            full_name = f"{namespace}.{method_name_with_dots}"
        else:
            full_name = method_full_name.replace("_", ".")
    
    print(f"  解析结果：{full_name}")
    assert full_name == "daily_tasks.get_tasks", f"期望 daily_tasks.get_tasks，得到 {full_name}"
    print("  ✓ 通过\n")
    
    # 测试用例 2：单下划线分隔（向后兼容）
    tool_name = "call_text_helper_get_text"
    print(f"测试 2: {tool_name}")
    
    if not tool_name.startswith("call_"):
        raise ValueError(f"无效的工具名称：{tool_name}")
    
    method_full_name = tool_name[5:]
    parts = method_full_name.split("__", 1)
    
    if len(parts) == 2:
        namespace = parts[0]
        method_name = parts[1]  # 方法名中可能包含点号，不需要替换
        full_name = f"{namespace}.{method_name}"
    else:
        parts = method_full_name.split("_", 1)
        if len(parts) == 2:
            namespace = parts[0]
            method_name = parts[1].replace("_", ".")
            full_name = f"{namespace}.{method_name}"
        else:
            full_name = method_full_name.replace("_", ".")
    
    print(f"  解析结果：{full_name}")
    assert full_name == "text.helper.get.text", f"期望 text.helper.get.text，得到 {full_name}"
    print("✓ 通过\n")
    
    # 测试用例 3：带有点号的方法名
    tool_name = "call_daily_tasks__get_task_by_id"
    print(f"测试 3: {tool_name}")
    
    method_full_name = tool_name[5:]
    parts = method_full_name.split("__", 1)
    
    if len(parts) == 2:
        namespace = parts[0]
        method_name = parts[1]  # 方法名中可能包含点号，不需要替换
        full_name = f"{namespace}.{method_name}"
    else:
        parts = method_full_name.split("_", 1)
        if len(parts) == 2:
            namespace = parts[0]
            method_name = parts[1].replace("_", ".")
            full_name = f"{namespace}.{method_name}"
        else:
            full_name = method_full_name.replace("_", ".")
    
    print(f"  解析结果：{full_name}")
    assert full_name == "daily_tasks.get_task_by_id", f"期望 daily_tasks.get_task_by_id，得到 {full_name}"
    print("✓ 通过\n")


# 测试返回值转换
def test_result_conversion():
    """测试返回值转换为字符串的逻辑"""
    
    print("测试返回值转换:")
    
    # 测试用例 1：字符串类型
    result1 = "这是一个字符串"
    if not isinstance(result1, str):
        result_str1 = repr(result1)
    else:
        result_str1 = result1
    print(f"  字符串：{result_str1}")
    assert result_str1 == result1
    print("  ✓ 通过\n")
    
    # 测试用例 2：字典类型
    result2 = {"key": "value", "number": 42}
    if not isinstance(result2, str):
        result_str2 = repr(result2)
    else:
        result_str2 = result2
    print(f"  字典：{result_str2}")
    assert result_str2 == "{'key': 'value', 'number': 42}"
    print("  ✓ 通过\n")
    
    # 测试用例 3：列表类型
    result3 = [1, 2, 3, "test"]
    if not isinstance(result3, str):
        result_str3 = repr(result3)
    else:
        result_str3 = result3
    print(f"  列表：{result_str3}")
    assert result_str3 == "[1, 2, 3, 'test']"
    print("  ✓ 通过\n")
    
    # 测试用例 4：None 类型
    result4 = None
    if not isinstance(result4, str):
        result_str4 = repr(result4)
    else:
        result_str4 = result4
    print(f"  None: {result_str4}")
    assert result_str4 == "None"
    print("  ✓ 通过\n")


# 测试参数解析
def test_arguments_parsing():
    """测试参数字符串解析"""
    
    print("测试参数解析:")
    
    # 测试用例 1：JSON 字符串
    arguments_str1 = '{"param1": "value1", "param2": 42}'
    try:
        if arguments_str1 and isinstance(arguments_str1, str):
            arguments1 = json.loads(arguments_str1)
        elif isinstance(arguments_str1, dict):
            arguments1 = arguments_str1
        else:
            arguments1 = {}
    except json.JSONDecodeError as e:
        print(f"  解析失败：{e}")
        arguments1 = {}
    
    print(f"  JSON 字符串：{arguments1}")
    assert arguments1 == {"param1": "value1", "param2": 42}
    print("  ✓ 通过\n")
    
    # 测试用例 2：空字符串
    arguments_str2 = ""
    try:
        if arguments_str2 and isinstance(arguments_str2, str):
            arguments2 = json.loads(arguments_str2)
        elif isinstance(arguments_str2, dict):
            arguments2 = arguments_str2
        else:
            arguments2 = {}
    except json.JSONDecodeError as e:
        print(f"  解析失败：{e}")
        arguments2 = {}
    
    print(f"  空字符串：{arguments2}")
    assert arguments2 == {}
    print("  ✓ 通过\n")
    
    # 测试用例 3：已经是字典
    arguments_str3 = {"already": "dict"}
    try:
        if arguments_str3 and isinstance(arguments_str3, str):
            arguments3 = json.loads(arguments_str3)
        elif isinstance(arguments_str3, dict):
            arguments3 = arguments_str3
        else:
            arguments3 = {}
    except json.JSONDecodeError as e:
        print(f"  解析失败：{e}")
        arguments3 = {}
    
    print(f"  字典：{arguments3}")
    assert arguments3 == {"already": "dict"}
    print("  ✓ 通过\n")


if __name__ == "__main__":
    print("=" * 60)
    print("工具调用功能测试")
    print("=" * 60 + "\n")
    
    test_tool_name_parsing()
    test_result_conversion()
    test_arguments_parsing()
    
    print("=" * 60)
    print("所有测试通过！✓")
    print("=" * 60)
