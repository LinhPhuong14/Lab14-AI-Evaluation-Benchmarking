import asyncio
import json
import os
import time
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# gpt-4o-mini estimated blended cost (input+output) per token
COST_PER_TOKEN_USD = 0.30 / 1_000_000


class RetrievalMetricsEvaluator:
    """Wraps RetrievalEvaluator to match the BenchmarkRunner.evaluator.score() interface."""

    def __init__(self, top_k: int = 3):
        self.top_k = top_k
        self.retrieval = RetrievalEvaluator()

    async def score(self, case, resp):
        expected_ids = self.retrieval._extract_expected_ids(case)
        retrieved_ids = self.retrieval._extract_retrieved_ids(case, resp)
        hit = self.retrieval.calculate_hit_rate(expected_ids, retrieved_ids, top_k=self.top_k)
        mrr = self.retrieval.calculate_mrr(expected_ids, retrieved_ids)
        return {
            "faithfulness": None,
            "relevancy": None,
            "retrieval": {"hit_rate": hit, "mrr": mrr},
        }


async def run_benchmark_with_results(agent_version: str, optimized: bool):
    print(f"\n[RUN] Starting benchmark for {agent_version} (optimized={optimized})...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("[FAIL] Missing data/golden_set.jsonl.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("[FAIL] data/golden_set.jsonl is empty.")
        return None, None

    runner = BenchmarkRunner(
        MainAgent(optimized=optimized, top_k=3),
        RetrievalMetricsEvaluator(top_k=3),
        LLMJudge(),
    )

    start = time.perf_counter()
    results = await runner.run_all(dataset)
    elapsed = time.perf_counter() - start
    print(f"  Completed in {elapsed:.1f}s ({len(results)} cases)")

    total = len(results)
    avg_hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
    avg_mrr = sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total
    total_tokens = sum(r.get("tokens_used", 0) for r in results)
    estimated_cost_usd = round(total_tokens * COST_PER_TOKEN_USD, 6)

    summary = {
        "metadata": {
            "version": agent_version,
            "total": total,
            "elapsed_seconds": round(elapsed, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
        "metrics": {
            "avg_score": round(sum(r["judge"]["final_score"] for r in results) / total, 4),
            "hit_rate": round(avg_hit_rate, 4),
            "avg_hit_rate": round(avg_hit_rate, 4),
            "avg_mrr": round(avg_mrr, 4),
            "agreement_rate": round(
                sum(r["judge"]["agreement_rate"] for r in results) / total, 4
            ),
        },
        "cost": {
            "total_tokens": total_tokens,
            "estimated_cost_usd": estimated_cost_usd,
        },
    }
    return results, summary


async def run_benchmark(version: str, optimized: bool):
    _, summary = await run_benchmark_with_results(version, optimized=optimized)
    return summary


async def main():
    v1_summary = await run_benchmark("Agent_V1_Base", optimized=False)
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized", optimized=True)

    if not v1_summary or not v2_summary:
        print(f"{RED}[FAIL] Cannot run benchmark. Check data/golden_set.jsonl.{RESET}")
        return

    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]

    print("\n" + "=" * 50)
    print("  REGRESSION COMPARISON")
    print("=" * 50)
    print(f"  V1 Avg Score  : {v1_summary['metrics']['avg_score']:.4f}")
    print(f"  V2 Avg Score  : {v2_summary['metrics']['avg_score']:.4f}")
    print(f"  Delta         : {'+' if delta >= 0 else ''}{delta:.4f}")
    print(f"  Agreement Rate: {v2_summary['metrics']['agreement_rate'] * 100:.1f}%")
    print(f"  V1 Retrieval  : hit@3={v1_summary['metrics']['avg_hit_rate']:.4f}  mrr={v1_summary['metrics']['avg_mrr']:.4f}")
    print(f"  V2 Retrieval  : hit@3={v2_summary['metrics']['avg_hit_rate']:.4f}  mrr={v2_summary['metrics']['avg_mrr']:.4f}")
    print(f"  Total Tokens  : {v2_summary['cost']['total_tokens']:,}")
    print(f"  Est. Cost     : ${v2_summary['cost']['estimated_cost_usd']:.6f} USD")
    print("=" * 50)

    # Regression Release Gate
    if delta > 0:
        print(f"\n{GREEN}✅ RELEASE APPROVED  — V2 outperforms V1 by {delta:+.4f}{RESET}")
    else:
        print(f"\n{RED}🚨 ROLLBACK TRIGGERED — V2 did not improve over V1 (delta={delta:+.4f}){RESET}")

    # Persist reports
    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    print(f"\n{YELLOW}Reports saved → reports/summary.json  |  reports/benchmark_results.json{RESET}")


if __name__ == "__main__":
    asyncio.run(main())
