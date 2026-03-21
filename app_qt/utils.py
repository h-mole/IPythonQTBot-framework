import asyncio
import threading
import concurrent.futures
from typing import Callable

def wrap_async_in_sync(async_func:Callable, tool_name: str):
    def wrap_func(*args, **kwargs):
        # 1. 获取协程对象（注意：这里不要加 await，只是创建对象）
        coro = async_func(*args, **kwargs)
        
        try:
            # 2. 尝试获取当前正在运行的事件循环
            # 如果当前线程没有运行中的循环，会抛出 RuntimeError
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # === 情况 A: 当前没有运行中的 EventLoop ===
            # 这是最简单的情况，我们可以创建一个新的临时循环来运行任务。
            # asyncio.run() 会自动创建循环、运行任务、关闭循环。
            try:
                return asyncio.run(coro)
            except RuntimeError as e:
                # 防止极少数情况下 asyncio.run 嵌套调用的报错
                # 如果 asyncio.run 失败，尝试手动管理（兼容性处理）
                if "asyncio.run() cannot be called from a running event loop" in str(e):
                     # 这种情况通常不应该发生，因为上面已经捕获了 get_running_loop 的错误
                     # 但作为防御性编程，如果发生，尝试回退方案
                     loop = asyncio.new_event_loop()
                     asyncio.set_event_loop(loop)
                     return loop.run_until_complete(coro)
                raise e
        else:
            # === 情况 B: 当前已有运行中的 EventLoop ===
            # 这意味着调用者处于一个异步上下文中。
            
            # 检查当前线程是否就是运行该 Loop 的线程
            # 注意：loop._thread_id 是内部属性，但在标准库中广泛使用
            if hasattr(loop, '_thread_id') and loop._thread_id == threading.get_ident():
                # === 情况 B-1: 同一线程（死锁风险） ===
                # 当前线程正在运行 EventLoop，如果我们在此阻塞等待结果，
                # EventLoop 就无法继续执行，导致永远等不到结果（死锁）。
                
                # 解决方案：
                # 方案一（推荐）：抛出异常，强制用户使用 await。
                raise RuntimeError(
                    f"Attempted to call tool '{tool_name}' synchronously from an async context. "
                    "This would cause a deadlock. Please use 'await' to call this tool asynchronously."
                )
                
                # 方案二（高级）：如果用户安装了 nest_asyncio 库，可以支持这种用法。
                # 但作为通用库，不建议假设用户环境，因此推荐方案一。
                # import nest_asyncio
                # nest_asyncio.apply()
                # return loop.run_until_complete(coro)
            else:
                # === 情况 B-2: 不同线程 ===
                # EventLoop 在主线程运行，而 wrap_func 在工作线程中被调用。
                # 我们需要将任务安全地提交给 EventLoop 所在的线程执行。
                
                # 使用 run_coroutine_threadsafe 将协程提交到运行中的 Loop
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                
                # 阻塞当前线程等待结果（可以设置 timeout 防止永久挂起）
                try:
                    # 建议设置超时时间，防止工具卡死导致调用线程永久阻塞
                    return future.result(timeout=60) 
                except concurrent.futures.TimeoutError:
                    future.cancel()
                    raise TimeoutError(f"Tool '{tool_name}' execution timed out.")
                    
    return wrap_func

import asyncio
import threading
from typing import Coroutine, Any

class AsyncThreadRunner:
    """
    一个在独立线程中维护 EventLoop 的工具类。
    支持：从外部提交异步任务并等待结果。
    """
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        # 将当前线程的事件循环设置为我们创建的循环
        asyncio.set_event_loop(self.loop)
        # 持续运行循环，直到被停止
        self.loop.run_forever()

    def submit(self, coro: Coroutine) -> Any:
        """
        在该线程的 EventLoop 中提交并运行一个异步函数，
        并阻塞当前调用线程直到获得结果。
        """
        # 将协程放入线程内部的 Loop 中运行，并返回一个 Future
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        # 阻塞等待结果（可以设置 timeout 防止死锁）
        return future.result()

    def stop(self):
        """停止事件循环和线程"""
        self.loop.call_soon_threadsafe(self.loop.stop)

# --- 使用示例 ---

async def my_async_task(name, delay):
    print(f"任务 {name} 开始，等待 {delay} 秒... (线程ID: {threading.get_ident()})")
    await asyncio.sleep(delay)
    print(f"任务 {name} 结束")
    return f"结果是 {name}"

# # 场景：在主线程（同步环境）中调用
# runner = AsyncThreadRunner()

# # 提交任务并获取返回值
# result = runner.submit(my_async_task("A", 1))
# print(f"主线程收到: {result}")

# runner.stop()
