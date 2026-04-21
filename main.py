import asyncio
import json
import os
import time
from engine.runner import BenchmarkRunner
from agent.main_agent import MainAgent
from engine.retrieval_eval import RetrievalEvaluator
from engine.llm_judge import LLMJudge

class RetrievalMetricsEvaluator:
    """
    Evaluator that computes retrieval metrics from:
    - Ground truth: case["metadata"]["expected_retrieval_ids"]
    - Prediction: resp["retrieved_ids"]
    """

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
    print(f"[RUN] Khoi dong Benchmark cho {agent_version} (optimized={optimized})...")

    if not os.path.exists("data/golden_set.jsonl"):
        print("[FAIL] Thieu data/golden_set.jsonl. Hay chay 'python data/synthetic_gen.py' truoc.")
        return None, None

    with open("data/golden_set.jsonl", "r", encoding="utf-8") as f:
        dataset = [json.loads(line) for line in f if line.strip()]

    if not dataset:
        print("[FAIL] File data/golden_set.jsonl rong. Hay tao it nhat 1 test case.")
        return None, None

    runner = BenchmarkRunner(
        MainAgent(optimized=optimized, top_k=3),
        RetrievalMetricsEvaluator(top_k=3),
        LLMJudge(),
    )
    results = await runner.run_all(dataset)

    total = len(results)
    avg_hit_rate = sum(r["ragas"]["retrieval"]["hit_rate"] for r in results) / total
    avg_mrr = sum(r["ragas"]["retrieval"]["mrr"] for r in results) / total
    summary = {
        "metadata": {"version": agent_version, "total": total, "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")},
        "metrics": {
            "avg_score": sum(r["judge"]["final_score"] for r in results) / total,
            "hit_rate": avg_hit_rate,
            "avg_hit_rate": avg_hit_rate,
            "avg_mrr": avg_mrr,
            "agreement_rate": sum(r["judge"]["agreement_rate"] for r in results) / total
        }
    }
    return results, summary

async def run_benchmark(version: str, optimized: bool):
    _, summary = await run_benchmark_with_results(version, optimized=optimized)
    return summary

async def main():
    v1_summary = await run_benchmark("Agent_V1_Base", optimized=False)
    v2_results, v2_summary = await run_benchmark_with_results("Agent_V2_Optimized", optimized=True)
    
    if not v1_summary or not v2_summary:
        print("[FAIL] Khong the chay Benchmark. Kiem tra lai data/golden_set.jsonl.")
        return

    print("\n--- KET QUA SO SANH (REGRESSION) ---")
    delta = v2_summary["metrics"]["avg_score"] - v1_summary["metrics"]["avg_score"]
    print("V1 Score:", v1_summary["metrics"]["avg_score"])
    print("V2 Score:", v2_summary["metrics"]["avg_score"])
    print("Delta:", ("+" if delta >= 0 else "") + f"{delta:.2f}")
    print("Agreement Rate: %.2f%%" % (v2_summary["metrics"]["agreement_rate"] * 100))
    print("V1 Retrieval: hit@3=%.4f mrr=%.4f" % (v1_summary["metrics"]["avg_hit_rate"], v1_summary["metrics"]["avg_mrr"]))
    print("V2 Retrieval: hit@3=%.4f mrr=%.4f" % (v2_summary["metrics"]["avg_hit_rate"], v2_summary["metrics"]["avg_mrr"]))

    os.makedirs("reports", exist_ok=True)
    with open("reports/summary.json", "w", encoding="utf-8") as f:
        json.dump(v2_summary, f, ensure_ascii=False, indent=2)
    with open("reports/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(v2_results, f, ensure_ascii=False, indent=2)

    if delta > 0:
        print("[APPROVE] RELEASE APPROVED")
    else:
        print("[BLOCK] ROLLBACK TRIGGERED")

if __name__ == "__main__":
    asyncio.run(main())
