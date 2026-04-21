import asyncio
import time
from typing import List, Dict


class BenchmarkRunner:
    def __init__(self, agent, evaluator, judge):
        self.agent = agent
        self.evaluator = evaluator
        self.judge = judge

    async def run_single_test(self, test_case: Dict) -> Dict:
        start_time = time.perf_counter()

        # 1. Call agent
        response = await self.agent.query(test_case["question"])
        latency = time.perf_counter() - start_time

        # 2. Retrieval metrics (hit_rate, MRR)
        ragas_scores = await self.evaluator.score(test_case, response)

        # 3. Multi-judge scoring (OpenAI + Gemini)
        judge_result = await self.judge.evaluate_multi_judge(
            test_case["question"],
            response["answer"],
            test_case["expected_answer"],
        )

        # 4. Token cost tracking from agent metadata
        tokens_used = response.get("metadata", {}).get("tokens_used", 0)

        return {
            "test_case": test_case["question"],
            "agent_response": response["answer"],
            "retrieved_ids": response.get("retrieved_ids", []),
            "expected_ids": test_case.get("metadata", {}).get("expected_retrieval_ids", []),
            "difficulty": test_case.get("metadata", {}).get("difficulty", "unknown"),
            "type": test_case.get("metadata", {}).get("type", "unknown"),
            "latency": round(latency, 4),
            "tokens_used": tokens_used,
            "ragas": ragas_scores,
            "judge": judge_result,
            "status": "fail" if judge_result["final_score"] < 3 else "pass",
        }

    async def run_all(self, dataset: List[Dict], batch_size: int = 5) -> List[Dict]:
        """
        Process dataset in batches using asyncio.gather.
        Sleep between batches to respect OpenAI rate limits.
        Target: 50 cases in under 2 minutes.
        """
        results: List[Dict] = []
        total_batches = (len(dataset) + batch_size - 1) // batch_size

        for batch_idx, i in enumerate(range(0, len(dataset), batch_size)):
            batch = dataset[i : i + batch_size]
            tasks = [self.run_single_test(case) for case in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=False)
            results.extend(batch_results)

            processed = min(i + batch_size, len(dataset))
            print(f"  [Batch {batch_idx + 1}/{total_batches}] {processed}/{len(dataset)} cases done.")

            # Rate limit guard: pause between batches (skip after last)
            if batch_idx < total_batches - 1:
                await asyncio.sleep(1.0)

        return results
