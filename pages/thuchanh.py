import streamlit as st
import google.generativeai as genai
import json
import re
import time
import random
import textwrap
import html
import os
import requests
from PIL import Image
from io import BytesIO

# Thư viện Word
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Thư viện PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

# ==========================================
# 1. CẤU HÌNH & CSS (GIỮ NGUYÊN)
# ==========================================
st.set_page_config(page_title="IELTS Writing Master", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Merriweather:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header {
        font-family: 'Merriweather', serif;
        color: #0F172A;
        font-weight: 700;
        font-size: 2.2rem;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-family: 'Inter', sans-serif;
        color: #64748B;
        font-size: 1.1rem;
        margin-bottom: 2rem;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 1rem;
    }
    .step-header {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.2rem;
        color: #1E293B;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .guide-box {
        background-color: #f8f9fa;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: #31333F;
    }
    .error-card {
        background-color: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.2s;
    }
    .annotated-text {
        font-family: 'Merriweather', serif;
        line-height: 1.8;
        color: #374151;
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
    }
    del { color: #9CA3AF; text-decoration: line-through; margin-right: 4px; text-decoration-thickness: 2px; }
    ins.grammar { background-color: #4ADE80; color: #022C22; text-decoration: none; padding: 2px 6px; border-radius: 4px; font-weight: 700; border: 1px solid #22C55E; }
    ins.vocab { background-color: #FDE047; color: #000; text-decoration: none; padding: 2px 6px; border-radius: 4px; font-weight: 700; border: 1px solid #FCD34D; }
    
    div.stButton > button {
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIC AI (GIỮ NGUYÊN)
# ==========================================
try:
    ALL_KEYS = st.secrets["GEMINI_API_KEYS"]
except Exception:
    st.error("⚠️ Chưa cấu hình secrets.toml chứa GEMINI_API_KEYS!")
    st.stop()

def generate_content_with_failover(prompt, image=None, json_mode=False):
    keys_to_try = list(ALL_KEYS)
    random.shuffle(keys_to_try) 
    model_priority = ["gemini-2.0-flash-thinking-preview-01-21", "gemini-3-flash-preview", "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
    
    for current_key in keys_to_try: 
        try:
            genai.configure(api_key=current_key)
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            sel_model = None
            for target in model_priority:
                if any(target in m_name for m_name in available_models):
                    sel_model = target
                    break
            if not sel_model: sel_model = "gemini-1.5-flash" 

            temp_model = genai.GenerativeModel(model_name=sel_model)
            content_parts = [prompt]
            if image: content_parts.append(image)
            
            gen_config = {"temperature": 0.3, "top_p": 0.95, "top_k": 64, "max_output_tokens": 32000}
            if json_mode and "thinking" not in sel_model.lower():
                gen_config["response_mime_type"] = "application/json"
            
            if "thinking" in sel_model.lower():
                 gen_config["thinking_config"] = {"include_thoughts": True, "thinking_budget": 1024}

            response = temp_model.generate_content(content_parts, generation_config=gen_config)
            return response, sel_model 
        except Exception:
            continue
    return None, None

# ==========================================
# 3. PROMPT KHỦNG (RESTORE 100% - KHÔNG XÓA DÒNG NÀO)
# ==========================================
GRADING_PROMPT_TEMPLATE = """
Bạn hãy đóng vai trò là một Giám khảo IELTS với 30 năm kinh nghiệm làm việc tại Hội đồng Anh (British Council). Nhiệm vụ của bạn là đánh giá bài viết dựa trên **bộ tiêu chí chuẩn xác của IELTS Writing Task 1 (Band Descriptors)**. 
**Phân loại bài thi (Context Awareness):** Bắt buộc phải nhận diện đây là IELTS Academic: Biểu đồ/Đồ thị/Quy trình/Map. Đề bài nói về nội dung gì.
**Yêu cầu khắt khe:** Bạn phải sử dụng **tiêu chuẩn của Band 9.0 làm thước đo tham chiếu cao nhất** để soi xét bài làm. Hãy thực hiện một bản "Gap Analysis" chi tiết: chỉ ra mọi thiếu sót một cách nghiêm ngặt và chính xác tuyệt đối, từ những lỗi sai căn bản cho đến những điểm chưa đạt được độ tinh tế của một bài viết điểm tuyệt đối.
**YÊU CẦU ĐẶC BIỆT (CHẾ ĐỘ KIỂM TRA KỸ):** Bạn không cần phải trả lời nhanh. Hãy dành thời gian "suy nghĩ" để phân tích thật sâu và chi tiết (Step-by-step Analysis).

### 1. TƯ DUY & GIAO THỨC LÀM VIỆC (CORE PROTOCOL)
* **>> GIAO THỨC PHÂN TÍCH CHẬM (SLOW REASONING PROTOCOL):**
    * Bạn không được phép tóm tắt nhận xét. Với mỗi tiêu chí, bạn phải viết ít nhất 200-300 từ.
    * Bạn phải thực hiện phân tích theo phương pháp "Socratic": Đặt câu hỏi về từng câu văn của thí sinh, tìm ra điểm chưa hoàn hảo và giải thích cặn kẽ tại sao nó chưa đạt Band 7.0 hoặc Band 9.0 từ dữ liệu bài viết này.
    * Cấm dùng các cụm từ chung chung như "Good grammar" hay "Appropriate vocabulary". Bạn phải trích dẫn ít nhất 3-5 ví dụ thực tế từ bài làm cho mỗi tiêu chí để chứng minh cho nhận định của mình.
*   **Persona:** Giám khảo lão làng, khó tính nhưng công tâm. Tông giọng phản hồi trực diện, không khen ngợi sáo rỗng. Nếu bài tệ, phải nói rõ là tệ.
*   **>> NGUYÊN TẮC "HOLISTIC SCORING" (Chấm điểm tổng hòa):** 
    *   Tuyệt đối phân biệt giữa **Lỗi hệ thống (Systematic error)** và **Lỗi trượt chân (Slip)**.
    *   *Lỗi trượt chân (Slip):* Là lỗi nhỏ, ngẫu nhiên (như viết thiếu 1 chữ cái, thừa 1 từ so sánh). Nếu bài viết thể hiện trình độ từ vựng/ngữ pháp xuất sắc, những lỗi này **KHÔNG ĐƯỢC** dùng làm lý do để hạ điểm từ 8 xuống 7 hoặc từ 9 xuống 8.
*   **Chế độ "Deep Scan":** Không trả lời nhanh. Hãy dành thời gian phân tích từng câu, từng từ theo quy trình "Step-by-step Analysis".
*   **Quy tắc "Truy quét kiệt quệ" (Exhaustive Listing):**
    *   Tuyệt đối KHÔNG gộp lỗi. Nếu thí sinh sai 10 lỗi mạo từ, liệt kê đủ 10 mục.
    *   Danh sách lỗi trong JSON là bằng chứng pháp lý. Mọi lỗi nhỏ nhất (dấu phẩy, viết hoa, mạo từ) đều phải được ghi nhận. Nếu JSON ít lỗi mà điểm GRA thấp, đó là một sự mâu thuẫn nghiêm trọng.
    *   **>> BỔ SUNG QUY TẮC TAXONOMY:** Khi phân loại lỗi trong JSON, chỉ được sử dụng các thuật ngữ chuẩn mực (ví dụ: Subject-Verb Agreement, Collocation, Article, Comma Splice). TUYỆT ĐỐI KHÔNG sáng tạo ra tên lỗi lạ (như "Bad word", "Wrong grammar").
*   **Nhận diện ngữ cảnh (Context Awareness):** Tự xác định là Academic (Biểu đồ/Process/Map) hay General Training (Thư) để áp dụng Band Descriptors tương ứng.
* **>> GIAO THỨC QUÉT 2 LỚP (TWO-PASS SCANNING):**
    * Lớp 1: Tìm các lỗi nặng (Cấu trúc, từ vựng sai ngữ cảnh, logic dữ liệu).
    * Lớp 2: Quét lại toàn bộ bài để tìm các lỗi nhỏ (Mạo từ, số ít/nhiều, dấu câu, viết hoa). 
    * Chỉ sau khi hoàn thành 2 lớp quét này mới được lập danh sách lỗi cuối cùng.
*   **>> NGUYÊN TẮC "APPROXIMATION TOLERANCE":** 
    *   Đối với các số liệu rất nhỏ (< 2-3%), chấp nhận các từ ngữ ước lượng mạnh như *"virtually no"*, *"almost zero"*, *"negligible"*. Đừng coi đây là lỗi sai dữ liệu (Logic Error) trừ khi số liệu thực tế > 5%.    

### 2. TIÊU CHÍ CHẤM ĐIỂM CHI TIẾT (4 CRITERIA)
#### A. Task Achievement (TA)
*   **Tư duy dữ liệu & Nhóm thông tin (Logical Grouping):**
    *   **Band 8.0+:** Thí sinh PHẢI biết nhóm các đối tượng tương đồng vào cùng đoạn văn một cách thông minh (Skilfully selected). Nếu chỉ liệt kê máy móc -> Tối đa Band 6-7.
    *   **>> BỔ SUNG QUY TẮC CHẶN BAND 6 (Comparison Rule):** Nếu bài viết chỉ mô tả đơn lẻ (description) số liệu của từng đối tượng mà KHÔNG CÓ sự so sánh (comparison) tương quan giữa các đối tượng -> **TỐI ĐA BAND 6.0** (Dù mô tả đúng 100%).
    *   **>> BỔ SUNG QUY TẮC "TOTAL/OTHER" (Safety Net):** Các hạng mục như 'Total', 'Miscellaneous', 'Other' KHÔNG ĐƯỢC tính là Key Features bắt buộc. Nếu thí sinh bỏ qua các số liệu này, HOÀN TOÀN KHÔNG ĐƯỢC TRỪ ĐIỂM. (Cảnh báo: Nếu trừ điểm lỗi này là sai quy chế).
*   **Độ dài & Sự súc tích (Word Count vs Conciseness):**
    *   **Không phạt oan:** Nếu bài > 200 từ nhưng thông tin đắt giá, số liệu chính xác 100% -> KHÔNG hạ điểm TA.
    *   `>> ƯU TIÊN "DATA SYNTHESIZING": Đánh giá cao nếu thí sinh biết biến số liệu % thành phân số (fractions) hoặc các cụm từ ước lượng (rounding) thay vì chỉ liệt kê số liệu thô từ bảng.`
    *   **Chỉ trừ điểm khi:** Bài viết dài dòng do lặp ý (Repetitive) hoặc lan man (Irrelevant). Nếu > 200 từ mà nội dung tốt, chỉ đưa vào phần "Lời khuyên" là nên cô đọng hơn.
    *   **Hình phạt:** < 150 từ (đánh giá khắt khe TA), < 20 từ (Band 1).
*   **Các bẫy "Chết người" (Negative Features - TA):**
    *   **Object vs Figure:** Phạt nặng lỗi sai chủ ngữ (VD: "The figure of apple rose" -> Sai; "The consumption of apple rose" -> Đúng).
    *   **Nhầm đơn vị:** Đề là % mà viết là Number -> Chặn đứng ở Band 5.0 TA.
    *   **No Data/Support:** Academic mà mô tả không có số liệu đi kèm -> Band 5.0.
    *   **Band 5 (Nguy hiểm):** Nếu mô tả xu hướng mà **không có số liệu (data)** đi kèm -> BẮT BUỘC hạ xuống Band 5 (Theo dòng in đậm: "There may be no data to support the description").
    *   **Overview:** Process phải đủ "Đầu-Giữa-Cuối"; Map phải có "Sự thay đổi tổng quan". Sai/Thiếu Overview -> Tối đa Band 5-6.
    *   **Band 7:** Phải xác định được xu hướng chính/sự khác biệt rõ ràng (Clear overview).
    *   **Band 6:** Có nỗ lực viết Overview nhưng thông tin chọn lọc sai hoặc không rõ ràng.
    *   **Band 5:** Không có Overview hoặc Overview sai lệch hoàn toàn.
    *   **Ý kiến cá nhân:** Tuyệt đối cấm. Có ý kiến cá nhân -> Trừ điểm nặng.
*   **>> BỔ SUNG QUY TẮC FORMAT & TONE:**
        *   **Lỗi định dạng (Format):** Nếu bài viết dùng gạch đầu dòng (bullet points) hoặc đánh số (1, 2, 3) thay vì viết đoạn văn -> **TỐI ĐA BAND 5.0 TA**.
        *   **Lỗi giọng điệu (Tone - GT):** Nếu đề yêu cầu "Formal letter" mà dùng ngôn ngữ suồng sã (slang, contractions like "gonna") -> Trừ điểm nặng xuống **Band 5.0-6.0**.
*   **Math Logic Check:** Soi kỹ các từ chỉ mức độ (slight, significant). Ví dụ: Từ 10% lên 15% là tăng gấp rưỡi -> Cấm dùng "slight".
*   **Endpoint Trap:** Cấm dùng "peak" cho năm cuối cùng của biểu đồ (vì không biết tương lai). Gợi ý: "ending at a high".
*   **>> CHIẾN THUẬT OVERVIEW BAND 8.0-9.0 (BẮT BUỘC ĐỐI CHIẾU):**
    1.  **Nguyên tắc "No Data":** Overview đạt Band cao TUYỆT ĐỐI không được chứa số liệu chi tiết. 
    2.  **Cấu trúc "Double Content":** Phải bao quát được cả (1) Xu hướng chính (Trends) VÀ (2) Sự so sánh nổi bật nhất (Major Comparisons/High-lows).
    3.  **Kỹ thuật Synthesis:** Đánh giá xem học sinh có biết gộp các đối tượng tương đồng để khái quát hóa không, hay chỉ đang liệt kê.
    4.  **Vị trí:** Khuyên học sinh đặt ngay sau Introduction để tạo luồng logic.
#### B. Coherence & Cohesion (CC)
*   **Liên kết "Vô hình" (Invisible Cohesion - Band 9):** Ưu tiên các cấu trúc "respectively", "in that order", mệnh đề quan hệ rút gọn.
*   **Mechanical Linkers (Lỗi máy móc):** Nếu câu nào cũng bắt đầu bằng "First, Second, In addition, Furthermore" -> Tối đa Band 6.0.
*   **Paragraphing:** Bài viết phải chia đoạn logic. Chỉ có 1 đoạn văn -> CC tối đa 5.0.
*   **>> BỔ SUNG QUY TẮC "AMBIGUOUS REFERENCING" (The 'It' Trap):**
        *   Kiểm tra kỹ các đại từ thay thế (It, This, That, These, Those). Nếu dùng các từ này mà KHÔNG RÕ thay thế cho danh từ nào trước đó (gây khó hiểu) -> **TỐI ĐA BAND 6.0 CC**.
*   **>> QUY TẮC "INVISIBLE GLUE" (Keo dán vô hình):**
        *   Soi kỹ các từ dẫn đầu đoạn (Signposting words). Nếu thí sinh dùng lặp lại các từ như "Regarding...", "As for...", "Turning to..." quá 2 lần -> Đánh dấu là "Mechanical" (Máy móc).
        *   Khuyến khích cách chuyển đoạn bằng chủ ngữ ẩn hoặc Reference (Ví dụ: Thay vì "Regarding A, it increased...", hãy viết "A, conversely, witnessed a rise...").
*   **>> NGUYÊN TẮC LINH HOẠT CC:** Nếu bài viết có logic tốt và dễ hiểu, việc sử dụng từ nối hơi máy móc (như "Regarding") KHÔNG NÊN kéo điểm xuống 7.0 ngay lập tức. Hãy cân nhắc Band 8.0 nếu dòng chảy thông tin (flow) vẫn mượt mà. Chỉ hạ xuống 7.0 nếu việc dùng từ nối gây khó chịu hoặc làm gián đoạn việc đọc.
*   **>> YÊU CẦU OUTPUT CHO PHẦN NÀY:**
    *   **Trích dẫn chứng:** Phải trích dẫn câu văn cụ thể của thí sinh để phân tích.
    *   **Gợi ý "Vừa sức":** 
        *   Bài dưới Band 7 -> Gợi ý sửa cho ĐÚNG.
        *   Bài Band 7+ -> Gợi ý sửa cho HAY (Band 9).
#### C. Lexical Resource (LR)
*   **Naturalness over Academic:** Ưu tiên từ vựng tự nhiên (use, help, start) hơn là từ đao to búa lớn sai ngữ cảnh (utilise, facilitate, commence).
*   **Blacklist:** Cảnh báo các từ sáo rỗng/học thuộc lòng bị lạm dụng.
*   **Precision:** Soi kỹ Collocation (VD: "increased significantly" > "increased strongly").
*   **>> BỔ SUNG QUY TẮC "REPETITION" (Lặp từ):**
        *   Nếu một từ vựng quan trọng (ví dụ: "increase", "fluctuate") bị lặp lại > 3 lần mà không có nỗ lực thay thế (paraphrase) -> **TỐI ĐA BAND 5.0 LR** (Lỗi "Limited flexibility").
    *   **>> QUY TẮC CHÍNH TẢ (Spelling Threshold):**
        *   Sai 1-2 lỗi nhỏ -> Vẫn có thể Band 8.
        *   Sai vài lỗi (A few) nhưng vẫn hiểu được -> Band 7.
        *   Sai nhiều lỗi (Noticeable) nhưng vẫn hiểu được -> Band 6.
        *   Sai gây khó hiểu (Impede meaning) -> Band 5.
*   **>> NGUYÊN TẮC "NO DOUBLE PENALIZATION" (Không phạt kép):**
        *   Nếu lỗi thuộc về Redundancy (thừa từ: *most highest*) hoặc Spelling (*fluctation*), hãy tính nó vào điểm Lexical Resource (LR).
        *   KHÔNG trừ điểm Grammatical Range (GRA) cho những lỗi đã tính ở LR, trừ khi nó làm sai cấu trúc câu nghiêm trọng. Đây là lý do tại sao một bài có lỗi từ vựng vẫn có thể đạt 9.0 GRA nếu cấu trúc câu phức tạp và đa dạng.
*   **Word Choice:** Ưu tiên "Proportion" cho dữ liệu nhân lực/dân số. "Percentage" chỉ là con số thuần túy.
*   **Precision:** "Chosen one" -> Sai style. Sửa thành "Popular sector".
#### D. Grammatical Range & Accuracy (GRA)
*   **Độ chính xác tuyệt đối:** Soi kỹ từng lỗi mạo từ, giới từ, số ít/nhiều.
*   **Tỷ lệ câu không lỗi (Error-free sentences):**
    *   Band 6: Có lỗi nhưng không quá khó hiểu.
    *   Band 7: Câu không lỗi xuất hiện thường xuyên (Frequent).
    *   Band 8+: Đa số các câu hoàn toàn sạch lỗi (Majority error-free).
*   **Các lỗi kỹ thuật:**
    *   **Comma Splice:** Dùng dấu phẩy nối hai mệnh đề độc lập -> Kéo điểm xuống Band 5-6.
    *   **The Mad Max:** Lạm dụng hoặc thiếu mạo từ "the".
    *   **Past Perfect Trigger:** Thấy "By + [thời gian quá khứ]" mà không dùng Quá khứ hoàn thành -> Đánh dấu yếu kém về Range.
    *   **>> BỔ SUNG QUY TẮC DẤU CÂU (Punctuation Control):** Ngoài Comma Splice, nếu bài viết thường xuyên thiếu dấu phẩy ngăn cách mệnh đề phụ (Subordinate clause), hoặc viết hoa tùy tiện -> **KHÔNG ĐƯỢC CHẤM BAND 8.0 GRA**.
*   **>> CHIẾN THUẬT PARAPHRASING (Introduction Strategy):**
        *   Kiểm tra câu mở đầu (Introduction). Nếu thí sinh chỉ thay từ đồng nghĩa (synonyms) trong cụm danh từ (Noun Phrase), hãy đánh giá ở mức "Standard".
        *   Nếu thí sinh chuyển đổi được cấu trúc từ Noun Phrase (*the number of...*) sang Noun Clause (*how many...*), hãy ghi nhận đây là điểm cộng lớn cho Band 8+ GRA.
*   **Band 9 Threshold:** Nếu bài viết dùng câu phức hay và tự nhiên, cho phép 1-2 lỗi nhỏ (slips). Đừng kẹt ở Band 8.0 chỉ vì một lỗi mạo từ.
*   **>> NGUYÊN TẮC "SLIPS" TRONG GRA:** Band 9.0 GRA cho phép "rare minor errors" (các lỗi nhỏ hiếm gặp). Nếu bài viết sử dụng nhiều cấu trúc phức tạp một cách tự nhiên, đừng ngần ngại cho 9.0 dù vẫn còn 1-2 lỗi mạo từ hoặc số ít/nhiều. Đừng máy móc chặn ở 8.0.
*   **>> GIAO THỨC "PREPOSITION MICRO-SCANNING" (Soi Giới từ Chết người):**
    *   Sau khi quét toàn bộ bài viết, hãy thực hiện một lượt quét **thứ hai** chỉ để tìm lỗi giới từ đi kèm với số liệu và xu hướng.
    *   **To:** Dùng cho điểm đến cuối cùng (VD: "recovered **to** 15%").
    *   **At:** Dùng cho một điểm cố định (VD: "stood **at** 10%").
    *   **Of:** Dùng để chỉ giá trị của một danh từ (VD: "a level **of** 15%").
    *   **In:** Dùng cho năm (VD: "**in** 2015").
    *   **By:** Dùng để chỉ một lượng thay đổi (VD: "decreased **by** 5%").
    *   **BẮT BUỘC:** Nếu thí sinh dùng sai bất kỳ giới từ nào trong các trường hợp trên (ví dụ: dùng "at" hoặc "by" thay vì "to"), hãy bắt lỗi **"Preposition Error"** và giải thích rõ quy tắc sử dụng. Đây là lỗi cơ bản nhưng làm mất điểm rất nặng.
    
### 3. QUY TRÌNH CHẤM ĐIỂM & TỰ SỬA LỖI (SCORING & SELF-CORRECTION)

Mọi từ hoặc dấu câu nằm trong thẻ `<del>...</del>` ở bản sửa **BẮT BUỘC** phải có một mục nhập (entry) riêng biệt tương ứng trong danh sách `errors`. Tuyệt đối không được tóm tắt hay gộp lỗi.
**Bước 1: Deep Scan & Lập danh sách lỗi (JSON Errors Array)**
**Bước 2: Tạo bản sửa lỗi (Annotated Essay)**
**Bước 3: Chấm lại bản sửa lỗi (JSON Output - Internal Re-grading)**

Sau khi đánh giá xong (viết phần phân tích chi tiết bằng lời văn), bạn **BẮT BUỘC** phải trích xuất dữ liệu kết quả cuối cùng dưới dạng một **JSON Object duy nhất** ở cuối câu trả lời.

Cấu trúc JSON:
```json
{
  "original_score": {
      "task_achievement": "...", "cohesion_coherence": "...", "lexical_resource": "...", "grammatical_range": "...", "overall": "..."
  },
  "detailed_analysis": {
      "task_achievement": "...", "cohesion_coherence": "...", "lexical_resource": "...", "grammatical_range": "..."
  },
  "errors": [
    { "category": "Grammar" hoặc "Vocabulary", "type": "Tên Lỗi", "impact_level": "High" | "Medium" | "Low", "explanation": "...", "original": "...", "correction": "..." }
  ],
  "annotated_essay": "...",
   "revised_score": {
      "word_count_check": "...", "logic_re_evaluation": "...", "task_achievement": "...", "cohesion_coherence": "...", "lexical_resource": "...", "grammatical_range": "...", "overall": "..."
  }
}
```

Thông tin bài làm:
a/ Đề bài (Task 1 question): {{TOPIC}}
b/ Bài làm của thí sinh (Written report): {{ESSAY}}
"""

# ==========================================
# 4. HELPER FUNCTIONS
# ==========================================

def clean_json(text):
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match: return match.group(1).strip()
    match_raw = re.search(r"\{[\s\S]*\}", text)
    if match_raw: return match_raw.group(0).strip()
    return None

def parse_guide_response(text):
    try:
        j_str = clean_json(text)
        return json.loads(j_str) if j_str else None
    except: return None

def process_grading_response(full_text):
    """Deep Search: Quét toàn bộ JSON để tìm nội dung phân tích chi tiết"""
    json_str = clean_json(full_text)
    data = {"errors": [], "annotatedEssay": None, "revisedScore": None, "originalScore": {}, "analysisMarkdown": ""}
    
    if json_str:
        try:
            parsed = json.loads(json_str)
            data.update(parsed)
            data["originalScore"] = parsed.get("original_score", {})
            data["annotatedEssay"] = parsed.get("annotated_essay")
            data["revisedScore"] = parsed.get("revised_score")
            
            sections = []
            sources = [parsed, parsed.get("detailed_analysis", {}), parsed.get("original_score", {}), parsed.get("analysis", {})]
            keywords = {
                "Task Achievement": ["task_achievement", "ta_gap", "ta_analysis", "achievement"],
                "Coherence & Cohesion": ["cohesion", "cc_gap", "cc_analysis", "coherence"],
                "Lexical Resource": ["lexical", "lr_gap", "lr_analysis", "vocabulary"],
                "Grammatical Range": ["grammatical", "gra_gap", "gra_analysis", "grammar"]
            }

            used_keys = set()
            for title, kw_list in keywords.items():
                found = False
                for src in sources:
                    if not isinstance(src, dict): continue
                    for k, v in src.items():
                        if any(kw in k.lower() for kw in kw_list) and isinstance(v, str) and len(v) > 50 and k not in used_keys:
                            sections.append(f"### 📘 {title}\n{v}")
                            used_keys.add(k)
                            found = True; break
                    if found: break
            
            if sections: data["analysisMarkdown"] = "\n\n".join(sections)
            elif parsed.get("analysis_markdown"): data["analysisMarkdown"] = parsed["analysis_markdown"]
        except:
             data["analysisMarkdown"] = full_text.split("```json")[0]
             
    if not data["analysisMarkdown"]: 
        data["analysisMarkdown"] = full_text.split("```json")[0]
    return data

# --- FILE EXPORT ---
def register_vietnamese_font():
    try:
        f_reg, f_bold = "Roboto-Regular.ttf", "Roboto-Bold.ttf"
        if not os.path.exists(f_reg):
            r = requests.get("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf")
            with open(f_reg, "wb") as f: f.write(r.content)
        if not os.path.exists(f_bold):
            r = requests.get("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf")
            with open(f_bold, "wb") as f: f.write(r.content)
        pdfmetrics.registerFont(TTFont('Roboto', f_reg))
        pdfmetrics.registerFont(TTFont('Roboto-Bold', font_bold))
        addMapping('Roboto', 0, 0, 'Roboto'); addMapping('Roboto', 1, 0, 'Roboto-Bold')
        return True
    except: return False

def create_docx(data, topic, essay, analysis):
    doc = Document()
    doc.add_heading('IELTS ASSESSMENT REPORT', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_heading('1. DETAILED ANALYSIS', level=1)
    doc.add_paragraph(analysis)
    buffer = BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

def create_pdf(data, topic, essay, analysis):
    register_vietnamese_font()
    buffer = BytesIO(); doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet(); elements = [Paragraph("IELTS ASSESSMENT REPORT", styles['Title']), Paragraph("DETAILED ANALYSIS", styles['Heading1'])]
    safe_text = html.escape(analysis).replace('\n', '<br/>')
    elements.append(Paragraph(safe_text, styles['Normal']))
    doc.build(elements); buffer.seek(0)
    return buffer

# ==========================================
# 5. QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ==========================================
if "step" not in st.session_state: st.session_state.step = 1 
if "guide_data" not in st.session_state: st.session_state.guide_data = None
if "grading_result" not in st.session_state: st.session_state.grading_result = None
if "saved_topic" not in st.session_state: st.session_state.saved_topic = ""
if "saved_img" not in st.session_state: st.session_state.saved_img = None

# ==========================================
# 6. GIAO DIỆN CHÍNH
# ==========================================
st.markdown('<div class="main-header">🎓 IELTS Writing Task 1 – Examiner-Guided</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Learning & Scoring Based on IELTS Band Descriptors</div>', unsafe_allow_html=True)

if st.session_state.step == 1:
    st.markdown('<div class="step-header">STEP 1 – Visual Data</div>', unsafe_allow_html=True)
    uploaded_image = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key="img_input", label_visibility="collapsed")
    if uploaded_image:
        img_data = Image.open(uploaded_image)
        st.image(img_data, width=400)
    else: img_data = None

    st.markdown("---")
    st.markdown('<div class="step-header">STEP 2 – Task 1 Question</div>', unsafe_allow_html=True)
    question_input = st.text_area("Question", height=150, placeholder="The chart below shows...", key="q_input", label_visibility="collapsed")

    st.markdown("---")
    st.markdown('<div class="step-header">STEP 3 – Examiner Focus</div>', unsafe_allow_html=True)
    st.markdown('<div style="background:#F1F5F9; padding:15px; border-radius:8px;">✓ Task type identification<br>✓ Key trends & overview logic<br>✓ Data selection & comparison<br>✓ Band scoring (TA – CC – LR – GRA)</div>', unsafe_allow_html=True)

    if st.button("🚀  Analyze & Guide (Start Learning)", type="primary", use_container_width=True):
        if not question_input or not img_data:
            st.warning("⚠️ Vui lòng nhập đề bài và tải ảnh lên.")
        else:
            st.session_state.saved_topic = question_input
            st.session_state.saved_img = img_data
            
            with st.spinner("AI Examiner đang phân tích biểu đồ..."):
                prompt_guide = """
                Bạn là một Siêu Giáo viên IELTS Writing (Band 9.0). Hãy phân tích hình ảnh và viết hướng dẫn chi tiết từng bước bằng Tiếng Việt (dùng thẻ HTML <ul>, <li>, <b> để trình bày).
                FORMAT JSON OUTPUT:
                { "task_type": "...", "intro_guide": "...", "overview_guide": "...", "body1_guide": "...", "body2_guide": "..." }
                """
                res, _ = generate_content_with_failover(prompt_guide + "\nĐề bài: " + question_input, img_data, json_mode=True)
                if res:
                    g_data = parse_guide_response(res.text)
                    if g_data:
                        st.session_state.guide_data = g_data
                        st.session_state.step = 2
                        st.rerun()

# --- STEP 2: WRITING PRACTICE ---
if st.session_state.step == 2 and st.session_state.guide_data:
    if not st.session_state.saved_topic or not st.session_state.saved_img:
        st.session_state.step = 1; st.rerun()
    
    data = st.session_state.guide_data
    col_left, col_right = st.columns([4, 6], gap="medium")
    
    with col_left:
        st.markdown("### 📄 Đề bài & Hình ảnh")
        st.markdown(f'<div style="background:#f8f9fa; padding:15px; border-radius:8px; border:1px solid #eee; font-style:italic;">{st.session_state.saved_topic}</div>', unsafe_allow_html=True)
        st.image(st.session_state.saved_img, use_container_width=True)
        st.info(f"📌 **Dạng bài:** {data.get('task_type')}")

    with col_right:
        def get_wc(k): return len(st.session_state.get(k, "").split())
        total_wc = sum(get_wc(k) for k in ["in_intro", "in_overview", "in_body1", "in_body2"])
        
        st.markdown(f'<div style="display:flex; justify-content:space-between;"><b>✍️ Bài làm của bạn</b><span style="color:#6B7280;">Word count: {total_wc}/150+</span></div>', unsafe_allow_html=True)

        def render_sec(title, g_key, i_key):
            st.markdown(f"##### {title}")
            with st.expander(f"💡 Hướng dẫn {title}"):
                st.markdown(f'<div class="guide-box">{data.get(g_key)}</div>', unsafe_allow_html=True)
            return st.text_area(title, height=150, key=i_key, label_visibility="collapsed")

        intro = render_sec("Introduction", "intro_guide", "in_intro")
        overview = render_sec("Overview", "overview_guide", "in_overview")
        body1 = render_sec("Body 1", "body1_guide", "in_body1")
        body2 = render_sec("Body 2", "body2_guide", "in_body2")

        if st.button("✨ Submit to Examiner Pro (Chấm điểm)", type="primary", use_container_width=True):
            if total_wc < 20: st.warning("⚠️ Bài viết quá ngắn.")
            else:
                with st.status("👨‍🏫 Examiner đang chấm bài...") as status:
                    full_essay = f"{intro}\n\n{overview}\n\n{body1}\n\n{body2}".strip()
                    prompt_grade = GRADING_PROMPT_TEMPLATE.replace('{{TOPIC}}', st.session_state.saved_topic).replace('{{ESSAY}}', full_essay)
                    res_grade, _ = generate_content_with_failover(prompt_grade, st.session_state.saved_img)
                    if res_grade:
                        mk, p_data = process_grading_response(res_grade.text)
                        st.session_state.grading_result = {"data": p_data, "markdown": mk, "essay": full_essay, "topic": st.session_state.saved_topic}
                        st.session_state.step = 3
                        status.update(label="✅ Đã chấm xong!", state="complete", expanded=False)
                        st.rerun()

# --- STEP 3: RESULTS ---
if st.session_state.step == 3 and st.session_state.grading_result:
    res = st.session_state.grading_result
    g_data, analysis_text = res["data"], res["markdown"]
    st.markdown("## 🛡️ EXAMINER ASSESSMENT REPORT")
    scores = g_data.get("originalScore", {})
    cols = st.columns(5)
    cols[0].metric("Task Achievement", scores.get("task_achievement", "-"))
    cols[1].metric("Coherence", scores.get("cohesion_coherence", "-"))
    cols[2].metric("Lexical", scores.get("lexical_resource", "-"))
    cols[3].metric("Grammar", scores.get("grammatical_range", "-"))
    cols[4].metric("OVERALL", scores.get("overall", "-"))
    
    st.markdown("---")
    t1, t2, t3, t4 = st.tabs(["📝 Phân tích", "🔴 Lỗi Ngôn ngữ", "🔵 Lỗi Logic", "✍️ Bài sửa"])
    with t1: st.markdown(analysis_text)
    with t2:
        micro = [e for e in g_data.get('errors', []) if e.get('category') in ['Grammar', 'Vocabulary', 'Ngữ pháp', 'Từ vựng']]
        for idx, err in enumerate(micro):
            badge = "#DCFCE7" if err.get('category') in ['Grammar','Ngữ pháp'] else "#FEF9C3"
            st.markdown(f'<div class="error-card"><b>#{idx+1} {err["type"]}</b><div style="background:{badge}; padding:8px; border-radius:5px;"><s>{err["original"]}</s> ➔ <b>{err["correction"]}</b></div><small><i>{err["explanation"]}</i></small></div>', unsafe_allow_html=True)
    with t3:
        macro = [e for e in g_data.get('errors', []) if e.get('category') not in ['Grammar', 'Vocabulary', 'Ngữ pháp', 'Từ vựng']]
        for err in macro: st.markdown(f'<div class="error-card" style="border-left:5px solid #3B82F6;"><b>{err["type"]}</b><br>{err["explanation"]}<br>Gợi ý: <b>{err["correction"]}</b></div>', unsafe_allow_html=True)
    with t4: st.markdown(f'<div class="annotated-text">{g_data.get("annotatedEssay", "")}</div>', unsafe_allow_html=True)

    st.markdown("---")
    rev = g_data.get("revised_score", {})
    if rev:
        st.subheader("📈 Dự báo điểm sau sửa")
        r_cols = st.columns(5)
        r_cols[0].metric("TA", rev.get("task_achievement", "-"))
        r_cols[1].metric("CC", rev.get("cohesion_coherence", "-"))
        r_cols[2].metric("LR", rev.get("lexical_resource", "-"))
        r_cols[3].metric("GRA", rev.get("grammatical_range", "-"))
        r_cols[4].metric("OVERALL", rev.get("overall", "-"))
    
    if st.button("🔄 Làm bài mới", use_container_width=True):
        for k in ["step", "guide_data", "grading_result", "saved_topic", "saved_img"]: st.session_state[k] = None
        st.session_state.step = 1; st.rerun()
