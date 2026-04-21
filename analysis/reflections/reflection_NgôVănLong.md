# Individual Reflection — Ngô Văn Long
**Vai trò:** Member 4 — DevOps & System Integrator  
**Lab:** Day 14 — AI Evaluation Factory  
**Ngày:** 2026-04-21

---

## 1. Đóng góp kỹ thuật (Engineering Contribution)

Tôi chịu trách nhiệm toàn bộ phần tích hợp hệ thống và vận hành pipeline, cụ thể:

### `engine/runner.py` — Async Benchmark Pipeline
- Thiết kế `BenchmarkRunner` xử lý test cases theo batch với `asyncio.gather()`.
- Cấu hình `batch_size=5` và delay 1 giây giữa các batch để tránh Rate Limit của OpenAI/Gemini.
- Kết quả: 60 test cases hoàn thành trong **33 giây** (mục tiêu < 2 phút).

### `main.py` — Regression Release Gate
- Xây dựng logic chạy song song **Agent V1 (Base — Dense retrieval)** và **Agent V2 (Optimized — Hybrid RRF)**.
- Tính `delta = V2_score - V1_score`: nếu delta > 0 → in `RELEASE APPROVED ✅`, ngược lại → `ROLLBACK TRIGGERED 🚨`.
- Tích hợp đo lường token usage và `estimated_cost_usd` vào `reports/summary.json`.

### `analysis/failure_analysis.md` — Phân tích 5 Whys
- Phân loại 4 nhóm lỗi từ 60 test cases: Out-of-context hallucination, Adversarial number confusion, Multi-step reasoning failure, Tone mismatch.
- Viết phân tích **5 Whys** sâu cho 3 case nghiêm trọng nhất, truy tìm root cause đến tận kiến trúc hệ thống.
- Đề xuất Action Plan P0/P1/P2 với ước tính % cải thiện cho từng hành động.

---

## 2. Hiểu sâu kỹ thuật (Technical Depth)

### Mean Reciprocal Rank (MRR) là gì?
MRR đo chất lượng xếp hạng của retriever. Với mỗi câu hỏi, nếu document đúng được retrieve ở vị trí thứ `k`, thì điểm MRR cho case đó là `1/k`. Trung bình tất cả các cases cho ra `avg_mrr`.

Ví dụ thực tế trong hệ thống này: `avg_mrr = 0.6083` nghĩa là trung bình document đúng xuất hiện ở vị trí ~1.6 trong top-3 retrieved documents — tương đối tốt nhưng vẫn có room để cải thiện với semantic chunking.

### Agreement Rate & Cohen's Kappa
**Agreement Rate** trong hệ thống này tính đơn giản:
- `|score_A - score_B| <= 1` → agreement = 1.0 (Strong)
- `|score_A - score_B| <= 2` → agreement = 0.5 (Moderate)
- `|score_A - score_B| >= 3` → agreement = 0.0 (Major disagreement)

**Cohen's Kappa** là phiên bản nâng cao hơn: nó loại trừ xác suất đồng thuận ngẫu nhiên. Kappa = (P_observed - P_expected) / (1 - P_expected). Hệ thống hiện tại chưa implement Kappa — đây là một cải tiến cần thêm vào để đo độ tin cậy của Judge chính xác hơn.

### Position Bias trong LLM Judge
Position Bias xảy ra khi Judge model có xu hướng ưu tiên câu trả lời ở vị trí nhất định (thường là đầu tiên) bất kể nội dung. Trong `llm_judge.py`, hàm `check_position_bias()` được để placeholder — chưa implement. Cách phát hiện: đảo thứ tự (A,B) thành (B,A) rồi so sánh kết quả chấm.

### Trade-off Chi phí vs Chất lượng
Benchmark 60 cases với `gpt-4o-mini` + `gemini-2.0-flash-lite` tốn ~$0.0024 (~2,400 VND). Nếu dùng `gpt-4o` full thì chất lượng judge tốt hơn nhưng tốn ~20× chi phí. Chiến lược tối ưu: dùng model nhẹ cho bulk evaluation, chỉ escalate lên model nặng khi agreement rate thấp (< 0.5) — tiết kiệm ~70% chi phí mà vẫn giữ được accuracy trên các case khó.

---

## 3. Giải quyết vấn đề (Problem Solving)

### Vấn đề 1: Gemini API bị quota exceeded (429)
**Triệu chứng:** Toàn bộ Gemini scores fallback về 3.0 với lỗi `Free Tier limit exceeded`, khiến agreement_rate bị thấp giả tạo.  
**Giải pháp:** Đổi từ `gemini-2.0-flash` sang `gemini-2.0-flash-lite` — model nhẹ hơn, quota cao hơn trên free tier.

### Vấn đề 2: Race condition khi chạy async
**Triệu chứng:** Ban đầu `asyncio.gather()` gọi quá nhiều requests đồng thời, gây 429 Rate Limit liên tục.  
**Giải pháp:** Chia thành batches với `batch_size=5` và `asyncio.sleep(1)` giữa các batch — đây là pattern sliding window thay vì gửi tất cả cùng lúc.

### Vấn đề 3: Benchmark results chứa mock data (API key chưa load)
**Triệu chứng:** Chạy lần đầu khi chưa có `.env`, toàn bộ judge reasoning đều là `"OpenAI API Key missing"`, score mặc định 3.0.  
**Giải pháp:** Thêm `.env` đúng chỗ, xác nhận `load_dotenv()` được gọi trước khi khởi tạo `LLMJudge`. Chạy lại `python main.py` để có kết quả thực tế.

---

## 4. Kết luận

Vai trò System Integrator đòi hỏi hiểu toàn bộ data flow: từ dataset → agent → retrieval eval → multi-judge → regression report. Phần thách thức nhất là đảm bảo async pipeline không bị sập ở giữa do rate limit, và đảm bảo output schema nhất quán để `check_lab.py` pass toàn bộ.

Bài học lớn nhất: **một hệ thống eval chỉ đáng tin khi chính bản thân nó được test kỹ** — kết quả mock (API key missing) trông "đẹp" (agreement 100%) nhưng hoàn toàn vô nghĩa so với kết quả thực tế (agreement 55.8% phản ánh đúng hành vi của Judges).
