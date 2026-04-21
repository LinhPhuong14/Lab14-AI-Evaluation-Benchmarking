# Bảng Phân Công Nhiệm Vụ - Lab 14 (Hệ thống AI Evaluation)

Tài liệu này là chuẩn phân công tác chiến dành cho **nhóm 4 người**, được thiết kế để bao phủ 100% tiêu chí chấm điểm (60 điểm nhóm + 40 điểm cá nhân) của Lab 14. Bằng cách tuân thủ tài liệu này, nhóm sẽ tránh được rủi ro chồng chéo code (Merge Conflict) và tối đa hóa điểm hiệu năng.

---

## 🎯 Tổng quan Kế hoạch Tác chiến

- **Mục tiêu chính**: Dựng thành công Hệ thống Đánh giá Tự động (Benchmark) cho AI Agent gồm 2 phiên bản (Base và Optimized).
- **Yêu cầu chung**: Các thành viên làm việc độc lập trên file của mình, push lên nhánh riêng biệt trước khi Merge.
- **Thứ tự thực thi ưu tiên**: Vị trí **Member 1** cần hoàn thiện tập dữ liệu (JSONL) càng sớm càng tốt để 3 thành viên còn lại có data chạy thử vòng lặp hệ thống.

---

## 👨‍💻 [COMPLETED ✅] Member 1: Data & Security Engineer (Trọng điểm: Dataset & SDG - 10đ)

*   **Trạng thái**: Đã sinh thành công 60 test cases ra file `data/golden_set.jsonl`.
*   **Cấu trúc Output của file để các bạn phía sau sử dụng**:
    ```json
    {
        "question": "Câu hỏi test",
        "expected_answer": "Đáp án chuẩn",
        "context": "Context nguyên bản",
        "metadata": {
            "difficulty": "easy/medium/hard",
            "type": "factual/adversarial/out_of_context",
            "expected_retrieval_ids": ["doc_policy_01"]
        }
    }
    ```
*   *(Nhóm Data đã hoàn thành bước tạo phễu đầu vào. Các nhóm khác bắt đầu parse dữ liệu theo Schema trên!)*

---

## 🧠 Member 2: AI Engineer - Retrieval & Agent Optimization (Trọng điểm: Retrieval Evaluation - 10đ)

*   **File làm việc chính**: `agent/main_agent.py` và `engine/retrieval_eval.py`
*   **Mục tiêu (Deliverables)**: Agent RAG hoàn chỉnh chạy mượt và Hệ thống chấm điểm Vector Database.
*   **Chi tiết Nhiệm vụ**:
    1.  **Bring-Your-Own-Agent**: Bê nguyên logic con Agent (đã hoàn thiện ở Lab 8, 9, 10) tích hợp vào class `MainAgent` của `main_agent.py`. Lưu ý Agent phải trả về cả `answer` lẫn mảng `retrieved_ids` (ID của các văn bản nó tìm được).
    2.  **Đo lường Hit Rate & MRR (Cập nhật logic từ Phase 1)**:
        *   Bạn mở file `.jsonl` để loop qua. Mảng *Ground Truth* giờ nằm ở key `case["metadata"]["expected_retrieval_ids"]`.
        *   *Hit Rate*: Tính tỷ lệ ID sinh ra từ biến trên nằm trong top 3 của `retrieved_ids`.
        *   *Mean Reciprocal Rank (MRR)*: Chấm điểm sự xếp thứ hạng tìm kiếm.
    3.  **Tối ưu**: Nâng cấp thử các thủ thuật Retrival lên phiên bản `Agent_V2_Optimized` để ra kết quả tìm kiếm tốt hơn.
*   **Tiêu chí cá nhân 100%**: Đảm bảo công thức Hit Rate và MRR tính toán toán học chính xác 100%.

---

## ⚖️ Member 3: AI Engineer - Judge & Consensus (Trọng điểm: Multi-Judge Consensus - 15đ)

*   **File làm việc chính**: `engine/llm_judge.py`
*   **Mục tiêu (Deliverables)**: Mô-đun chấm điểm sử dụng nhiều mô hình phân định độ khách quan.
*   **Chi tiết Nhiệm vụ**:
    1.  **Multi-Model Framework**: Triển khai logic gọi **ít nhất 2 mô hình khác nhau** (VD: Gọi cả `gpt-4o-mini` và `gemini-1.5-flash` qua API).
    2.  **Định nghĩa Rubrics Score**: Giám khảo không thể chấm bừa, phải có metric. Tạo Prompt bắt giám khảo chấm Accuracy (độ chính xác) và Tone (sự chuyên nghiệp) từ 1-5.
    3.  **Consensus / Agreement Logic (Cốt lõi)**: Viết code tính độ đồng thuận của 2 giám khảo. Xử lý xung đột tự động: Nếu GPT chấm 5 điểm nhưng Gemini chấm 1 điểm -> Cần một logic rành mạch (VD: Từng giám khảo lập luận, hoặc tính trung bình cộng).
    4.  *(Nâng cao - Tuỳ chọn)* Bẫy Position Bias: Đảo vị trí nội dung tham khảo xem Judge có ưu tiên đáp án đưa vào trước hay không.
*   **Tiêu chí cá nhân 100%**: Xử lý mượt các bất đồng điểm số giữa nhiều mô hình Judge.

---

## 🏭 Member 4: DevOps & System Integrator (Trọng điểm: Async, Regression Gate & 5 Whys - 25đ)


*   **File làm việc chính**: `engine/runner.py`, `main.py` và thư mục `analysis/`
*   **Mục tiêu (Deliverables)**: Toàn vẹn hệ thống Async Benchmark và Reports quyết định Vận Mệnh Bản Phát Hành.
*   **Chi tiết Nhiệm vụ**:
    1.  **Asynchronous Mastery**: Trong `runner.py`, bạn phải đôn đốc tốc độ xử lý bằng `asyncio.gather` cùng chia lô `batch_size`. Pipeline 50 Cases bắt buộc phải chạy xong trong **dưới 2 phút** và không bị báo lỗi văng vì sập Rate Limit của OpenAI.
    2.  **Regression Release Gate**: Cấu hình `main.py` tự động so điểm Agent V1 với Agent V2. Nếu V2 > V1 -> In dòng chữ xanh `RELEASE APPROVED`. Nếu V2 < V1 -> `ROLLBACK TRIGGERED`.
    3.  **Cost Measurement**: Đo và thống kê lượng Token thụt đi là bao nhiêu, in ra file `summary.json`.
    4.  **Failure Analysis (Biên tập)**: Viết file `failure_analysis.md` bằng cách nhìn vào các test case thất bại thảm hại nhất, triển khai phân tích mô hình **5 Whys** để chứng minh lỗi tại Retrieval hay tại Prompting.
*   **Tiêu chí cá nhân 100%**: Run command `python check_lab.py` phải full xanh rờn (✅) mới cho ra lò nộp bài môn học.

---

## 🚀 Lịch trình Kiểm tra Chéo (Cross-check Sync)

1.  **Block 1 (T0 + 45 Phút)**:
    *   ✅ Member 1 Đã HOÀN THÀNH `/data/golden_set.jsonl`.
    *   Member 2 đã có sẵn mock kết quả trả về hoặc agent cơ bản.
2.  **Block 2 (T0 + 90 Phút)**:
    *   Member 3 hoàn tất code Consensus Judge.
    *   Member 4 yêu cầu gom các file lại thành nhánh Main và bắt đầu test Run Async.
3.  **Block 3 (Nộp Bài)**:
    *   Cả nhóm đọc lướt chéo code của nhau để trả lời được câu hỏi bảo vệ bài của Technical Depth (MRR là gì? Agreement Rate tính sao?).

---

## 🤖 Hướng dẫn phối hợp nếu Team sử dụng các công cụ AI Agents khác nhau
Nếu nhóm của bạn mỗi người sử dụng một AI Coding Agent khác nhau (Cursor, Github Copilot, Claude Engineer, hay Gemini Code Assist), hãy làm theo chỉ dẫn này để Agent của đồng đội hiểu bài toán nhanh nhất:

1.  **Chia sẻ Context**: Khi bắt đầu phiên làm việc, hãy đưa cụm Prompt System này cho con Agent của bạn: *"Đọc kỹ file `TEAM_TASKS.md` và tập `data/golden_set.jsonl`. Tôi là Member [số thứ tự]. Hãy giúp tôi viết code hoàn thiện file [tên_file_của_bạn] đáp ứng các tiêu chí 100% điểm cá nhân được quy định."*
2.  **Đừng chỉnh sửa chéo**: Cài đặt "`.cursorignore`" hoặc cấm Agent của bạn Edit file thuộc phạm vi của Member khác. Nó sẽ làm hỏng Data Pipeline hiện tại.
3.  **Bảo vệ Schema**: Khi prompt cho Agent Code Runner/Judge, hãy gửi rõ Structure JSON Output của Phase 1 ở phía trên, để Agent tự viết key cho chuẩn xác (ví dụ `["metadata"]["expected_retrieval_ids"]`), tránh bug KeyError.

Chúc Team phá đảo toàn vẹn 100/100 Điểm Expert Level Lab 14! 🚀
