from typing import Any, Dict, List, Optional

class RetrievalEvaluator:
    def __init__(self):
        pass

    def calculate_hit_rate(self, expected_ids: List[str], retrieved_ids: List[str], top_k: int = 3) -> float:
        """Hit@k: co it nhat 1 expected_id nam trong top_k retrieved_ids."""
        if not expected_ids:
            return 0.0

        top_retrieved = retrieved_ids[:top_k]
        hit = any(doc_id in top_retrieved for doc_id in expected_ids)
        return 1.0 if hit else 0.0

    def calculate_mrr(self, expected_ids: List[str], retrieved_ids: List[str]) -> float:
        """MRR: 1/rank voi rank la vi tri dau tien (1-indexed) cua expected_id."""
        if not expected_ids:
            return 0.0

        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in expected_ids:
                return 1.0 / (i + 1)
        return 0.0

    @staticmethod
    def _extract_expected_ids(case: Dict[str, Any]) -> List[str]:
        metadata = case.get("metadata", {}) if isinstance(case, dict) else {}
        expected = metadata.get("expected_retrieval_ids", case.get("expected_retrieval_ids", []))
        if not isinstance(expected, list):
            return []
        return [str(item) for item in expected]

    @staticmethod
    def _extract_retrieved_ids(case: Dict[str, Any], response: Optional[Dict[str, Any]]) -> List[str]:
        if isinstance(response, dict):
            ids = response.get("retrieved_ids", [])
            if isinstance(ids, list):
                return [str(item) for item in ids]

        ids = case.get("retrieved_ids", []) if isinstance(case, dict) else []
        if isinstance(ids, list):
            return [str(item) for item in ids]
        return []

    async def evaluate_batch(self, dataset: List[Dict[str, Any]], agent: Optional[Any] = None, top_k: int = 3) -> Dict[str, Any]:
        """
        Cham retrieval cho toan bo dataset.
        - Ground truth: case["metadata"]["expected_retrieval_ids"]
        - Prediction: response["retrieved_ids"] hoac case["retrieved_ids"]
        """
        total = len(dataset)
        if total == 0:
            return {
                "avg_hit_rate": 0.0,
                "avg_mrr": 0.0,
                "total_cases": 0,
                "details": [],
            }

        details: List[Dict[str, Any]] = []
        hit_sum = 0.0
        mrr_sum = 0.0

        for case in dataset:
            response: Optional[Dict[str, Any]] = None
            if agent is not None:
                response = await agent.query(case["question"])

            expected_ids = self._extract_expected_ids(case)
            retrieved_ids = self._extract_retrieved_ids(case, response)

            hit = self.calculate_hit_rate(expected_ids, retrieved_ids, top_k=top_k)
            mrr = self.calculate_mrr(expected_ids, retrieved_ids)
            hit_sum += hit
            mrr_sum += mrr

            details.append(
                {
                    "question": case.get("question", ""),
                    "expected_ids": expected_ids,
                    "retrieved_ids": retrieved_ids,
                    "hit_rate": hit,
                    "mrr": mrr,
                }
            )

        return {
            "avg_hit_rate": hit_sum / total,
            "avg_mrr": mrr_sum / total,
            "total_cases": total,
            "top_k": top_k,
            "details": details,
        }
