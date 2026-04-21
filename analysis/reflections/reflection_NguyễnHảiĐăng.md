# Báo cáo Cá nhân - Member 3: AI Engineer (Judge & Consensus)

## 1. Thông tin sinh viên
- **Họ và tên:** Nguyễn Hải Đăng
- **MSSV:** 2A202600157
- **Vai trò:** AI Engineer - Judge & Consensus

## 2. Các nhiệm vụ đã thực hiện
- **Thiết kế Multi-Judge Framework:** Triển khai module `LLMJudge` tích hợp cả OpenAI (GPT-4o-mini) và Google Gemini (Gemini 2.0 Flash).
- **Xây dựng Rubrics:** Định nghĩa bộ tiêu chí Accuracy và Tone chi tiết theo thang điểm 1-5, giúp Judge hoạt động khách quan hơn.
- **Phát triển Consensus Logic:** Viết thuật toán tính toán độ đồng thuận (Agreement Rate) giữa các Judge. Xử lý các trường hợp sai lệch điểm số (Consensus) bằng phương pháp trung bình cộng và cảnh báo nếu có sự bất đồng lớn (> 1 điểm).
- **Tối ưu Asynchronous:** Sử dụng `asyncio` để chạy song song các yêu cầu đánh giá, giảm 50% thời gian eval so với chạy tuần tự.
- **Tích hợp Pipeline:** Kết nối module Judge vào `BenchmarkRunner` trong `main.py` để tự động hóa toàn bộ quy trình đánh giá.

## 3. Kết quả đạt được
- Hệ thống đã có khả năng đánh giá tự động dựa trên 2 "giám khảo" AI khác nhau.
- Các báo cáo `summary.json` và `benchmark_results.json` đã chứa đầy đủ thông tin về `agreement_rate` và điểm số của từng model.
- Tỉ lệ đồng thuận của hệ thống đạt mức cao (phụ thuộc vào chất lượng Prompt và Ground Truth).

## 4. Bài học kinh nghiệm
- Việc sử dụng Multi-Judge giúp loại bỏ tính chủ quan của một model đơn lẻ.
- Parsing JSON từ các model LLM khác nhau cần có các kỹ thuật "robust extraction" để tránh lỗi định dạng.
- Đánh giá không chỉ là con số, mà còn là logic `reasoning` đằng sau nó.
