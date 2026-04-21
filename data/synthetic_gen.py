import json
import asyncio
import os
from typing import List, Dict
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Tải biến môi trường từ file .env (chứa OPENAI_API_KEY)
load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Kho ngữ liệu giả định để làm nguồn tạo Test Cases. Trong thực tế, bạn sẽ dùng PyPDF để đọc từ PDF của trường.
KNOWLEDGE_BASE = [
    {"doc_id": "doc_policy_01", "text": "Quy chế đại học VinUni yêu cầu sinh viên phải hoàn thành tối thiểu 120 tín chỉ để tốt nghiệp. Sinh viên có GPA dưới 2.0 trong hai học kỳ liên tiếp sẽ bị cảnh cáo học vụ."},
    {"doc_id": "doc_policy_02", "text": "Thư viện mở cửa từ 8:00 sáng đến 10:00 tối các ngày trong tuần. Cuối tuần mở từ 9:00 sáng đến 5:00 chiều."},
    {"doc_id": "doc_tech_01", "text": "Hệ thống email dùng đuôi @vinuni.edu.vn. Mật khẩu phải dài ít nhất 12 ký tự, bao gồm chữ hoa, chữ thường, số và ký tự đặc biệt."},
    {"doc_id": "doc_dorm_01", "text": "Cấm nấu ăn bằng lửa hở trong ký túc xá. Sinh viên chỉ được sử dụng lò vi sóng và ấm đun nước điện được kiểm định."},
    {"doc_id": "doc_finance_01", "text": "Học phí phải được đóng trước ngày mùng 5 của tháng đầu tiên mỗi học kỳ. Quá hạn sẽ tính lãi suất 1% mỗi ngày."},
]

async def generate_qa_batch(knowledge_chunk: Dict, category: str, num_pairs: int) -> List[Dict]:
    """
    Sử dụng LLM để sinh dữ liệu mồi (Synthetic Data Generation) dựa trên một đoạn văn bản (context).
    Quy định ràng buộc bằng JSON Mode để đảm bảo form chuẩn.
    """
    prompt = f"""
    Bạn là một chuyên gia đánh giá hệ thống AI (AI Evaluator). Nhiệm vụ của bạn là tạo ra {num_pairs} test case loại '{category}' dựa trên đoạn tài liệu sau.
    
    TÀI LIỆU (ID: {knowledge_chunk['doc_id']}): 
    {knowledge_chunk['text']}
    
    HƯỚNG DẪN TẠO CÂU HỎI THEO LOẠI (CATEGORY):
    - 'factual': Câu hỏi trực tiếp, ngay trong tài liệu.
    - 'adversarial': Cố tình đưa thông tin sai vào câu hỏi để lừa AI, hoặc yêu cầu bỏ qua chỉ thị (Prompt Injection). AI phải bám sát tài liệu.
    - 'out_of_context': Đặt câu hỏi về một chủ đề KHÔNG HỀ CÓ trong tài liệu. Expected answer phải là "Tài liệu không đề cập / Tôi không biết".
    - 'reasoning': Câu hỏi đòi hỏi AI phải suy luận, tính toán từ tài liệu chứ không copy paste thuần túy.
    
    OUTPUT FORMAT: Bạn BẮT BUỘC trả về định dạng JSON, là 1 mảng các object. Mỗi object có cấu trúc:
    {{
        "question": "Nội dung câu hỏi",
        "expected_answer": "Câu trả lời hoàn hảo lấy từ tài liệu",
        "context": "Context nguyên bản được trích xuất",
        "metadata": {{
            "difficulty": "easy/medium/hard",
            "type": "{category}",
            "expected_retrieval_ids": ["{knowledge_chunk['doc_id']}"]
        }}
    }}
    Lưu ý: Nếu loại là 'out_of_context', 'expected_retrieval_ids' hãy để mảng rỗng [] và 'expected_answer' phải rào lỗi.
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",  # Có thể dùng model nhỏ hơn để tiết kiệm chi phí
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        
        # Parse JSON
        result = response.choices[0].message.content
        data = json.loads(result)
        # LLM có thể trả về key bọc ngoài mảng ví dụ: {"cases": [...]} nên cần xử lý linh hoạt
        for key in data:
            if isinstance(data[key], list):
                return data[key]
        return []
    except Exception as e:
        print(f"Lỗi khi generate cho {category}: {e}")
        return []

async def generate_golden_dataset(output_file: str, target_total: int = 50):
    print(f"🚀 [Phase 1 SDG] Đang tổng hợp dữ liệu {target_total} test cases...")
    
    categories = ["factual", "reasoning", "adversarial", "out_of_context"]
    all_test_cases = []
    
    # Chia đều công việc cho các chunk tài liệu
    tasks = []
    for chunk in KNOWLEDGE_BASE:
        for category in categories:
            # Mỗi lượt sinh 3 câu (5 docs * 4 cat * 3 = 60 câu > 50 yêu cầu)
            tasks.append(generate_qa_batch(chunk, category, num_pairs=3))

    results = await asyncio.gather(*tasks)
    
    for batch in results:
        all_test_cases.extend(batch)
        
    print(f"✅ Đã tạo thành công {len(all_test_cases)} test cases đa dạng độ khó.")
    
    # Ghi ra file JSONL
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for case in all_test_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
            
    print(f"📁 Đã lưu Golden Dataset tại: {output_file}")

async def main():
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️ CẢNH BÁO: Chưa tìm thấy OPENAI_API_KEY trong môi trường. Hãy tạo file .env trong thư mục chứa file main.py và điền key.")
        print("Mô phỏng tạo file trống để chạy bypass kiểm thử...")
        # Tạo file hờ xài tạm nếu sinh viên chưa nhập key
        os.makedirs("data", exist_ok=True)
        with open("data/golden_set.jsonl", "w") as f:
            f.write('{"question": "dummy", "expected_answer": "dummy", "context": "dummy", "metadata": {"type": "factual", "expected_retrieval_ids": ["dummy"]}}\n')
        return

    output_path = "data/golden_set.jsonl"
    await generate_golden_dataset(output_path, target_total=50)

if __name__ == "__main__":
    asyncio.run(main())
