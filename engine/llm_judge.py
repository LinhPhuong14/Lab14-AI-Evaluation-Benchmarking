import asyncio
import json
import os
from typing import Dict, Any
from openai import AsyncOpenAI
import google.generativeai as genai
from dotenv import load_dotenv

# Load môi trường (API Keys)
load_dotenv()

class LLMJudge:
    def __init__(self, openai_model: str = "gpt-4o-mini", gemini_model: str = "gemini-2.0-flash-lite"):
        # Setup OpenAI
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = AsyncOpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        self.openai_model = openai_model
        
        # Setup Gemini
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
        self.gemini_model_name = gemini_model
        
        # TODO: Định nghĩa rubrics chi tiết cho các tiêu chí: Accuracy, Professionalism, Safety
        self.rubrics = {
            "accuracy": (
                "Accuracy (1-5): Đánh giá xem câu trả lời có chính xác về mặt thông tin so với Ground Truth không. "
                "5: Hoàn toàn chính xác. 4: Có lỗi nhỏ hoặc thiếu sót không đáng kể. 3: Thiếu thông tin quan trọng nhưng phần lớn vẫn đúng. "
                "2: Nhiều lỗi sai hoặc có hiện tượng ảo giác (hallucination). 1: Hoàn toàn sai hoặc không liên quan."
            ),
            "tone": (
                "Tone (1-5): Đánh giá sự chuyên nghiệp và thái độ của phản hồi. "
                "5: Rất chuyên nghiệp, lịch sự và hữu ích. 4: Chuyên nghiệp nhưng hơi khô khan. "
                "3: Bình thường/Đạt tiêu chuẩn. 2: Hơi thiếu chuyên nghiệp hoặc giống robot. "
                "1: Thô lỗ hoặc không phù hợp."
            )
        }

    async def _call_openai(self, prompt: str) -> Dict[str, Any]:
        """Gọi OpenAI GPT để chấm điểm."""
        if not self.openai_client:
            return {"accuracy": 3, "tone": 3, "reasoning": "OpenAI API Key missing"}
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert AI evaluator. Use JSON format only."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            return {"accuracy": 3, "tone": 3, "reasoning": f"OpenAI Error: {str(e)}"}

    async def _call_gemini(self, prompt: str) -> Dict[str, Any]:
        """Gọi Google Gemini để chấm điểm."""
        if not self.gemini_api_key:
            return {"accuracy": 3, "tone": 3, "reasoning": "Gemini API Key missing"}
        
        try:
            model = genai.GenerativeModel(self.gemini_model_name)
            # Gemini 1.5 hỗ trợ JSON mode qua generation_config
            response = await model.generate_content_async(
                prompt + "\n\nIMPORTANT: Return ONLY a valid JSON object.",
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json"
                )
            )
            return json.loads(response.text)
        except Exception as e:
            # Fallback nếu JSON mode fail hoặc không hỗ trợ ở model cũ
            try:
                model = genai.GenerativeModel(self.gemini_model_name)
                response = await model.generate_content_async(prompt)
                content = response.text
                
                # Robust extraction: find the first '{' and last '}'
                try:
                    start_idx = content.find('{')
                    end_idx = content.rfind('}') + 1
                    if start_idx != -1 and end_idx != -1:
                        json_str = content[start_idx:end_idx]
                        return json.loads(json_str)
                except:
                    if "```json" in content:
                        content = content.split("```json")[1].split("```")[0].strip()
                        return json.loads(content)
                
                return {"accuracy": 3, "tone": 3, "reasoning": f"Gemini Parsing Error: {content[:50]}"}
            except:
                return {"accuracy": 3, "tone": 3, "reasoning": f"Gemini Error: {str(e)}"}

    async def evaluate_multi_judge(self, question: str, answer: str, ground_truth: str) -> Dict[str, Any]:
        """
        EXPERT TASK: Gọi ít nhất 2 model (ví dụ GPT-4o và Gemini).
        Tính toán sự sai lệch. Nếu lệch > 1 điểm, cần logic xử lý.
        """
        prompt = f"""
Evaluate the following AI assistant's response.
Question: {question}
Answer: {answer}
Ground Truth: {ground_truth}

Rubrics:
- {self.rubrics['accuracy']}
- {self.rubrics['tone']}

Return ONLY a JSON object with this structure:
{{
  "accuracy": <int 1-5>,
  "tone": <int 1-5>,
  "reasoning": "<string concise explanation>"
}}
"""
        # Gọi 2 model song song
        res_openai_task = self._call_openai(prompt)
        res_gemini_task = self._call_gemini(prompt)
        
        res_openai, res_gemini = await asyncio.gather(res_openai_task, res_gemini_task)
        
        # Trích xuất điểm (mặc định 3 nếu thiếu hoặc lỗi)
        score_a_acc = res_openai.get("accuracy", 3)
        score_b_acc = res_gemini.get("accuracy", 3)
        score_a_tone = res_openai.get("tone", 3)
        score_b_tone = res_gemini.get("tone", 3)
        
        # Consensus Logic: Tính trung bình cộng + Xử lý xung đột
        avg_acc = (score_a_acc + score_b_acc) / 2
        avg_tone = (score_a_tone + score_b_tone) / 2
        
        # Xử lý xung đột (Expert Conflict Resolution)
        # Nếu lệch > 1 điểm, sử dụng phương pháp Conservative (lấy điểm thấp hơn)
        consensus_note = "Strong agreement."
        if abs(score_a_acc - score_b_acc) > 1:
            avg_acc = min(score_a_acc, score_b_acc)
            consensus_note = f"Major disagreement in Accuracy (Gap: {abs(score_a_acc - score_b_acc)}). Using conservative score."
        
        final_score = round((avg_acc + avg_tone) / 2, 2)
        
        # Agreement Rate: 1.0 nếu lệch <= 1, 0.5 nếu lệch > 1, 0.0 nếu lệch >= 3
        diff = abs(score_a_acc - score_b_acc)
        if diff <= 1:
            agreement = 1.0
        elif diff <= 2:
            agreement = 0.5
        else:
            agreement = 0.0
            
        return {
            "final_score": final_score,
            "agreement_rate": agreement,
            "consensus_note": consensus_note,
            "individual_scores": {
                "openai": {"accuracy": score_a_acc, "tone": score_a_tone, "reasoning": res_openai.get("reasoning")},
                "gemini": {"accuracy": score_b_acc, "tone": score_b_tone, "reasoning": res_gemini.get("reasoning")}
            }
        }

    async def check_position_bias(self, question: str, response_a: str, response_b: str):
        """
        Nâng cao: Thực hiện đổi chỗ response A và B để xem Judge có thiên vị vị trí không.
        Đây là kỹ thuật chuyên sâu để đảm bảo tính khách quan của Judge model.
        """
        # Logic: 
        # 1. Prompt Judge chấm điểm cặp (A, B)
        # 2. Prompt Judge chấm điểm cặp (B, A)
        # 3. So sánh kết quả. Nếu Judge luôn chọn phương án đầu tiên bất kể nội dung -> Position Bias.
        # Với bài toán Lab 14, focus chính là evaluate Single Answer so với Ground Truth.
        pass

if __name__ == "__main__":
    async def test():
        judge = LLMJudge()
        res = await judge.evaluate_multi_judge(
            "VinUni yêu cầu bao nhiêu tín chỉ?",
            "Sinh viên cần 100 tín chỉ để tốt nghiệp.",
            "Quy chế yêu cầu tối thiểu 120 tín chỉ."
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        
    asyncio.run(test())
