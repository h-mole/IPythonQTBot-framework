"""
单元测试 - 测试 List[BaseSettings] 的功能
"""
import sys
sys.path.append(r"C:\Users\hzy\Programs\myhelper")
sys.path.append(r"C:\Users\hzy\Programs\myhelper\pyside6-settings")

from app_qt.configs import LLMProvider, LLMConfigSettings
from pathlib import Path
import json


def test_list_settings_basic():
    """测试 List[BaseSettings] 的基本功能"""
    print("=" * 60)
    print("测试 1: 创建包含 List[BaseSettings] 的配置")
    print("=" * 60)
    
    # 创建配置
    settings = LLMConfigSettings(
        provider="openai",
        model="gpt-4",
        max_context_messages=20,
        customization_name="test",
        provider_list=[
            LLMProvider(name="openai", api_key="sk-123", api_url="https://api.openai.com/v1"),
            LLMProvider(name="zhipu", api_key="abc", api_url="https://open.bigmodel.cn/api/paas/v4")
        ]
    )
    
    print(f"✓ 创建成功，provider_list 长度：{len(settings.provider_list)}")
    assert len(settings.provider_list) == 2
    print(f"✓ Provider 1: {settings.provider_list[0].name}")
    print(f"✓ Provider 2: {settings.provider_list[1].name}")
    

def test_list_settings_add_item():
    """测试动态添加 item"""
    print("\n" + "=" * 60)
    print("测试 2: 动态添加 item")
    print("=" * 60)
    
    settings = LLMConfigSettings(
        provider="openai",
        model="gpt-4",
        provider_list=[]
    )
    
    print(f"初始长度：{len(settings.provider_list)}")
    assert len(settings.provider_list) == 0
    
    # 模拟添加操作
    new_provider = LLMProvider(name="test", api_key="test-key", api_url="https://test.com")
    settings.provider_list.append(new_provider)
    
    print(f"添加后长度：{len(settings.provider_list)}")
    assert len(settings.provider_list) == 1
    print(f"✓ 添加成功：{settings.provider_list[0].name}")


def test_list_settings_load_save():
    """测试从文件加载和保存"""
    print("\n" + "=" * 60)
    print("测试 3: 加载和保存")
    print("=" * 60)
    
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        config_file = os.path.join(tmp_dir, "test_config.json")
    
    # 创建并保存配置
    original = LLMConfigSettings(
        provider="openai",
        model="gpt-4",
        provider_list=[
            LLMProvider(name="openai", api_key="sk-123", api_url="https://api.openai.com/v1"),
        ]
    )
    
    # 手动保存到文件
    data = original.model_dump()
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 配置已保存到：{config_file}")
    
    # 从文件加载
    loaded = LLMConfigSettings.load(config_file=config_file)
    
    print(f"✓ 配置已从文件加载")
    print(f"✓ Provider List 长度：{len(loaded.provider_list)}")
    assert len(loaded.provider_list) == 1
    print(f"✓ Provider 名称：{loaded.provider_list[0].name}")


def test_type_detection():
    """测试类型检测功能"""
    print("\n" + "=" * 60)
    print("测试 4: 类型检测")
    print("=" * 60)
    
    from typing import get_args, get_origin, List
    
    field_type = list[LLMProvider]
    origin = get_origin(field_type)
    
    print(f"Field type: {field_type}")
    print(f"Origin: {origin}")
    
    is_list = origin is list or origin is List
    print(f"Is List type: {is_list}")
    
    if is_list:
        args = get_args(field_type)
        print(f"Args: {args}")
        if args:
            item_type = args[0]
            print(f"Item type: {item_type}")
            print(f"Item type name: {item_type.__name__}")
            
            # 检查是否是 BaseSettings 子类
            from pyside6_settings import BaseSettings
            is_subclass = isinstance(item_type, type) and issubclass(item_type, BaseSettings)
            print(f"Is BaseSettings subclass: {is_subclass}")
            assert is_subclass
    
    print("✓ 类型检测通过")


if __name__ == "__main__":
    try:
        test_list_settings_basic()
        test_list_settings_add_item()
        test_list_settings_load_save()
        test_type_detection()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
