import asyncio
import unicodedata
import math
import re
from collections import Counter
from typing import Any, Dict, List, Tuple

class MainAgent:
    """
    Day 08 style grounded RAG agent.

    - Base mode: dense-style lexical retrieval + grounded answer.
    - Optimized mode: hybrid retrieval with query expansion and small rerank.
    """
    def __init__(self, optimized: bool = False, top_k: int = 3):
        self.name = "SupportAgent-v2" if optimized else "SupportAgent-v1"
        self.optimized = optimized
        self.top_k = top_k
        self.knowledge_base = [
            {
                "doc_id": "doc_policy_01",
                "text": (
                    "Quy che dai hoc VinUni yeu cau sinh vien phai hoan thanh toi thieu "
                    "120 tin chi de tot nghiep. Sinh vien co GPA duoi 2.0 trong hai hoc "
                    "ky lien tiep se bi canh cao hoc vu."
                ),
            },
            {
                "doc_id": "doc_policy_02",
                "text": (
                    "Thu vien mo cua tu 8:00 sang den 10:00 toi cac ngay trong tuan. "
                    "Cuoi tuan mo tu 9:00 sang den 5:00 chieu."
                ),
            },
            {
                "doc_id": "doc_tech_01",
                "text": (
                    "He thong email dung duoi @vinuni.edu.vn. Mat khau phai dai it nhat "
                    "12 ky tu, bao gom chu hoa, chu thuong, so va ky tu dac biet."
                ),
            },
            {
                "doc_id": "doc_dorm_01",
                "text": (
                    "Cam nau an bang lua ho trong ky tuc xa. Sinh vien chi duoc su dung "
                    "lo vi song va am dun nuoc dien duoc kiem dinh."
                ),
            },
            {
                "doc_id": "doc_finance_01",
                "text": (
                    "Hoc phi phai duoc dong truoc ngay mung 5 cua thang dau tien moi hoc ky. "
                    "Qua han se tinh lai suat 1% moi ngay."
                ),
            },
        ]
        self.doc_tokens = {
            doc["doc_id"]: set(self._tokenize(doc["text"])) for doc in self.knowledge_base
        }
        self.doc_norm_tokens = {
            doc["doc_id"]: set(self._tokenize(self._normalize_text(doc["text"])))
            for doc in self.knowledge_base
        }
        self.doc_norm_text = {
            doc["doc_id"]: self._normalize_text(doc["text"])
            for doc in self.knowledge_base
        }
        self.doc_term_counts = {
            doc["doc_id"]: Counter(self._tokenize(doc["text"])) for doc in self.knowledge_base
        }
        self.doc_norm_term_counts = {
            doc["doc_id"]: Counter(self._normalize_tokens(doc["text"]))
            for doc in self.knowledge_base
        }
        self.doc_freq: Dict[str, int] = {}
        for doc_id, token_set in self.doc_norm_tokens.items():
            for token in token_set:
                self.doc_freq[token] = self.doc_freq.get(token, 0) + 1
        self.total_docs = len(self.knowledge_base)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r"\w+", text.lower())

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFKD", text)
        normalized = "".join(char for char in normalized if not unicodedata.combining(char))
        normalized = normalized.lower()
        normalized = re.sub(r"[^\w\s]", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _normalize_tokens(self, text: str) -> List[str]:
        return self._tokenize(self._normalize_text(text))

    def _idf(self, token: str) -> float:
        df = self.doc_freq.get(token, 0)
        # Smooth IDF to avoid zero and reduce extreme values for tiny corpora.
        return math.log((self.total_docs + 1.0) / (df + 1.0)) + 1.0

    def _bm25_lite_score(self, query_tokens: List[str], doc_id: str) -> float:
        if not query_tokens:
            return 0.0

        doc_counter = self.doc_norm_term_counts[doc_id]
        score = 0.0
        for token in query_tokens:
            tf = doc_counter.get(token, 0)
            if tf <= 0:
                continue
            score += (1.0 + math.log(1.0 + tf)) * self._idf(token)
        return score

    @staticmethod
    def _clean_source(source: str) -> str:
        return source.split("/")[-1].split("\\")[-1]

    def _expand_queries(self, question: str) -> List[str]:
        query = (question or "").strip()
        if not query:
            return []

        variants = [query]
        lowered = query.lower()

        # Keep a compact keyword-focused variant to improve recall.
        tokens = re.findall(r"[A-Za-z]{2,}|\d{2,}|\d+", query)
        if tokens:
            variants.append(" ".join(dict.fromkeys(token.lower() for token in tokens)))

        # Accent-insensitive variant helps Vietnamese matching.
        normalized = self._normalize_text(query)
        if normalized and normalized != lowered:
            variants.append(normalized)

        # Split on common Vietnamese connectors for multi-part questions.
        for separator in [" và ", " hoặc ", " nếu ", " thì ", ";", ","]:
            if separator in lowered:
                for part in query.split(separator):
                    part = part.strip()
                    if len(part) >= 4:
                        variants.append(part)

        deduped = []
        seen = set()
        for variant in variants:
            normalized = variant.strip()
            if not normalized or normalized in seen:
                continue
            deduped.append(normalized)
            seen.add(normalized)
        return deduped

    def _score_documents(self, question: str) -> List[Tuple[str, float]]:
        q_tokens = self._tokenize(question)
        q_token_set = set(q_tokens)
        q_norm_tokens = self._normalize_tokens(question)
        q_norm_set = set(q_norm_tokens)
        scores: List[Tuple[str, float]] = []

        for doc in self.knowledge_base:
            doc_id = doc["doc_id"]
            d_tokens = self.doc_tokens[doc_id]
            d_norm_tokens = self.doc_norm_tokens[doc_id]
            term_counts = self.doc_term_counts[doc_id]
            overlap_terms = q_token_set & d_tokens
            lexical_overlap = sum(term_counts.get(token, 0) for token in overlap_terms)
            norm_overlap = len(q_norm_set & d_norm_tokens)
            bm25_score = self._bm25_lite_score(q_norm_tokens, doc_id)

            score = float(lexical_overlap) + (norm_overlap * 0.75) + (bm25_score * 0.35)
            if self.optimized:
                # Optimized mode uses only generic boosts: token coverage + numeric consistency.
                long_token_bonus = sum(1.0 for tok in q_token_set if len(tok) >= 5 and tok in d_tokens)
                norm_phrase_bonus = 2.0 if any(token in self.doc_norm_text[doc_id] for token in q_norm_set if len(token) >= 4) else 0.0
                raw_phrase_bonus = 1.0 if any(token in doc["text"].lower() for token in q_token_set if len(token) >= 4) else 0.0
                numeric_bonus = 1.5 if any(token.isdigit() for token in q_token_set) and any(token.isdigit() for token in d_tokens) else 0.0
                token_coverage = 0.0
                if q_norm_set:
                    token_coverage = len(q_norm_set & d_norm_tokens) / len(q_norm_set)
                score += long_token_bonus + norm_phrase_bonus + raw_phrase_bonus + numeric_bonus + (token_coverage * 3.0)

            scores.append((doc_id, score))

        scores.sort(key=lambda x: (x[1], x[0]), reverse=True)
        return scores

    def _retrieve_dense(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        ranked = self._score_documents(question)
        return self._format_chunks(ranked, top_k)

    def _retrieve_sparse(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        tokens = self._normalize_tokens(question)
        if not tokens:
            return []

        token_counts = Counter(tokens)
        ranked: List[Tuple[str, float]] = []
        for doc in self.knowledge_base:
            doc_id = doc["doc_id"]
            doc_counter = self.doc_norm_term_counts[doc_id]
            score = 0.0
            for token, count in token_counts.items():
                if token in doc_counter:
                    score += min(count, 2) * (1.0 + math.log(1.0 + doc_counter[token])) * self._idf(token)

            if self.optimized and score > 0:
                q_norm_set = set(tokens)
                d_norm_tokens = self.doc_norm_tokens[doc_id]
                coverage = len(q_norm_set & d_norm_tokens) / max(len(q_norm_set), 1)
                score += coverage * 2.0
            ranked.append((doc_id, score))

        ranked.sort(key=lambda item: item[1], reverse=True)
        return self._format_chunks(ranked, top_k)

    def _retrieve_hybrid(self, question: str, top_k: int) -> List[Dict[str, Any]]:
        query_variants = self._expand_queries(question)
        dense_results: List[Dict[str, Any]] = []
        sparse_results: List[Dict[str, Any]] = []

        for variant in query_variants:
            dense_results.extend(self._retrieve_dense(variant, top_k * 2))
            sparse_results.extend(self._retrieve_sparse(variant, top_k * 2))

        if not dense_results:
            dense_results = self._retrieve_dense(question, top_k * 2)
        if not sparse_results:
            sparse_results = self._retrieve_sparse(question, top_k * 2)

        rrf_scores: Dict[str, float] = {}
        docs_by_id: Dict[str, Dict[str, Any]] = {}
        k_constant = 60

        for rank, doc in enumerate(dense_results, 1):
            doc_id = doc["metadata"]["doc_id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k_constant + rank)
            docs_by_id[doc_id] = doc

        for rank, doc in enumerate(sparse_results, 1):
            doc_id = doc["metadata"]["doc_id"]
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (k_constant + rank)
            docs_by_id.setdefault(doc_id, doc)

        ranked_ids = sorted(rrf_scores.keys(), key=lambda doc_id: rrf_scores[doc_id], reverse=True)
        results: List[Dict[str, Any]] = []
        for doc_id in ranked_ids[:top_k]:
            chunk = dict(docs_by_id[doc_id])
            chunk["score"] = round(rrf_scores[doc_id], 6)
            results.append(chunk)

        # Final optimized rerank: prefer chunks with higher exact overlap against normalized query.
        if self.optimized and results:
            q_norm_set = set(self._normalize_tokens(question))

            def rerank_key(chunk: Dict[str, Any]) -> Tuple[float, float, str]:
                doc_id = chunk["metadata"]["doc_id"]
                text_norm = self.doc_norm_text[doc_id]
                normalized_overlap = sum(1 for token in q_norm_set if len(token) >= 4 and token in text_norm)
                numeric_overlap = sum(1 for token in q_norm_set if token.isdigit() and token in text_norm)
                coverage = normalized_overlap / max(len(q_norm_set), 1)
                return (
                    float(chunk.get("score", 0.0)) + normalized_overlap * 0.05 + numeric_overlap * 0.2 + coverage,
                    float(chunk.get("score", 0.0)),
                    doc_id,
                )

            results.sort(key=rerank_key, reverse=True)
        return results

    def _format_chunks(self, ranked: List[Tuple[str, float]], top_k: int) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for doc_id, score in ranked:
            if score <= 0:
                continue
            doc = next(item for item in self.knowledge_base if item["doc_id"] == doc_id)
            results.append(
                {
                    "text": doc["text"],
                    "score": round(float(score), 4),
                    "metadata": {
                        "doc_id": doc_id,
                        "source": doc_id,
                    },
                }
            )
            if len(results) >= top_k:
                break
        return results

    def _extract_exact_citation(self, text: str, question: str, max_length: int = 180) -> str:
        if not text or not question:
            return text[:max_length] if text else ""

        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        query_tokens = set(self._tokenize(question))
        sentence_scores: List[Tuple[str, float, int]] = []

        for sentence in sentences:
            sentence_tokens = set(self._tokenize(sentence))
            if not sentence_tokens:
                continue
            overlap = query_tokens & sentence_tokens
            score = len(overlap) / max(len(query_tokens | sentence_tokens), 1)
            sentence_scores.append((sentence.strip(), score, len(overlap)))

        if not sentence_scores:
            return text[:max_length]

        sentence_scores.sort(key=lambda item: (item[1], item[2]), reverse=True)
        selected: List[str] = []
        total_length = 0
        for sentence, score, _ in sentence_scores:
            if score < 0.05:
                break
            if total_length + len(sentence) <= max_length:
                selected.append(sentence)
                total_length += len(sentence) + 1

        if selected:
            return " ".join(selected)[:max_length]
        return sentence_scores[0][0][:max_length]

    def _estimate_confidence(self, chunks: List[Dict[str, Any]], answer: str) -> float:
        if not chunks:
            return 0.1
        if "khong du thong tin" in answer.lower() or "khong co trong tai lieu" in answer.lower():
            return 0.3
        avg_score = sum(chunk.get("score", 0.0) for chunk in chunks) / len(chunks)
        return round(max(0.1, min(0.95, avg_score + 0.25)), 2)

    def _build_answer(self, question: str, chunks: List[Dict[str, Any]]) -> str:
        if not chunks:
            return "Tai lieu hien co khong de cap truc tiep den cau hoi nay."

        if any("khong du thong tin" in chunk.get("text", "").lower() for chunk in chunks):
            return "Tai lieu hien co khong de cap truc tiep den cau hoi nay."

        lines: List[str] = []
        for idx, chunk in enumerate(chunks, 1):
            source = chunk.get("metadata", {}).get("doc_id", "unknown")
            citation = self._extract_exact_citation(chunk.get("text", ""), question)
            lines.append(f"[{source}] {citation}")

        return "\n".join(lines)

    async def query(self, question: str) -> Dict:
        """
        Day 08 style grounded RAG:
        1. Retrieval: dense/sparse/hybrid depending on mode.
        2. Generation: deterministic grounded answer with citation.
        """
        await asyncio.sleep(0.05)

        retrieval_mode = "hybrid" if self.optimized else "dense"
        if self.optimized:
            candidates = self._retrieve_hybrid(question, self.top_k * 2)
        else:
            candidates = self._retrieve_dense(question, self.top_k)

        retrieved_ids = [chunk.get("metadata", {}).get("doc_id", "unknown") for chunk in candidates[: self.top_k]]
        contexts = [
            self._extract_exact_citation(chunk.get("text", ""), question)
            for chunk in candidates[: self.top_k]
        ]
        answer = self._build_answer(question, candidates[: self.top_k])

        if not retrieved_ids or all(not rid or rid == "unknown" for rid in retrieved_ids):
            answer = "Tai lieu hien co khong de cap truc tiep den cau hoi nay."

        confidence = self._estimate_confidence(candidates[: self.top_k], answer)

        return {
            "answer": answer,
            "retrieved_ids": retrieved_ids,
            "contexts": contexts,
            "sources": retrieved_ids,
            "confidence": confidence,
            "retrieval_mode": retrieval_mode,
            "metadata": {
                "model": "gpt-4o-mini",
                "tokens_used": max(1, len(self._tokenize(question)) * 8),
                "sources": retrieved_ids,
                "retrieval_mode": retrieval_mode,
                "confidence": confidence,
                "optimized": self.optimized,
            },
        }

if __name__ == "__main__":
    agent = MainAgent()
    async def test():
        resp = await agent.query("Làm thế nào để đổi mật khẩu?")
        print(resp)
    asyncio.run(test())
