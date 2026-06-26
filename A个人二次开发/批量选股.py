"""
TradingAgents-CN 批量选股工具 v2.0
─────────────────────────────────────
无限量并发分析 + 断点续跑 + 自动排名 + 结果导出

用法:
  python 批量选股.py --pool hs300 --workers 5 --depth 5     # 沪深300，深度5
  python 批量选股.py --pool csi500 --max 50 --workers 3     # 中证500前50
  python 批量选股.py --pool 600519,000858 --workers 2        # 自定义池
  python 批量选股.py --excel 300+500+1000/沪深300成分股列表.xlsx  # Excel文件
  python 批量选股.py --resume                               # 从上次中断处继续
  python 批量选股.py --export-only                           # 只看已跑完的结果汇总

股票池选项:
  csi500 / zz500  → 中证500 (500只)
  hs300 / hs300   → 沪深300 (300只)
  csi1000 / zz1000 → 中证1000 (1000只)
  逗号分隔代码      → 自定义池

输出:
  results/screening/screening_YYYYMMDD_HHMMSS.json  完整结果
  results/screening/screening_YYYYMMDD_HHMMSS.csv   CSV表格
  results/screening/_cache.json                     断点续跑缓存
"""
import os
import sys
import json
import time
import hashlib
import signal
import argparse
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results" / "screening"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# 全局停止标志（Ctrl+C 优雅退出）
_stop_requested = False

def signal_handler(sig, frame):
    global _stop_requested
    print("\n⏸️  收到中断信号，当前正在跑的会完成，新的不再启动...")
    _stop_requested = True

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ─── 1. 股票池 ────────────────────────────────────

INDEX_MAP = {
    "csi500":  ("000905", "中证500"),
    "zz500":   ("000905", "中证500"),
    "hs300":   ("000300", "沪深300"),
    "csi300":  ("000300", "沪深300"),
    "csi1000": ("000852", "中证1000"),
    "zz1000":  ("000852", "中证1000"),
}

def get_index_stocks(index_key: str) -> List[dict]:
    """从 AKShare 获取指数成分股"""
    if index_key not in INDEX_MAP:
        print(f"❌ 未知指数: {index_key}，可选: {list(INDEX_MAP.keys())}")
        return []

    code, name = INDEX_MAP[index_key]
    print(f"📡 正在获取 {name}({code}) 成分股...")
    try:
        import akshare as ak
        df = ak.index_stock_cons_csindex(symbol=code)
        stocks = []
        for _, row in df.iterrows():
            c = str(row["成分券代码"])
            if len(c) < 6:
                c = c.zfill(6)
            stocks.append({"code": c, "name": str(row["成分券名称"])})
        print(f"✅ {name}: {len(stocks)} 只成分股")
        return stocks
    except Exception as e:
        print(f"❌ 获取失败: {e}")
        return []

def get_custom_stocks(codes_str: str) -> List[dict]:
    """自定义股票代码"""
    codes = [c.strip() for c in codes_str.replace("，", ",").split(",") if c.strip()]
    return [{"code": c, "name": c} for c in codes]

# ─── 2. 缓存（断点续跑） ──────────────────────────

def _cache_key(code: str, date: str) -> str:
    return hashlib.md5(f"{code}_{date}".encode()).hexdigest()[:12]

def load_cache() -> dict:
    f = RESULTS_DIR / "_cache.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except:
            pass
    return {}

def save_cache(cache: dict):
    (RESULTS_DIR / "_cache.json").write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

# ─── 3. 单只分析 ──────────────────────────────────

def analyze_one(stock: dict, config: dict, stock_index: int, total: int) -> Optional[dict]:
    """分析单只股票（在子线程中运行）"""
    global _stop_requested

    code = stock["code"]
    name = stock.get("name", code)
    analysis_date = config["date"]

    # 缓存命中直接返回
    ck = _cache_key(code, analysis_date)
    if config.get("use_cache"):
        cache = load_cache()
        if ck in cache:
            cached = cache[ck]
            cached["_cached"] = True
            return cached

    print(f"\n{'─'*50}")
    print(f"[{stock_index}/{total}] 🔍 {name}({code}) 开始...")
    t0 = time.time()

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        cfg = DEFAULT_CONFIG.copy()
        cfg["llm_provider"] = config["llm_provider"]
        cfg["backend_url"] = config["backend_url"]
        cfg["deep_think_llm"] = config["model"]
        cfg["quick_think_llm"] = config["model"]
        cfg["max_debate_rounds"] = config.get("max_debate_rounds", 1)
        cfg["online_tools"] = config.get("online_tools", True)

        ta = TradingAgentsGraph(debug=True, config=cfg)
        _, decision = ta.propagate(code, analysis_date)

        elapsed = time.time() - t0
        result = {
            "code": code, "name": name, "date": analysis_date,
            "action": decision.get("action", "未知"),
            "target_price": decision.get("target_price", 0),
            "confidence": decision.get("confidence", 0),
            "risk_score": decision.get("risk_score", 0),
            "reasoning": decision.get("reasoning", ""),
            "elapsed_seconds": round(elapsed, 1),
            "timestamp": datetime.now().isoformat(),
            "_cached": False,
        }

        # 得分
        result["score"] = round(result["confidence"] * (1 - result.get("risk_score", 0.5)), 3)

        icon = {"买入": "🟢", "持有": "🟡", "卖出": "🔴"}.get(result["action"], "❓")
        print(f"  {icon} [{name}] {result['action']} | 目标 ¥{result['target_price']} | "
              f"置信 {result['confidence']:.0%} | 风险 {result['risk_score']:.0%} | "
              f"耗时 {elapsed:.0f}s | 得分 {result['score']:.3f}")

        # 更新缓存
        cache = load_cache()
        cache[ck] = result
        save_cache(cache)

        return result

    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ❌ [{name}] 失败 ({elapsed:.0f}s): {e}")
        # 不缓存错误结果
        return {
            "code": code, "name": name, "date": analysis_date,
            "action": "错误", "target_price": 0, "confidence": 0,
            "risk_score": 1.0, "reasoning": str(e),
            "elapsed_seconds": round(elapsed, 1), "score": 0,
            "timestamp": datetime.now().isoformat(), "_cached": False,
        }


# ─── 4. 排名 & 筛选 ──────────────────────────────

def rank_and_filter(results: List[dict]) -> List[dict]:
    """按综合得分排序"""
    for r in results:
        if "score" not in r:
            c = r.get("confidence", 0) or 0
            r["score"] = round(c * (1 - (r.get("risk_score", 0.5) or 0.5)), 3)

    order = {"买入": 0, "持有": 1, "卖出": 2, "错误": 3}
    results.sort(key=lambda r: (order.get(r.get("action", "错误"), 3), -r.get("score", 0)))
    return results

# ─── 5. 输出 ──────────────────────────────────────

def print_report(results: List[dict], config: dict):
    """打印汇总报告"""
    buys   = [r for r in results if r["action"] == "买入"]
    holds  = [r for r in results if r["action"] == "持有"]
    sells  = [r for r in results if r["action"] == "卖出"]
    errors = [r for r in results if r["action"] == "错误"]
    cached = [r for r in results if r.get("_cached")]

    avg_time = sum(r.get("elapsed_seconds", 0) for r in results) / max(len(results), 1)

    print(f"\n{'='*80}")
    print(f"  📊 TradingAgents-CN 批量选股报告")
    print(f"  日期: {config['date']} | 模型: {config['model']} | 并发: {config.get('workers',1)}")
    print(f"{'='*80}")
    print(f"  总分析: {len(results)} | 🟢买入:{len(buys)} | 🟡持有:{len(holds)} | "
          f"🔴卖出:{len(sells)} | ❌错误:{len(errors)} | 💾缓存命中:{len(cached)}")
    print(f"  平均耗时: {avg_time:.0f}s/只 | 总Token约: {len(results)*8000:,}")
    print(f"{'='*80}")

    # 买入推荐
    if buys:
        print(f"\n{'='*80}")
        print(f"  🟢 推荐买入（{len(buys)}只）—— 综合得分排序")
        print(f"{'='*80}")
        print(f"  {'排名':<4} {'代码':<8} {'名称':<10} {'得分':>6} {'置信度':>6} {'风险':>6} {'目标价':>8}  核心理由")
        print(f"  {'─'*76}")
        for i, r in enumerate(buys[:30], 1):
            reason = (r.get("reasoning", "") or "")[:55].replace("\n", " ")
            print(f"  {i:<4} {r['code']:<8} {r['name']:<10} {r['score']:>6.3f} "
                  f"{r['confidence']:>5.0%} {r['risk_score']:>5.0%} "
                  f"¥{r['target_price']:>7.2f}  {reason}")

    # 持有
    if holds:
        print(f"\n  🟡 建议持有（{len(holds)}只）:")
        for r in holds[:10]:
            print(f"     {r['code']} {r['name']:<10} 得分={r['score']:.3f}  "
                  f"置信={r['confidence']:.0%} 风险={r['risk_score']:.0%}")

    # 卖出
    if sells:
        print(f"\n  🔴 建议卖出（{len(sells)}只）")
        print(f"     （前10只）")
        for r in sells[:10]:
            print(f"     {r['code']} {r['name']:<10} 得分={r['score']:.3f}  "
                  f"置信={r['confidence']:.0%} 风险={r['risk_score']:.0%}")

    # 错误
    if errors:
        print(f"\n  ❌ 分析失败（{len(errors)}只）")
        for r in errors[:5]:
            reason = (r.get("reasoning", "") or "")[:60]
            print(f"     {r['code']} {r['name']:<10} {reason}")

def export_results(results: List[dict], config: dict):
    """导出 JSON + CSV"""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    label = config.get("pool_label", "custom")[:10]
    prefix = f"screening_{label}_{ts}"

    json_path = RESULTS_DIR / f"{prefix}.json"
    csv_path  = RESULTS_DIR / f"{prefix}.csv"

    # JSON
    clean = []
    for r in results:
        rr = {k: v for k, v in r.items() if not k.startswith("_")}
        clean.append(rr)
    json_path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")

    # CSV
    with open(csv_path, "w", encoding="utf-8-sig") as f:
        f.write("排名,代码,名称,决策,目标价,置信度,风险评分,综合得分,耗时秒,日期,核心理由\n")
        for i, r in enumerate(results, 1):
            val = lambda key: str(r.get(key, "")).replace(",", "，").replace('"', "'")
            f.write(f'{i},{val("code")},{val("name")},{val("action")},'
                    f'{val("target_price")},{val("confidence")},{val("risk_score")},'
                    f'{val("score")},{val("elapsed_seconds")},{val("date")},"{val("reasoning")[:200]}"\n')

    print(f"\n📁 结果已导出:")
    print(f"   JSON: {json_path}")
    print(f"   CSV:  {csv_path}")

# ─── 6. 主流程 ────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="TradingAgents-CN 批量选股 v2.0")
    p.add_argument("--pool", default=None,
                   help="股票池: csi500/hs300/csi1000 或 逗号分隔代码")
    p.add_argument("--max", type=int, default=0,
                   help="最多分析几只 (0=全部)")
    p.add_argument("--workers", type=int, default=3,
                   help="并发数（默认3，建议3-10）")
    p.add_argument("--model", default="deepseek-chat", help="模型名")
    p.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="分析日期")
    p.add_argument("--resume", action="store_true", help="从上次中断处继续")
    p.add_argument("--export-only", action="store_true", help="只看已有结果汇总")
    p.add_argument("--no-cache", action="store_true", help="忽略缓存，全部重新分析")
    p.add_argument("--debate-rounds", type=int, default=1, help="辩论轮数(1-3)")
    return p.parse_args()


def main():
    global _stop_requested
    args = parse_args()

    print("="*80)
    print("  TradingAgents-CN 批量选股工具 v2.0")
    print(f"  日期: {args.date} | 模型: {args.model} | 并发: {args.workers}")
    print("="*80)

    # 导出模式
    if args.export_only:
        cache = load_cache()
        results = list(cache.values())
        rank_and_filter(results)
        config = {"date": args.date, "model": args.model, "workers": 0, "pool_label": "cache"}
        print_report(results, config)
        export_results(results, config)
        return

    # 获取股票池
    if args.pool is None:
        # 交互模式
        print("\n请选择股票池:")
        print("  1. 中证500 (csi500)")
        print("  2. 沪深300 (hs300)")
        print("  3. 中证1000 (csi1000)")
        print("  4. 自定义（输入代码逗号分隔）")
        choice = input("\n请输入选项 (1/2/3/4): ").strip()
        if choice == "1":
            stocks = get_index_stocks("csi500")
            pool_label = "csi500"
        elif choice == "2":
            stocks = get_index_stocks("hs300")
            pool_label = "hs300"
        elif choice == "3":
            stocks = get_index_stocks("csi1000")
            pool_label = "csi1000"
        elif choice == "4":
            codes = input("请输入股票代码（逗号分隔）: ").strip()
            stocks = get_custom_stocks(codes)
            pool_label = "custom"
        else:
            print("无效输入，退出")
            return
    elif args.pool in INDEX_MAP:
        stocks = get_index_stocks(args.pool)
        pool_label = args.pool
    else:
        stocks = get_custom_stocks(args.pool)
        pool_label = "custom"

    if not stocks:
        print("❌ 股票池为空")
        return

    # 限制数量
    if args.max > 0 and args.max < len(stocks):
        stocks = stocks[:args.max]

    print(f"\n📋 股票池: {len(stocks)} 只")

    # 是否续跑
    cache = load_cache() if args.resume else {}
    use_cache = not args.no_cache

    # 统计缓存命中
    cached_count = 0
    if use_cache:
        for s in stocks:
            ck = _cache_key(s["code"], args.date)
            if ck in cache:
                cached_count += 1
        if cached_count > 0:
            print(f"💾 缓存命中: {cached_count}/{len(stocks)} 只（使用 --no-cache 重新跑）")

    pending = len(stocks) - (cached_count if use_cache else 0)
    if pending > 0:
        est_min = pending * 4.5 / args.workers
        print(f"⏱️  预计耗时: ~{est_min:.0f} 分钟 ({pending}只 / {args.workers}并发)")
        print(f"💰 预估Token: ~{pending * 8000:,} tokens")
        print(f"\n按 Ctrl+C 可随时停止，已完成的结果会自动保存\n")
    else:
        print("✅ 全部命中缓存，无需重新分析\n")

    config = {
        "date": args.date,
        "model": args.model,
        "llm_provider": "deepseek",
        "backend_url": "https://api.deepseek.com",
        "max_debate_rounds": args.debate_rounds,
        "online_tools": True,
        "use_cache": use_cache,
        "workers": args.workers,
        "pool_label": pool_label,
    }

    results = []
    total = len(stocks)
    completed = 0
    failed = 0

    # 并发分析
    if pending > 0:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {}
            for i, stock in enumerate(stocks):
                if _stop_requested:
                    break
                ck = _cache_key(stock["code"], args.date)
                if use_cache and ck in cache:
                    continue  # 缓存命中跳过
                future = executor.submit(
                    analyze_one, stock, config, i+1, total
                )
                futures[future] = stock

            print(f"\n{'─'*50}")
            print(f"🚀 {len(futures)} 个任务已提交，等待完成...\n")

            for future in as_completed(futures):
                if _stop_requested:
                    # 取消未开始的任务
                    for f in futures:
                        f.cancel()
                    break
                stock = futures[future]
                try:
                    result = future.result(timeout=900)  # 15分钟超时
                    if result:
                        results.append(result)
                        if result.get("action") == "错误":
                            failed += 1
                        else:
                            completed += 1
                except FuturesTimeout:
                    print(f"  ⏰ [{stock['name']}] 超时（>15分钟），跳过")
                    failed += 1
                except Exception as e:
                    print(f"  ❌ [{stock['name']}] 线程异常: {e}")
                    failed += 1

    # 合并缓存结果
    if use_cache:
        seen = {r["code"] for r in results}
        cache = load_cache()
        for stock in stocks:
            if _stop_requested:
                break
            ck = _cache_key(stock["code"], args.date)
            if stock["code"] not in seen and ck in cache:
                cached = cache[ck]
                cached["_cached"] = True
                results.append(cached)
                seen.add(stock["code"])

    # 排名 + 输出
    results = [r for r in results if r.get("action") != "错误"]
    rank_and_filter(results)

    print(f"\n✅ 完成: {completed} | ❌ 失败: {failed} | 💾 缓存: {cached_count}")
    print_report(results, config)
    export_results(results, config)

    # 最终建议
    buys = [r for r in results if r["action"] == "买入"]
    holds = [r for r in results if r["action"] == "持有"]
    if buys:
        print(f"\n💡 推荐关注 ({len(buys)}只):")
        top5 = buys[:5]
        for r in top5:
            print(f"   🟢 {r['code']} {r['name']} — 得分 {r.get('score',0):.3f} | "
                  f"目标 ¥{r['target_price']} | 置信 {r.get('confidence',0):.0%}")
    elif holds:
        print(f"\n💡 暂无强烈买入信号，可观望 ({len(holds)}只)")
    else:
        print("\n💡 当前无买入/持有信号，市场整体偏弱，建议观望")

    print(f"\n{'='*80}")
    print("  批量选股完成！可重新运行 --export-only 查看报告")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
