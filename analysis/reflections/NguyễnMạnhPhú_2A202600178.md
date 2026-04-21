# Individual Reflection — Nguyễn Mạnh Phú
**Vai trò:** Member 2 — AI Engineer (Retrieval & Agent Optimization)  
**Lab:** Day 14 — AI Evaluation Factory  
**Ngày:** 2026-04-21

---

## 1. Đóng góp kỹ thuật (Engineering Contribution)

Tôi phụ trách phần Bring-Your-Own-Agent và đo lường Retrieval Evaluation, cụ thể:

### `agent/main_agent.py` — Agent Contract Integration
- Tích hợp logic agent vào `MainAgent` để hàm `query()` trả về đúng contract cho toàn bộ pipeline.
- Bảo đảm các trường đầu ra luôn có mặt: `answer`, `retrieved_ids`, `contexts`, `sources`, `confidence`, `metadata`.
- Mục tiêu chính là để các module đánh giá phía sau không bị vỡ schema khi chạy benchmark hàng loạt.

### `engine/retrieval_eval.py` — Retrieval Metrics
- Cập nhật logic đọc ground truth theo schema mới: `case["metadata"]["expected_retrieval_ids"]`.
- Triển khai Hit Rate@3: nếu có ít nhất một ID đúng nằm trong top 3 `retrieved_ids` thì tính 1, ngược lại tính 0, sau đó lấy trung bình toàn bộ test cases.
- Triển khai MRR: nếu ID đúng đầu tiên nằm ở vị trí thứ $k$ thì điểm reciprocal rank là $1/k$, còn nếu không có ID đúng thì bằng 0.
- Kết quả chạy full 60 test cases cho thấy pipeline metric hoạt động đúng và có thể dùng để so sánh các phiên bản retrieval.

### `golden_set.jsonl` và phiên bản retrieval Optimized
- Kiểm tra và đối chiếu toàn bộ tập `golden_set.jsonl` để bảo đảm ground truth được đọc đúng.
- So sánh hai phiên bản retrieval:
  - Base: cấu hình chuẩn.
  - Optimized: cải tiến retrieval strategy để đẩy đúng document lên cao hơn trong top results.
- Kết quả benchmark mới nhất sau khi chạy lại `python main.py`:
  - Phiên bản hiện tại (`Agent_V2_Optimized`): `avg_score = 2.5667`, `avg_hit_rate = 0.6333`, `avg_mrr = 0.6083`
  - `agreement_rate = 50.0%`, `total_tokens = 8,088`, `estimated_cost_usd = 0.002426`


---

## 2. Hiểu sâu kỹ thuật (Technical Depth)

### Hit Rate@3 và MRR khác nhau thế nào?
Hit Rate@3 đo việc có tìm thấy đúng hay không trong top 3, còn MRR đo document đúng xuất hiện sớm hay muộn trong danh sách retrieve. Hai metric này phải đi cùng nhau vì một hệ thống có thể vẫn hit đúng nhưng đẩy document đúng xuống thấp, làm chất lượng thực tế giảm đi.

Ví dụ trong hệ thống này, `avg_hit_rate = 0.6333` nghĩa là gần hai phần ba test cases có ít nhất một document đúng trong top 3. Đồng thời `avg_mrr = 0.6083` cho thấy chất lượng xếp hạng vẫn còn room để cải thiện vì document đúng chưa luôn nằm ở vị trí cao nhất.

### Ground-truth schema và rủi ro đánh giá sai
Ground truth của bài này không nằm ở top-level mà nằm trong `metadata`. Chỉ cần đọc sai key `expected_retrieval_ids` là toàn bộ benchmark có thể trả kết quả “đẹp” nhưng sai. Đây là lỗi rất dễ xảy ra khi evaluation pipeline thay đổi schema mà module đọc dữ liệu không được cập nhật đồng bộ.

### Trade-off giữa Retrieval Quality và tốc độ tối ưu
Tăng chất lượng retrieval không phải lúc nào cũng làm tăng Hit Rate ngay lập tức. Trong case của tôi, bản optimized chủ yếu cải thiện MRR chứ không tăng Hit Rate, nghĩa là hệ thống đã đưa document đúng lên vị trí tốt hơn chứ chưa mở rộng được số case hit đúng. Đây là kiểu cải tiến thực dụng: có hiệu quả đo được, nhưng vẫn cần tuning tiếp nếu muốn nhảy bậc về recall.

---

## 3. Giải quyết vấn đề (Problem Solving)

### Vấn đề 1: Schema ground truth không khớp
**Triệu chứng:** Nếu đọc nhầm key ground truth thì evaluation có thể trả sai toàn bộ `hit_rate` và `mrr`, dù agent vẫn chạy bình thường.  
**Giải pháp:** Chuẩn hóa lại `engine/retrieval_eval.py` để đọc đúng `case["metadata"]["expected_retrieval_ids"]` và kiểm tra lại toàn bộ `golden_set.jsonl`.

### Vấn đề 2: Agent trả thiếu trường output
**Triệu chứng:** Nếu `query()` không trả đủ các trường như `retrieved_ids`, `sources`, hoặc `metadata`, pipeline benchmark dễ vỡ ở bước sau.  
**Giải pháp:** Siết contract trong `MainAgent` để mọi response đều có đủ trường cần thiết trước khi đẩy sang evaluator.

### Vấn đề 3: Độ đồng thuận judge chưa cao
**Triệu chứng:** Theo summary mới nhất, `agreement_rate = 50.0%` và `avg_score = 2.5667`, cho thấy mức đồng thuận giữa các judge còn trung bình và chất lượng tổng thể chưa thật ổn định.  
**Giải pháp:** Tiếp tục tinh chỉnh retrieval và chuẩn hóa prompt/tiêu chí chấm để giảm chênh lệch giữa các judge, rồi rerun benchmark để kiểm tra xu hướng cải thiện.

---

## 4. Kết luận

Vai trò Retrieval & Agent Optimization đòi hỏi phải kiểm soát chặt cả contract của agent lẫn logic đánh giá phía sau. Phần thách thức lớn nhất là bảo đảm schema không lệch giữa agent và evaluator, vì chỉ cần lệch một key là toàn bộ benchmark mất ý nghĩa.

Bài học lớn nhất: **một hệ thống retrieval chỉ đáng tin khi metric được đọc đúng và contract được giữ chặt** — đồng thời phải theo dõi sát độ đồng thuận giữa các judge, vì khi agreement thấp thì quyết định release cần thận trọng và ưu tiên rollback an toàn.