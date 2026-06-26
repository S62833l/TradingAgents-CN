"""
从Excel读取沪深300 → 调用网页API批量提交 → 任务中心可见
用法: python 网页批量提交.py
"""
import pandas as pd
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://localhost:8000"
EXCEL_PATH = "300+500+1000/沪深300成分股列表.xlsx"

# 1. 读取股票列表
df = pd.read_excel(EXCEL_PATH)
codes = df.iloc[:, 0].astype(str).str.zfill(6).tolist()
names = df.iloc[:, 1].astype(str).tolist()
print(f"📋 读取 {len(codes)} 只股票")

# 2. 登录获取 token
print("🔐 登录...")
resp = requests.post(f"{BASE_URL}/api/auth/login", json={
    "username": "admin",
    "password": "admin123"
})
if resp.status_code != 200:
    print(f"❌ 登录失败: {resp.status_code} {resp.text}")
    exit(1)

token = resp.json()["data"]["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ 登录成功")

# 3. 分批提交（每批10只，避免超时）
BATCH_SIZE = 10
total = len(codes)
submitted = 0

for i in range(0, total, BATCH_SIZE):
    batch_codes = codes[i:i+BATCH_SIZE]
    batch_names = names[i:i+BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1
    total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

    print(f"\n📤 提交第 {batch_num}/{total_batches} 批 ({len(batch_codes)}只)...", end=" ")

    try:
        resp = requests.post(
            f"{BASE_URL}/api/analysis/batch",
            json={
                "title": f"沪深300_第{batch_num}批_{batch_codes[0]}_{batch_codes[-1]}",
                "symbols": batch_codes,
                "parameters": {
                    "research_depth": 5,
                    "selected_analysts": ["market", "fundamentals", "news"],
                    "quick_model": "deepseek-chat",
                    "deep_model": "deepseek-chat"
                }
            },
            headers=headers,
            timeout=60
        )

        if resp.status_code == 200:
            data = resp.json()
            task_count = len(data.get("task_ids", []))
            submitted += task_count
            print(f"✅ {task_count}个任务")
        else:
            print(f"❌ HTTP {resp.status_code}: {resp.text[:100]}")

    except Exception as e:
        print(f"❌ 异常: {e}")

    time.sleep(2)  # 避免请求过快

print(f"\n{'='*50}")
print(f"✅ 提交完成！共 {submitted}/{total} 只")
print(f"   去 http://localhost:3000 → 任务中心 查看")
print(f"{'='*50}")
