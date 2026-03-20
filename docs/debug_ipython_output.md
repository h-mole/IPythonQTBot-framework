# IPython LLM Agent 输出调试指南

## 问题现象

在终端运行 Python 脚本可以看到 LLM 的流式输出，但在 IPython 控制台中看不到输出。

## 原因分析

IPython 控制台（特别是基于 Qt 的 RichJupyterWidget）使用自己的输出系统，而不是标准的 `sys.stdout`。

## 解决方案

### 方案 1: 使用 sys.stdout.write() (已实现)

```python
def _on_chunk_received(self, chunk: str):
    if hasattr(self, 'ipython_shell') and self.ipython_shell:
        import sys
        # 使用 IPython 的输出系统
        if hasattr(sys.stdout, 'write'):
            sys.stdout.write(chunk)
            sys.stdout.flush()
        else:
            print(chunk, end="", flush=True)
    else:
        print(chunk, end="", flush=True)
```

### 方案 2: 使用 IPython display 系统

如果方案 1 不起作用，可以尝试：

```python
from IPython.display import display, Markdown

def _on_chunk_received(self, chunk: str):
    if self.ipython_shell:
        # 累积内容并更新显示
        if not hasattr(self, '_current_response'):
            self._current_response = ""
        
        self._current_response += chunk
        
        # 使用 Markdown 格式显示
        display(Markdown(self._current_response), display_id=True, clear=True)
    else:
        print(chunk, end="", flush=True)
```

### 方案 3: 直接写入 IPython kernel 的输出流

```python
def _on_chunk_received(self, chunk: str):
    if self.ipython_shell:
        # 获取当前 kernel 的输出流
        kernel = self.ipython_shell.kernel
        if kernel and hasattr(kernel, 'stdout'):
            kernel.stdout.write(chunk)
            kernel.stdout.flush()
        else:
            print(chunk, end="", flush=True)
    else:
        print(chunk, end="", flush=True)
```

## 测试步骤

### 1. 检查 agent 是否正确注入

在 IPython 控制台中输入：

```python
agent
```

应该看到类似输出：
```
<app_qt.ipython_llm_bridge.Agent object at 0x...>
```

### 2. 检查 ipython_shell 引用

```python
agent.ipython_shell
```

应该看到 IPython shell 对象。

### 3. 测试基本输出

```python
print("测试输出")
```

确认 IPython 控制台能正常显示 print 输出。

### 4. 测试 LLM 对话

```python
agent.ask("你好")
```

观察是否有输出。

### 5. 调试输出流程

如果仍然没有输出，添加调试信息：

修改 `_on_chunk_received` 方法：

```python
def _on_chunk_received(self, chunk: str):
    print(f"[DEBUG] 收到 chunk: {repr(chunk)}", file=sys.stderr)
    
    if hasattr(self, 'ipython_shell') and self.ipython_shell:
        print(f"[DEBUG] 使用 IPython 输出系统", file=sys.stderr)
        import sys
        
        if hasattr(sys.stdout, 'write'):
            print(f"[DEBUG] sys.stdout 可用", file=sys.stderr)
            sys.stdout.write(chunk)
            sys.stdout.flush()
        else:
            print(f"[DEBUG] sys.stdout 不可用，回退到 print", file=sys.stderr)
            print(chunk, end="", flush=True)
    else:
        print(f"[DEBUG] 不在 IPython 环境中", file=sys.stderr)
        print(chunk, end="", flush=True)
```

然后在 IPython 控制台中查看 stderr 输出。

## 常见问题

### Q1: agent 对象不存在

**解决**: 确保在 `ipython_console_tab.py` 中正确调用了 `_inject_llm_agent_api()`

### Q2: 有输出但看不到

可能是输出到了错误的流。检查：
- stdout vs stderr
- IPython 的前后端通信

### Q3: Qt 线程问题

确保输出在主线程中执行。目前通过 Qt 信号机制保证。

## 备选方案

如果以上都不工作，可以使用最简单的方案：

```python
def _on_chunk_received(self, chunk: str):
    # 最简单的方式：直接打印
    # Qt 应该会捕获这个输出并显示在控制台中
    print(chunk, end="", flush=True)
```

因为 PySide6 的 IPython 控制台会重定向标准输出，所以简单的 `print()` 也应该工作。

## 验证清单

- [ ] agent 对象成功注入到 IPython 命名空间
- [ ] agent.ipython_shell 引用存在
- [ ] _on_chunk_received 被调用（可以通过日志验证）
- [ ] sys.stdout.write() 被调用
- [ ] IPython 控制台能正常显示普通 print 输出

## 联系支持

如果问题仍未解决，请提供以下信息：
1. IPython 版本：`import IPython; print(IPython.__version__)`
2. qtconsole 版本：`import qtconsole; print(qtconsole.__version__)`
3. PySide6 版本：`import PySide6; print(PySide6.__version__)`
4. 完整的错误信息或调试输出
