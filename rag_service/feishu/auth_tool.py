"""
Feishu OAuth Authorization Tool
用法:
1. 运行 python -m feishu.auth_tool 获取授权 URL
2. 浏览器打开 URL，扫码授权
3. 授权后会跳转到 localhost，浏览器地址栏会有 code 参数
4. 复制 code，运行 python -m feishu.auth_tool --code <CODE>
5. Token 会保存到 .feishu_token 文件
"""
import os
import sys
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

TOKEN_FILE = Path.home() / ".feishu_token"


def get_authorization_url():
    """Generate OAuth URL and print instructions"""
    from feishu.oauth import get_oauth

    oauth = get_oauth()
    url = oauth.get_authorization_url()

    print("=" * 60)
    print("Step 1: 打开以下 URL 进行授权")
    print("=" * 60)
    print(url)
    print()
    print("=" * 60)
    print("Step 2: 授权后，浏览器会跳转到 localhost")
    print("        复制浏览器地址栏中的 code 参数值")
    print("        然后运行:")
    print("        python -m feishu.auth_tool --code <这里粘贴CODE>")
    print("=" * 60)


def exchange_code(code: str):
    """Exchange authorization code for token"""
    from feishu.oauth import get_oauth

    oauth = get_oauth()
    token_data = oauth.exchange_code_for_token(code)

    # Save token
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"Token 已保存到: {TOKEN_FILE}")
    print(f"access_token: {token_data.get('access_token', '')[:30]}...")
    print(f"expires_in: {token_data.get('expires_in')} 秒")


def load_saved_token():
    """Load saved token from file"""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None


def test_connection():
    """Test if saved token works"""
    token_data = load_saved_token()
    if not token_data:
        print("没有保存的 token，请先授权")
        print("运行: python -m feishu.auth_tool")
        return

    from feishu.user_client import set_user_token

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    set_user_token(access_token, refresh_token)

    # Test by listing files
    from feishu.user_client import get_user_client

    client = get_user_client()
    try:
        data = client.list_my_drive_files()
        files = data.get("files", [])
        print(f"连接成功！你的云盘根目录有 {len(files)} 个文件/文件夹")
        for f in files[:5]:
            print(f"  - [{f.get('type')}] {f.get('name')}")
        if len(files) > 5:
            print(f"  ... 还有 {len(files) - 5} 个文件")
    except Exception as e:
        print(f"连接失败: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Feishu OAuth 授权工具")
    parser.add_argument("--code", type=str, help="授权码（从回调 URL 中获取）")
    parser.add_argument("--test", action="store_true", help="测试已保存的 token")

    args = parser.parse_args()

    if args.test:
        test_connection()
    elif args.code:
        exchange_code(args.code)
    else:
        get_authorization_url()
