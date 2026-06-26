"""
TradingAgents-CN 本地测试脚本 —— 使用 DeepSeek 分析股票
不需要 Docker, MongoDB, Redis
"""
import os
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量（DeepSeek API Key等）
load_dotenv()

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# 检查 API Key
key = os.getenv("DEEPSEEK_API_KEY")
print(f"🔑 DeepSeek API Key: {key[:15]}...{key[-4:]}" if key and len(key) > 20 else "❌ API Key 未配置!")

# 配置：使用 DeepSeek
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"
config["backend_url"] = "https://api.deepseek.com"
config["deep_think_llm"] = "deepseek-chat"
config["quick_think_llm"] = "deepseek-chat"
config["max_debate_rounds"] = 1
config["online_tools"] = True

# 初始化交易智能体
print("🚀 正在初始化 TradingAgents...")
ta = TradingAgentsGraph(debug=True, config=config)

# 分析股票：贵州茅台
print("\n📊 开始分析贵州茅台 (600519)...")
_, decision = ta.propagate("600519", "2026-06-24")
print(f"\n📋 分析结果:\n{decision}")
