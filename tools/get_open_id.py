"""获取你的飞书 open_id 的小工具"""
import os
import requests

APP_ID = os.getenv("FEISHU_APP_ID") or input("请输入 app_id: ").strip()
APP_SECRET = os.getenv("FEISHU_APP_SECRET") or input("请输入 app_secret: ").strip()
IDENTIFIER = input("请输入你的飞书手机号或邮箱: ").strip()

# 1. 获取 token
resp = requests.post(
    "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
    json={"app_id": APP_ID, "app_secret": APP_SECRET},
)
token = resp.json().get("tenant_access_token")
if not token:
    print(f"获取 token 失败: {resp.json()}")
    exit(1)
print(f"✅ token 获取成功")

# 2. 判断输入是手机号还是邮箱
if "@" in IDENTIFIER:
    id_type, id_value = "email", IDENTIFIER
else:
    id_type, id_value = "mobile", IDENTIFIER

# 3. 批量获取用户 ID
resp = requests.post(
    "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    params={"user_id_type": "open_id"},
    json={f"{id_type}s": [id_value]},
)
data = resp.json()
if data.get("code") != 0:
    print(f"查询失败: {data.get('msg', '')}")
    print(f"完整响应: {data}")
    exit(1)

user_list = data.get("data", {}).get("user_list", [])
if user_list and user_list[0].get("user_id"):
    open_id = user_list[0]["user_id"]
    print(f"\n🎉 你的 open_id 是: {open_id}")
    print(f"\n请将此值填入 .env 文件的 FEISHU_RECEIVE_ID 字段")
else:
    print(f"未找到用户，请确认手机号/邮箱是否正确")
    print(f"完整响应: {data}")
