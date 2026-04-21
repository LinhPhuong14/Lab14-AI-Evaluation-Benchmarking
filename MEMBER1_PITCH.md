# 🎙️ Cẩm nang Thuyết Trình cho Member 1 (Nhóm Data - SDG)

Đây là tài liệu script giúp bạn tự tin Pitching (thuyết trình demo) lúc giảng viên/TA đi vòng quanh kiểm tra đánh giá chấm điểm Lab 14.

---

## 1. Giao tiếp ban đầu (Mở bài)

> *"Chào thầy/cô, nhiệm vụ của em là hệ thống đứng đầu phễu trong toàn bộ quy trình Evaluation - tạo ra **Golden Dataset** (Tập dữ liệu Vàng). Quan điểm của nhóm em là: Để test hệ thống một cách thực tiễn, bộ bài kiểm tra phải cực kỳ khó. Nếu bài test dễ, điểm Evaluation trọn vẹn 100% cũng vô nghĩa. Cho nên em đã xây dựng một Module gọi là Synthetic Data Generator (SDG) chạy hoàn toàn tự động bằng LLM."*

## 2. Giải thích cơ chế kỹ thuật (Kiến thức cốt lõi phải hiểu)

*(Bạn hãy mở file `data/synthetic_gen.py` lên, chỉ vào các phần code và giải thích tuần tự 3 khái niệm sau)*:

### Khái niệm 1: Synthetic Data Generation (Sinh dữ liệu tổng hợp bằng AI)
> *"Thưa thầy/cô, thay vì thành viên nhóm phải ngồi viết tay 50 câu hỏi test case tốn hàng giờ, em sử dụng API của mô hình để tự động hóa quy trình (Automation). Em thiết kế một **Prompt Template** đẩy các đoạn tài liệu thô vào răn đe LLM trả ra cấu trúc dữ liệu theo đúng định dạng được quy định (Sử dụng tham số hỗ trợ JSON mode)."*

### Khái niệm 2: Red Teaming (Đóng vai tin tặc tấn công AI) & Hard Cases
*(Chỉ vào phần khai báo mảng `categories = ["factual", "reasoning", "adversarial", "out_of_context"]`):*

> *"Để phục vụ cho yêu cầu Hard Cases, em đã chia tệp bài kiểm tra (Evaluation Test Cases) ra làm 4 phân loại độ khó:
> - Tầng 1: **Factual/Reasoning** là loại bình thường để test sự hiểu văn bản và độ chính xác của tìm kiếm.
> - Tầng 2: **Adversarial (Bẫy/Tấn công)** là cố tình đưa thông tin sai vào câu hỏi để xem con Agent RAG của máy có xuôi theo trả lời bậy bạ không, hay nó biết từ chối dựa trên căn cứ văn bản.
> - Tầng 3: **Out of Context** là em bốc đại một câu hỏi ngoài lề (cố tình nhồi nhét không nằm trong kho tài liệu) để xem Agent có bị Hallucination (Ảo giác) bịa chuyện hay không."*

### Khái niệm 3: Mapping ID để tương hỗ đo lường MRR & Hit Rate
*(Chỉ vào phần thuộc tính JSON `"expected_retrieval_ids"`):*

> *"Bên cạnh đó, điểm ăn tiền là thầy/cô sẽ thấy mỗi Test Case bằng JSON em đều gắn kèm một mảng Tracking ID. Ví dụ câu hỏi này sinh ra từ tài liệu có ID là `doc_policy_01`, em sẽ map ID này vào đầu ra. Mục đích là để làm "nhãn đúng đắn (Ground Truth)" cho luồng kiểm định tiếp theo. Nếu Member 2 gọi Vector Database để tìm kiếm mà không trích xuất đúng cái ID khép kín này thì coi như Hệ thống AI của tụi em đã bị rớt ngay từ phần tìm kiếm."*

## 3. Khái niệm về Hiệu năng Bất đồng bộ (Khoe kỹ năng Coding Performance)

*(Cuộn xuống dòng có hàm `main()` và lệnh `await asyncio.gather(*tasks)`)*:

> *"Cuối cùng về mặt Performance, để tối ưu tốc độ cho Pipeline sinh ra 60 câu hỏi, em không dùng vòng lặp FOR gọi API tuần tự thủ công đợi mất hàng phút đồng hồ. Hệ thống của e bọc toàn bộ bằng Coroutine của Python - `asyncio.gather`. Hệ thống bắn song song (Parallel execution) đẩy tất cả requests lên Server Model trong cùng một thời điểm, giới hạn độ trễ (Latency) tổng thời gian gen tất cả test cases xuống tính bằng giây, tăng tốc độ hoàn thành Evaluation Factor."*
