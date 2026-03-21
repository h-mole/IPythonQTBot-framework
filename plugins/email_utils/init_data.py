"""
初始化邮箱工具插件的配置
创建默认配置文件示例
"""

import os
import json

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CONFIG_FILE = os.path.join(DATA_DIR, "email_accounts.json")


def init_config():
    """初始化配置文件"""
    # 确保目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # 创建示例配置
    example_config = {
        "accounts": [
            {
                "name": "示例邮箱",
                "username": "your_email@example.com",
                "password": "your_password_or_app_token",
                "imap_server": "imap.example.com",
                "imap_port": 993,
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "use_ssl": True
            }
        ]
    }
    
    # 如果配置文件不存在，创建示例配置
    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(example_config, f, ensure_ascii=False, indent=4)
        print(f"✓ 已创建示例配置文件：{CONFIG_FILE}")
        print("⚠ 请编辑此文件，填入您的真实邮箱账号信息")
    else:
        print(f"ℹ 配置文件已存在：{CONFIG_FILE}")
        print("  如需重置，请先删除此文件")


if __name__ == "__main__":
    init_config()
    print("\n初始化完成！")
    print("\n常见邮箱服务器配置参考:")
    print("-" * 60)
    print("Gmail:")
    print("  IMAP: imap.gmail.com:993 (SSL)")
    print("  SMTP: smtp.gmail.com:587 (TLS)")
    print("  注意：需要使用应用专用密码")
    print("\n163 邮箱:")
    print("  IMAP: imap.163.com:993 (SSL)")
    print("  SMTP: smtp.163.com:465 (SSL)")
    print("  注意：需要使用客户端授权码")
    print("\nQQ 邮箱:")
    print("  IMAP: imap.qq.com:993 (SSL)")
    print("  SMTP: smtp.qq.com:465 (SSL)")
    print("  注意：需要开启 IMAP/SMTP 服务并获取授权码")
    print("\nOutlook/Hotmail:")
    print("  IMAP: outlook.office365.com:993 (SSL)")
    print("  SMTP: smtp.office365.com:587 (STARTTLS)")
    print("-" * 60)
