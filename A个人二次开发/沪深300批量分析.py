"""
沪深300 批量分析 — 从Excel读取成分股，并发AI分析
用法: python 沪深300批量分析.py --workers 5
断点续跑: python 沪深300批量分析.py --workers 5 --resume
"""
import os, sys, json, time, hashlib, signal, argparse, pandas as pd
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeout
from dotenv import load_dotenv
load_dotenv()

BASE = Path(__file__).parent
RES_DIR = BASE / "results" / "screening"
RES_DIR.mkdir(parents=True, exist_ok=True)

DEPTH_MAP = {
    1: (1, 1), 2: (1, 1), 3: (1, 2), 4: (2, 2), 5: (3, 3)
}

_stop = False
def _h(s, f): signal.signal(s, f)
_h(signal.SIGINT, lambda s,f: (setattr(sys.modules[__name__], '_stop', True), print("\n⏸️ 中断...")))

def _ck(c, d): return hashlib.md5(f"{c}_{d}".encode()).hexdigest()[:12]
def _load():
    f = RES_DIR / "_cache_hs300.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
def _save(c): (RES_DIR / "_cache_hs300.json").write_text(json.dumps(c, ensure_ascii=False, indent=2), encoding="utf-8")

def load_excel(path: str) -> list:
    """从Excel读取股票列表，自动补零"""
    df = pd.read_excel(path)
    codes = df.iloc[:,0].astype(str).str.zfill(6).tolist()  # 补零到6位
    names = df.iloc[:,1].astype(str).tolist()
    return [{"code": c, "name": n} for c, n in zip(codes, names)]

def analyze_one(stock, config, idx, total):
    global _stop
    code, name = stock["code"], stock["name"]
    dt = config["date"]
    ck = _ck(code, dt)

    if not config.get("no_cache"):
        cache = _load()
        if ck in cache:
            r = cache[ck]; r["_cached"] = True; return r

    debates, risks = config["depth_tuple"]
    print(f"\n[{idx}/{total}] 🔍 {name}({code}) 深度{config['depth']} (辩论{debates}/风控{risks})")

    try:
        from tradingagents.graph.trading_graph import TradingAgentsGraph
        from tradingagents.default_config import DEFAULT_CONFIG

        cfg = DEFAULT_CONFIG.copy()
        cfg.update({
            "llm_provider": "deepseek", "backend_url": "https://api.deepseek.com",
            "deep_think_llm": config["model"], "quick_think_llm": config["model"],
            "max_debate_rounds": debates, "max_risk_discuss_rounds": risks,
            "online_tools": True,
        })

        ta = TradingAgentsGraph(
            debug=True, config=cfg,
            selected_analysts=config.get("analysts", ["market", "fundamentals", "news"])
        )
        _, decision = ta.propagate(code, dt)

        r = {
            "code": code, "name": name, "date": dt,
            "action": decision.get("action", "?"),
            "target_price": decision.get("target_price", 0),
            "confidence": decision.get("confidence", 0),
            "risk_score": decision.get("risk_score", 0),
            "reasoning": decision.get("reasoning", ""),
            "timestamp": datetime.now().isoformat(), "_cached": False,
        }
        r["score"] = round(r["confidence"] * (1 - r.get("risk_score", 0.5)), 3)

        icon = {"买入":"🟢","持有":"🟡","卖出":"🔴"}.get(r["action"],"❓")
        print(f"  {icon} {r['action']} | 目标¥{r['target_price']} | 置信{r['confidence']:.0%} | 风险{r['risk_score']:.0%} | 得分{r['score']:.3f}")

        cache = _load(); cache[ck] = r; _save(cache)
        return r
    except Exception as e:
        print(f"  ❌ 失败: {e}")
        return {"code": code, "name": name, "action": "错误", "score": 0, "reasoning": str(e), "confidence": 0, "risk_score": 1.0}

def main():
    global _stop
    p = argparse.ArgumentParser()
    p.add_argument("--excel", default="300+500+1000/沪深300成分股列表.xlsx")
    p.add_argument("--workers", type=int, default=5)
    p.add_argument("--depth", type=int, default=5, choices=[1,2,3,4,5])
    p.add_argument("--analysts", default="market,fundamentals,news")
    p.add_argument("--model", default="deepseek-chat")
    p.add_argument("--date", default="2026-06-24")
    p.add_argument("--max", type=int, default=0)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--no-cache", action="store_true")
    args = p.parse_args()

    debates, risks = DEPTH_MAP[args.depth]
    analysts = [a.strip() for a in args.analysts.split(",")]

    print("="*70)
    print("  沪深300 批量AI分析")
    print(f"  日期:{args.date} | 深度:{args.depth}(辩论{debates}/风控{risks})")
    print(f"  分析师:{analysts} | 并发:{args.workers}")
    print("="*70)

    stocks = load_excel(args.excel)
    print(f"\n📋 Excel读取: {len(stocks)}只")
    if args.max > 0: stocks = stocks[:args.max]

    cache = _load() if args.resume else {}
    pending, results = [], []
    for i, s in enumerate(stocks):
        if not args.no_cache and _ck(s["code"], args.date) in cache:
            rr = cache[_ck(s["code"], args.date)]
            rr["_cached"] = True
            results.append(rr)
        else:
            pending.append((s, i+1))

    n = len(stocks)
    cached = len(results)
    to_run = len(pending)

    est = to_run * 280 / args.workers / 60  # 深度5 每只~280s
    cost = to_run * 12000 * 0.002 / 1000  # DeepSeek ¥0.002/K tokens

    print(f"  待分析:{to_run}只 | 缓存命中:{cached} | ⏱️~{est:.0f}min | 💰~¥{cost:.1f}\n")

    if to_run == 0:
        print("✅ 全部命中缓存")
    else:
        config = {"date": args.date, "model": args.model, "depth": args.depth,
                  "depth_tuple": (debates, risks), "analysts": analysts,
                  "no_cache": args.no_cache}

        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {}
            for stock, idx in pending:
                if _stop: break
                futures[ex.submit(analyze_one, stock, config, idx, n)] = stock["code"]

            done = 0
            for future in as_completed(futures):
                if _stop:
                    for f in futures: f.cancel()
                    break
                code = futures[future]
                try:
                    rr = future.result(timeout=1200)
                    if rr: results.append(rr)
                    done += 1
                    print(f"  ✅ [{code}] 完成 ({done}/{to_run})")
                except FuturesTimeout:
                    print(f"  ⏰ [{code}] 超时")
                except Exception as e:
                    print(f"  ❌ [{code}] {e}")

    # 排名
    order = {"买入":0, "持有":1, "卖出":2, "错误":3}
    results.sort(key=lambda r: (order.get(r.get("action","错误"),3), -r.get("score",0)))

    buys = [r for r in results if r["action"]=="买入"]
    holds = [r for r in results if r["action"]=="持有"]
    sells = [r for r in results if r["action"]=="卖出"]

    print(f"\n{'='*70}")
    print(f"  📊 沪深300 分析报告")
    print(f"{'='*70}")
    print(f"  总:{len(results)} | 🟢买:{len(buys)} | 🟡持:{len(holds)} | 🔴卖:{len(sells)}")

    if buys:
        print(f"\n🟢 买入推荐:")
        for r in buys[:30]:
            print(f"  {r['code']} {r['name']:<10} 得分{r['score']:.3f} 目标¥{r['target_price']} 置信{r['confidence']:.0%}")
    else:
        print(f"\n💡 无买入信号")

    # 导出
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    jp = RES_DIR / f"hs300_depth{args.depth}_{ts}.json"
    clean = [{k:v for k,v in r.items() if not k.startswith("_")} for r in results]
    jp.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n📁 {jp}")

if __name__ == "__main__":
    main()
