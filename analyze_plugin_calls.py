#!/usr/bin/env python3
"""
插件调用分析演示脚本
展示如何使用 PluginCallAnalyzer 分析代码中的 plugin_manager 调用

此版本使用类型追踪来精确识别 PluginManager 实例，减少误报
"""

from plugin_call_analyzer import PluginCallAnalyzer


def main():
    # 创建分析器实例
    analyzer = PluginCallAnalyzer()
    
    # 分析插件目录
    print("Analyzing plugins directory...")
    results = analyzer.analyze_directory("./plugins")
    
    # 打印统计信息
    total_calls = sum(len(r.calls) for r in results)
    resolved = len(analyzer.get_all_resolved_calls())
    unresolved = len(analyzer.get_unresolved_calls())
    
    print(f"\nAnalysis complete!")
    print(f"  Files analyzed: {len(results)}")
    print(f"  Total calls: {total_calls}")
    print(f"  Resolved: {resolved}")
    print(f"  Unresolved: {unresolved}")
    
    # 打印所有注册的方法
    print("\n\n=== Registered Methods ===")
    for result in results:
        for call in result.calls:
            if call.call_type.value == "register_method" and call.is_resolved:
                print(f"  - {call.method_name} (at {result.file_path}:{call.line_number}, via {call.variable_name})")
    
    # 打印所有 get_method 调用
    print("\n\n=== get_method Calls ===")
    for result in results:
        for call in result.calls:
            if call.call_type.value == "get_method" and call.is_resolved:
                print(f"  - {call.method_name} (at {result.file_path}:{call.line_number}, via {call.variable_name})")
    
    # 打印未解析的警告
    unresolved_calls = analyzer.get_unresolved_calls()
    if unresolved_calls:
        print("\n\n=== Unresolved Calls (WARNING) ===")
        for call in unresolved_calls:
            print(f"  - {call.source_file}:{call.line_number} (via {call.variable_name})")
            for warning in call.warnings:
                print(f"    {warning}")
    
    # 生成 JSON 报告
    json_report = analyzer.generate_json_report()
    with open("plugin_calls_report.json", "w", encoding="utf-8") as f:
        f.write(json_report)
    print("\n\nJSON report saved to: plugin_calls_report.json")
    
    # 同时分析 app_qt 目录
    print("\n\nAnalyzing app_qt directory...")
    analyzer2 = PluginCallAnalyzer()
    results2 = analyzer2.analyze_directory("./app_qt")
    
    total_calls2 = sum(len(r.calls) for r in results2)
    resolved2 = len(analyzer2.get_all_resolved_calls())
    unresolved2 = len(analyzer2.get_unresolved_calls())
    
    print(f"  Files analyzed: {len(results2)}")
    print(f"  Total calls: {total_calls2}")
    print(f"  Resolved: {resolved2}")
    print(f"  Unresolved: {unresolved2}")
    
    # 打印系统方法注册
    print("\n\n=== System Methods Registered ===")
    for result in results2:
        for call in result.calls:
            if call.call_type.value == "_register_system_method" and call.is_resolved:
                print(f"  - {call.method_name} (at {result.file_path}:{call.line_number}, via {call.variable_name})")


if __name__ == "__main__":
    main()
