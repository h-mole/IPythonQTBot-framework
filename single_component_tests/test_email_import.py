"""测试导入是否成功"""
import sys
sys.path.insert(0, r'C:\Users\hzy\Programs\IPythonQTBot')

try:
    from plugins.email_utils import EmailManagerTab, load_plugin, unload_plugin
    print("✓ 导入成功")
    
    # 检查新的 Worker 类是否存在
    from plugins.email_utils.main import (
        EmailFetchWorker,
        EmailDetailWorker,
        DownloadAttachmentWorker,
        SendEmailWorker
    )
    print("✓ Worker 类导入成功")
    
    # 检查信号槽机制
    assert hasattr(EmailFetchWorker, 'emails_fetched'), "缺少 emails_fetched 信号"
    assert hasattr(EmailDetailWorker, 'detail_fetched'), "缺少 detail_fetched 信号"
    assert hasattr(DownloadAttachmentWorker, 'download_completed'), "缺少 download_completed 信号"
    assert hasattr(SendEmailWorker, 'send_completed'), "缺少 send_completed 信号"
    print("✓ 所有 Worker 都有正确的信号")
    
    print("\n✓ 所有测试通过！")
    
except Exception as e:
    print(f"✗ 导入失败：{e}")
    import traceback
    traceback.print_exc()
