# Báo cáo Phân tích Thất bại (Failure Analysis Report)

## 1. Tổng quan Benchmark

| Chỉ số | Agent V1 (Base) | Agent V2 (Optimized) |
|--------|-----------------|----------------------|
| Tổng số cases | 60 | 60 |
| Retrieval Strategy | Dense (lexical BM25-lite) | Hybrid (Dense + Sparse + RRF Rerank) |
| Trọng số scoring | overlap + BM25×0.35 | + long_token_bonus + norm_phrase_bonus + numeric_bonus |
| Avg Hit@3 (ước tính) | ~0.60 | ~0.75 |
| Avg MRR (ước tính) | ~0.55 | ~0.70 |
| LLM-Judge Avg Score | ~2.8 / 5.0 | ~3.2 / 5.0 |

---

## 2. Phân nhóm lỗi (Failure Clustering)

| Nhóm lỗi | Số lượng | Nguyên nhân |
|----------|----------|-------------|
| **Out-of-context hallucination** | ~14 | Retriever gán sai document vì khớp từ bề mặt với câu hỏi `out_of_context` |
| **Adversarial number confusion** | ~6 | Số sai trong đề bài (150 tín chỉ) lấn át BM25 score của document chứa số đúng (120) |
| **Multi-step reasoning failure** | ~8 | Agent trả lời trực tiếp từ citation thay vì suy luận tổng hợp nhiều điều kiện |
| **Tone mismatch** | ~4 | Agent trả lời bằng đoạn văn Latin (romanized) thay vì tiếng Việt đầy đủ |

---

## 3. Phân tích 5 Whys — 3 Case Thất Bại Nghiêm Trọng Nhất

---

### Case #1 — Out-of-context Hallucination

**Câu hỏi:** *"VinUni có chương trình học bổng nào cho sinh viên không?"*
**Expected:** `"Tài liệu không đề cập / Tôi không biết"`
**Agent trả lời:** `[doc_policy_01] Quy chế dai hoc VinUni yeu cau sinh vien phai hoan thanh...`

**Chẩn đoán:** Agent trả về citation từ `doc_policy_01` thay vì nhận ra câu hỏi nằm ngoài phạm vi tài liệu. Judge chấm Accuracy=1/5, Tone=3/5 → final_score=2.0 (FAIL).

| Bước | Why |
|------|-----|
| **Why 1** | Agent trả lời sai vì nó luôn trả về document có điểm cao nhất, kể cả khi điểm đó rất thấp. |
| **Why 2** | Điểm thấp vẫn được chọn vì hàm `_format_chunks` chỉ lọc `score <= 0`, không có ngưỡng tối thiểu có nghĩa. |
| **Why 3** | Không có ngưỡng confidence vì `_estimate_confidence` chỉ hạ score khi answer đã chứa "khong du thong tin" — nhưng answer chưa được kiểm tra trước. |
| **Why 4** | Kiểm tra "không đủ thông tin" chỉ dựa trên text của chunk, không dựa trên relevance score của query-document pair. |
| **Root Cause** | **Thiếu relevance threshold gate:** Retriever không có cơ chế reject khi max similarity score quá thấp (< 0.3). Kết quả là mọi câu hỏi đều nhận được câu trả lời, kể cả câu hỏi `out_of_context`.  |

**Action:** Thêm `min_score_threshold=0.3` vào `_format_chunks`. Nếu tất cả documents có score < threshold → trả về empty list → agent tự động fallback sang "Tài liệu không đề cập".

---

### Case #2 — Adversarial Number Confusion

**Câu hỏi:** *"Quy chế đại học VinUni yêu cầu sinh viên phải hoàn thành tối thiểu **150 tín chỉ** để tốt nghiệp. Điều này có đúng không?"*
**Expected:** `"...yêu cầu tối thiểu 120 tín chỉ..."` (cải chính)
**Agent trả lời:** Đôi khi echo lại số 150 vì lexical overlap cao hơn với câu hỏi.

**Chẩn đoán:** BM25-lite tính TF của token "150" trong câu hỏi, nhưng corpus chứa "120" chứ không phải "150". Tuy nhiên các token xung quanh ("tin chi", "tot nghiep") tạo overlap cao → document đúng được retrieve nhưng answer generation copy số từ câu hỏi thay vì từ context.

| Bước | Why |
|------|-----|
| **Why 1** | Agent echo số sai vì `_extract_exact_citation` chọn câu có Jaccard overlap cao nhất với câu hỏi — câu hỏi chứa "150" tạo lexical match mạnh hơn câu trong tài liệu chứa "120". |
| **Why 2** | `_extract_exact_citation` sử dụng `query_tokens & sentence_tokens` — token "150" không xuất hiện trong tài liệu nên không khớp, nhưng sentence nào có nhiều token trùng nhất vẫn được chọn bất kể số sai. |
| **Why 3** | Không có bước adversarial detection để phát hiện số trong câu hỏi khác số trong tài liệu. |
| **Why 4** | Hệ thống thiết kế theo kiểu grounded retrieval nhưng không validate ngược lại: "context có hỗ trợ claim trong câu hỏi không?" |
| **Root Cause** | **Thiếu claim verification layer:** Agent không có khả năng so sánh số liệu giữa câu hỏi và context. Cần thêm bước post-processing kiểm tra numeric consistency giữa câu hỏi và retrieved text. |

**Action:** Thêm numeric anomaly detection: nếu câu hỏi chứa số X và context chứa số Y ≠ X tại cùng vị trí ngữ nghĩa → đánh dấu là adversarial và ưu tiên trích dẫn từ context, không phải câu hỏi.

---

### Case #3 — Multi-step Reasoning Failure

**Câu hỏi:** *"Nếu một sinh viên có GPA là 2.5 trong học kỳ đầu tiên và GPA là 1.8 trong học kỳ thứ hai, sinh viên đó có bị cảnh cáo học vụ không?"*
**Expected:** Câu trả lời yêu cầu lập luận: chỉ có 1 học kỳ GPA < 2.0, nhưng rule yêu cầu **2 học kỳ liên tiếp**.
**Agent trả lời:** Trích dẫn nguyên văn rule từ `doc_policy_01` mà không áp dụng vào điều kiện cụ thể.

**Chẩn đoán:** Agent trả về `[doc_policy_01] Sinh vien co GPA duoi 2.0 trong hai hoc ky...` — đây là citation đúng nhưng không phải **câu trả lời** cho câu hỏi "có bị cảnh cáo không?". Judge chấm Accuracy=2/5 (thiếu inference step).

| Bước | Why |
|------|-----|
| **Why 1** | Agent không suy luận được vì nó là **retrieval-only agent** — `_build_answer` chỉ extract và format citation, không có LLM generation. |
| **Why 2** | Không có LLM generation vì thiết kế cố tình grounded-only để tránh hallucination, nhưng điều này loại bỏ cả khả năng reasoning. |
| **Why 3** | Không có LLM reasoning step vì chi phí API bị tối ưu — mỗi query chỉ dùng lexical scoring nội bộ, không call GPT cho generation. |
| **Why 4** | Benchmark dataset bao gồm câu hỏi dạng `reasoning` và `hard` nhưng agent không phân biệt loại câu hỏi để điều chỉnh chiến lược trả lời. |
| **Root Cause** | **Kiến trúc Agent không phù hợp với loại câu hỏi reasoning:** Retrieval-only agent phù hợp cho `factual` queries nhưng không xử lý được `reasoning` queries. Cần routing logic: factual → direct citation, reasoning → LLM-assisted inference. |

**Action:** Thêm query classifier dựa trên từ khóa ("nếu", "thì", "có ... không", "tính toán") để route câu hỏi reasoning sang LLM generation với context được inject.

---

## 4. Kế hoạch cải tiến (Action Plan)

| Ưu tiên | Hành động | Tác động | Độ khó |
|---------|-----------|---------|--------|
| 🔴 P0 | Thêm `min_score_threshold=0.3` vào `_format_chunks` để chặn out-of-context answers | Giảm ~23% false positive | Thấp |
| 🟠 P1 | Thêm query type routing (factual vs reasoning) — dùng keyword detection | Giải quyết ~13% reasoning failures | Trung bình |
| 🟠 P1 | Thêm numeric consistency check giữa query và retrieved context | Giảm ~10% adversarial failures | Trung bình |
| 🟡 P2 | Thêm Semantic Chunking thay vì toàn bộ document làm 1 chunk | Tăng retrieval precision cho câu hỏi multi-fact | Cao |
| 🟡 P2 | Tích hợp LLM generation (gpt-4o-mini) cho câu hỏi `hard` và `reasoning` | Cải thiện MRR và Judge Score tổng thể | Cao |

---

## 5. Kết luận

Hệ thống hiện tại đạt hiệu năng tốt ở **factual / easy** queries nhờ BM25-lite retrieval với accent normalization. Hai điểm yếu chính là:

1. **Không có rejection threshold** → hallucinate trên out-of-context queries
2. **Không có reasoning capability** → fail trên multi-condition inference

V2 Optimized (hybrid retrieval + RRF rerank) cải thiện Hit@3 và MRR đáng kể, nhưng vẫn gặp cùng kiến trúc limitation. Bước tiếp theo quan trọng nhất là thêm **relevance gate** (P0) và **query routing** (P1).
