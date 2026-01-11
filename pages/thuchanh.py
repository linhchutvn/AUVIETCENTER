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
# 1. CẤU HÌNH & CSS
# ==========================================
st.set_page_config(page_title="IELTS Writing Master", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Merriweather:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    /* Header Style */
    .main-header {
        font-family: 'Merriweather', serif;
        color: #0F172A;
        font-weight: 700;
        font-size: 2.2rem;
        margin-bottom: 0rem;
    }
    .sub-header {
        font-family: 'Inter', sans-serif;
        color: #64748B;
        font-size: 1.1rem;
        margin-bottom: 1rem;
        border-bottom: 1px solid #E2E8F0;
        padding-bottom: 0.5rem;
    }

    /* Step Headers */
    .step-header {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 1.2rem;
        color: #1E293B;
        margin-top: 1.5rem;
        margin-bottom: 0.5rem;
    }
    .step-desc {
        font-size: 0.9rem;
        color: #64748B;
        margin-bottom: 0.8rem;
    }

    /* Guide Box */
    .guide-box {
        background-color: #f8f9fa;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: #31333F;
    }

    /* Error Cards */
    .error-card {
        background-color: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.2s;
    }
    .error-card:hover {
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-color: #D1D5DB;
    }
    
    .annotated-text {
        font-family: 'Merriweather', serif;
        line-height: 1.8;
        color: #374151;
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    
    del { color: #9CA3AF; text-decoration: line-through; margin-right: 4px; text-decoration-thickness: 2px; }
    ins.grammar { background-color: #4ADE80; color: #022C22; text-decoration: none; padding: 2px 6px; border-radius: 4px; font-weight: 700; border: 1px solid #22C55E; }
    ins.vocab { background-color: #FDE047; color: #000; text-decoration: none; padding: 2px 6px; border-radius: 4px; font-weight: 700; border: 1px solid #FCD34D; }
    
    /* Button Customization */
    div.stButton > button {
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #D93434;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIC AI (FAILOVER)
# ==========================================
try:
    ALL_KEYS = st.secrets["GEMINI_API_KEYS"]
except Exception:
    st.error("⚠️ Chưa cấu hình secrets.toml chứa GEMINI_API_KEYS!")
    st.stop()

def generate_content_with_failover(prompt, image=None, json_mode=False):
    keys_to_try = list(ALL_KEYS)
    random.shuffle(keys_to_try) 
    
    model_priority = [
        "gemini-2.0-flash-thinking-preview-01-21", "gemini-3-flash-preview", 
        "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"
    ]
    
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
            
            gen_config = {
                "temperature": 0.3, "top_p": 0.95, "top_k": 64, "max_output_tokens": 32000
            }
            
            # QUAN TRỌNG: Chỉ bật JSON mode khi cần thiết (Tutor). 
            # Khi chấm điểm (Grading), ta cần cả Text + JSON nên để json_mode=False
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
# 3. PROMPT KHỦNG (NGUYÊN BẢN TỪ APP CHẤM ĐIỂM)
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
*   **Mechanical Linkers (Lỗi máy móc):** Nếu câu nào cũng bắt đầu bằng "Firstly, Secondly, In addition, Furthermore" -> Tối đa Band 6.0.
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
*   Dựa trên kết quả quét 3 lớp, liệt kê **TẤT CẢ** vấn đề vào mảng `errors`.
*   **>> QUY TẮC "BẰNG CHỨNG BẮT BUỘC" (MANDATORY EVIDENCE):**
    *   Nếu bạn định chấm điểm **Coherence & Cohesion dưới 9.0**, bạn **BẮT BUỘC** phải tạo ra ít nhất **2-3 mục lỗi** trong mảng `errors` thuộc nhóm `Coherence & Cohesion` để giải thích lý do trừ điểm.
    *   *Ví dụ:* Nếu chấm CC 6.0, bạn phải chỉ ra cụ thể: "Đoạn 2 thiếu câu chủ đề", "Từ nối 'Moreover' dùng sai", hoặc "Mạch văn bị đứt gãy".
    *   **CẤM:** Tuyệt đối không được để trống danh sách lỗi CC nếu điểm CC < 9.0.
*   **Thực hiện quét 2 lớp:** 
        *   *Lớp 1 (Grammar/Vocab):* Soi từng mạo từ, dấu phẩy, số ít/nhiều.
        *   *Lớp 2 (Data Logic):* Kiểm tra lỗi "Object vs Figure" (vd: nhầm giữa chủ thể ngành công nghiệp và lượng khí thải). 
*   **Liệt kê toàn bộ lỗi vào mảng `errors` trước.** Nếu có 14 vị trí sai, phải có 14 mục lỗi trong JSON. *Ví dụ:* Nếu sai 3 mạo từ 'the', phải có 3 mục lỗi riêng biệt.
*   **>> QUY TẮC "DOUBLE-TAGGING" (GẮN NHÃN KÉP - MỚI THÊM):**
    *   Nếu gặp lỗi ngữ pháp nghiêm trọng làm đứt gãy mạch văn (như `Sentence Fragment`, `Run-on Sentence`, `Comma Splice`), bạn phải tạo **2 mục lỗi** trong JSON:
        1.  Một mục `Grammar` (để sửa câu chữ).
        2.  Một mục `Coherence & Cohesion` với tên lỗi `Fragmented Flow` (để cảnh báo về mạch lạc).
    *   Điều này đảm bảo phần Coherence & Cohesion không bị trống và không hiển thị thông báo "Tuyệt vời" sai lệch.
*   Dựa trên danh sách lỗi này để tính toán Band điểm cho bài gốc (Markdown).
*   **Quy tắc làm tròn điểm bài viết theo chuẩn IELTS:**
    *   Làm tròn đến nửa band gần nhất (.0 hoặc .5).
    *   **NGOẠI LỆ BẮT BUỘC:**
        *   Điểm trung bình có đuôi **.25** -> BẮT BUỘC làm tròn **XUỐNG** số nguyên (Ví dụ: 8.25 -> 8.0).
        *   Điểm trung bình có đuôi **.75** -> BẮT BUỘC làm tròn **XUỐNG** .5 (Ví dụ: 8.75 -> 8.5).

**Bước 2: Tạo bản sửa lỗi (Annotated Essay)**
    *   **Nguyên tắc "Soi gương":** Bạn chỉ được phép sửa lỗi dựa trên danh sách lỗi đã lập ở Bước 1. 
    *   **Cấm sửa ngầm (No Hidden Edits):** Tuyệt đối không được "tiện tay" sửa các lỗi nhỏ (như thêm mạo từ 'the' hay viết hoa) trong bài sửa nếu bạn chưa khai báo lỗi đó trong danh sách `errors` ở Bước 1. 
    *   **Số lượng thẻ `<del>` phải bằng chính xác số lượng lỗi trong JSON.** Nếu sai lệch, hệ thống sẽ coi là vi phạm giao thức.
    
**Bước 3: Chấm lại bản sửa lỗi (JSON Output - Internal Re-grading)**
*   Hãy đóng vai một Giám khảo độc lập thứ 2 chấm lại bản `annotated_essay` vừa tạo (coi đây là một bài nộp mới đã sạch lỗi câu chữ).
*   **Luật Nội dung (Content Rule):** Vì bản sửa này chỉ khắc phục GRA/LR và giữ nguyên cấu trúc cũ, nên điểm TA và CC của bản sửa **THƯỜNG GIỮ NGUYÊN** như bài gốc. Nếu bài gốc thiếu Overview hoặc sai số liệu, bài sửa vẫn bị điểm thấp ở TA/CC.
*   **Điểm số `revised_score`:** Phải phản ánh đúng trình độ của bài sau khi đã sạch lỗi GRA/LR.
    *   **Kiểm tra độ dài:** Nếu bản sửa > 200 từ -> TA tối đa **8.0** (Phạt lỗi thiếu súc tích).
    *   **Kiểm tra tính tự nhiên:** Nếu dùng từ vựng "đao to búa lớn" gượng ép -> LR tối đa **8.0**.
*   **Lưu ý về TA & CC:** Vì bản sửa này chỉ sửa lỗi Ngữ pháp/Từ vựng và giữ nguyên cấu trúc cũ, nên điểm TA và CC của bản sửa **PHẢI GIỮ NGUYÊN** như bài gốc (trừ khi việc sửa từ vựng giúp ý nghĩa rõ ràng hơn thì có thể tăng nhẹ .5 điểm). 
*   **Consistency & Parity Check:** 
    *   Đếm số lượng thẻ `<del>` trong bài sửa. Nếu không khớp với số lượng mục lỗi trong mảng `errors` (Ví dụ: sửa 14 chỗ nhưng chỉ khai báo 7 lỗi), bạn đã vi phạm giao thức. Bạn phải bổ sung mảng `errors` cho đến khi đạt tỷ lệ **1:1**.
*   **>> CHỐT CHẶN BAND 9.0 (THE 9.0 BARRIER):**
    *   **Về Coherence & Cohesion (CC):** Tuyệt đối KHÔNG cho bản sửa đạt 9.0 nếu cấu trúc vẫn sử dụng các từ nối cơ bản ở đầu câu như *"Regarding...", "In addition...", "Overall..."*. Band 9 CC yêu cầu sự liên kết "vô hình" (invisible cohesion). Nếu cấu trúc bài gốc là Band 7-8, điểm CC của bản sửa **BẮT BUỘC** phải giữ nguyên ở mức 7-8.
    *   **Về Task Achievement & Lexical (TA/LR):** Kiểm tra lỗi logic "Object vs Figure". Nếu thí sinh viết *"Industry was the most polluted"* thay vì *"Industrial emissions were the highest"*, đây là lỗi tư duy dữ liệu nghiêm trọng. Bản sửa dù có sửa lại câu chữ thì điểm TA và LR vẫn phải bị khống chế (Ceiling) ở mức **7.0 - 8.0** vì lỗi sai bản chất chủ thể.
    *   **Về Đơn vị (Unit Accuracy):** Soi kỹ đơn vị (tonnes, %, number). Nếu bài gốc nhầm lẫn đơn vị, bản sửa dù có thay đổi từ vựng cũng không được phép tăng điểm TA quá 1.0 điểm so với bài gốc.
*   **>> GIAO THỨC "RE-SCAN" (QUÉT LẠI LẦN CUỐI):** Trước khi chốt điểm `revised_score`, hãy tự đặt câu hỏi: *"Tôi có đang quá hào phóng không? Nếu một Giám khảo khó tính nhất đọc bản sửa này, họ có thấy nó vẫn còn mang 'khung xương' của một bài Band 7 hay không?"*. Nếu có, hãy hạ điểm xuống ngay lập tức.
Thông tin bài làm:
a/ Đề bài (Task 1 question): {{TOPIC}}
b/ Mô tả hình ảnh (Picture/Graph/Chart): {{IMAGE_NOTE}}
c/ Bài làm của thí sinh (Written report): {{ESSAY}}

---
### NỘI DUNG ĐÁNH GIÁ CHI TIẾT:
**LƯU Ý QUAN TRỌNG VỀ SƯ PHẠM (PEDAGOGY RULE):**
Khi đưa ra ví dụ sửa lỗi (Example/Rewrite), bạn phải căn cứ vào **Band điểm hiện tại** của bài làm:
*   **Nếu bài < 6.0:** Hãy đưa ra ví dụ sửa ở mức **Band 7.0** (Tập trung vào sự Chính xác, Rõ ràng, Dễ hiểu). Đừng dùng từ quá khó.
*   **Nếu bài >= 6.5:** Hãy đưa ra ví dụ sửa ở mức **Band 9.0** (Tập trung vào sự Tinh tế, Học thuật, Cấu trúc phức tạp).
**QUY TẮC "CHỐNG SƠ SÀI" (ANTI-BREVITY RULE):**
1.  **Cấm nhận xét chung chung:** Tuyệt đối không viết "Cần cải thiện ngữ pháp" mà không chỉ rõ là cải thiện cái gì (thì, mạo từ, hay cấu trúc?).
2.  **Trích dẫn bằng chứng:** Mọi nhận xét đều phải trích dẫn câu văn cụ thể của thí sinh để chứng minh.
3.  **Luôn viết mẫu:** Dù bài làm ở Band 1 hay Band 9, bạn **BẮT BUỘC** phải cung cấp các ví dụ viết lại (Rewrite) ở cuối mỗi tiêu chí. Không được bỏ qua.

### **1. Task Achievement (Hoàn thành yêu cầu bài thi):**

*   **Đánh giá Overview (Cái nhìn tổng quan):** 
    *   [Phân tích: Đã có Overview chưa? Có nêu được xu hướng chính và sự so sánh nổi bật không?]
    *   **⚠️ Cảnh báo cho trình độ Band 5-6:** [Nếu Overview vẫn bị dính số liệu chi tiết, hãy giải thích tại sao lỗi này khiến họ bị kẹt ở Band 5 và hướng dẫn cách xóa bỏ để lên Band 7.]
*   **Độ chính xác và Chọn lọc dữ liệu:** 
    *   [Kiểm tra độ chính xác của số liệu. Có bị lỗi "Data Saturation" - nhồi nhét quá nhiều số liệu vụn vặt không?]
    *   [**Lưu ý:** Bỏ qua dữ liệu 'Total'/'Other' nếu không quan trọng.]
*   **Giải quyết yêu cầu (Response Strategy):** [Đánh giá cách nhóm thông tin. Thí sinh đang mô tả đơn lẻ (Band 5) hay đã biết tổng hợp dữ liệu để so sánh (Band 7+)?]

*   **⚠️ Các lỗi nghiêm trọng & Phân tích chuyên sâu:** 
    *   [Với mỗi lỗi tìm được, bạn **BẮT BUỘC** giải thích theo 3 bước:
        1. **Trích dẫn lỗi:** (Ví dụ: "the figure of pizza ate")
        2. **Lý do yếu kém:** (Ví dụ: Vi phạm lỗi tư duy Object vs Figure).
        3. **Tác động:** (Ví dụ: Làm mất tính chuyên nghiệp, khiến giám khảo đánh giá thấp tư duy logic).]

*   **💡 CHIẾN THUẬT NÂNG BAND (STEP-BY-STEP):**
    *   **Bước 1 (Lọc):** Tuyệt đối xóa số liệu khỏi Overview. Overview chỉ nói về "ý nghĩa" con số.
    *   **Bước 2 (Gộp):** Nhóm các đối tượng cùng tăng/cùng giảm để tạo sự súc tích (Economy).
    *   **Bước 3 (So sánh):** Luôn phải chỉ ra điểm cao nhất/thấp nhất hoặc sự thay đổi thứ hạng đáng kể.
    *   **Bước 4 (Kết nối):** Sử dụng liên kết "tàng hình" (While/Whereas/V-ing) thay vì từ nối máy móc.
    
*   **✍️ HÌNH MẪU ĐỐI CHIẾU (CHỌN MỨC PHÙ HỢP ĐỂ HỌC):**
    *   **Mẫu thực tế (Mục tiêu Band 7.0):** 
        *   *"Đây là phiên bản rõ ràng, chính xác, không lỗi logic mà bạn có thể đạt được ngay sau khi chỉnh sửa bài làm hiện tại:"*
        *   **[AI HÃY VIẾT OVERVIEW & BODY ĐẠT CHUẨN 7.0 DỰA TRÊN Ý TƯỞNG CỦA HỌC VIÊN]**
    *   **Mẫu chuyên sâu (Tham khảo Band 9.0):** 
        *   *"Đây là phiên bản để bạn tham khảo cách dùng từ vựng tinh tế và cấu trúc tổng hợp dữ liệu đỉnh cao của Giám khảo:"*
        *   **[AI HÃY VIẾT OVERVIEW & BODY ĐẠT CHUẨN 9.0 TẠI ĐÂY]**

> **📍 Điểm Task Achievement:** [Điểm số/9.0]

#### **2. Coherence and Cohesion (Độ mạch lạc và liên kết):**

*   **Tổ chức đoạn văn (Paragraphing):** [Phân tích logic chia đoạn: Bạn chia đoạn theo Tiêu chí gì (Thời gian/Đối tượng/Xu hướng)? Cách chia này có giúp người đọc dễ so sánh không? Mỗi đoạn có một trọng tâm rõ ràng không?]
*   **Sử dụng từ nối (Linking Devices):** [Đánh giá độ tự nhiên:
    *   **Cảnh báo:** Có bị lạm dụng từ nối đầu câu ("Mechanical Linking") như *Regarding, Turning to, Looking at, Firstly* không?
    *   **Khuyến khích:** Có sử dụng "Invisible Cohesion" (trạng từ đứng giữa câu như *meanwhile, however* hoặc dùng mệnh đề quan hệ để nối ý) không?]
*   **Phép tham chiếu (Referencing):** [Kiểm tra kỹ thuật Referencing: Bạn có sử dụng *it, this, that, the former, the latter, respectively* để tránh lặp từ không? Hay bạn lặp lại danh từ liên tục?]
*   **⚠️ Lỗi cần khắc phục:** [Chỉ ra cụ thể (càng nhiều càng tốt):
    1.  **Mạch văn đứt gãy:** Các câu rời rạc, không ăn nhập.
    2.  **Tham chiếu sai:** Dùng "it" nhưng không rõ thay thế cho từ nào (Ambiguous Reference).
    3.  **Lỗi cấu trúc:** Lặp lại cấu trúc câu (VD: Câu nào cũng bắt đầu bằng "The figure...").
    4.  **Câu thiếu động từ (Fragment):** Gây khó hiểu.]
*   **💡 Cải thiện & Nâng cấp (Correction & Upgrade):**
    *   *Câu gốc (Vấn đề):* "[Trích dẫn chính xác câu văn bị máy móc/lủng củng của thí sinh]"
    *   *Gợi ý viết lại (Natural Flow):* "[Nếu Band thấp: Sửa cho ĐÚNG ngữ pháp và RÕ nghĩa nối. Nếu Band 7+: Viết lại câu đó sử dụng cấu trúc liên kết ẩn hoặc chủ ngữ liên kết để đạt Band 8-9]"
    *   *Giải thích:* "[Tại sao cách viết mới giúp bài văn mượt mà và chuyên nghiệp hơn?]"
* **Yêu cầu bắt buộc về độ sâu:** Với mỗi lỗi tìm được, bạn phải giải thích theo 3 bước:
    1. Trích dẫn lỗi.
    2. Giải thích tại sao quy tắc Band Descriptors coi đây là điểm yếu.
    3. Phân tích tác động của lỗi này đến người đọc (gây hiểu lầm, làm mất tính chuyên nghiệp...).
    
> **📍 Điểm Coherence & Cohesion:** [Điểm số/9.0]

#### **3. Lexical Resource (Vốn từ vựng):**

*   **Đánh giá độ đa dạng (Range & Flexibility):** [Nhận xét tổng quan: Vốn từ của thí sinh đang ở mức nào? (Cơ bản/Đủ dùng/Phong phú). Có bị lỗi lặp từ ("Repetition") nghiêm trọng với các từ khóa chính (increase, decrease, figure...) không?]
*   **Độ chính xác và Văn phong (Precision & Style):** [Đánh giá: Thí sinh có dùng được các cụm từ kết hợp (Collocations) tự nhiên không hay là dịch từ tiếng mẹ đẻ (Word-for-word translation)? Có từ nào bị dùng sai ngữ cảnh (ví dụ: dùng văn nói "get up" thay vì "increase") không?]
*   **⚠️ Điểm yếu cốt lõi:** [Đừng liệt kê từng lỗi chính tả. Hãy chỉ ra **thói quen sai** của thí sinh. Ví dụ: *"Bạn thường xuyên chọn sai từ để mô tả đối tượng (Object)"* hoặc *"Bạn lạm dụng từ vựng quá trang trọng (Pretentious) không cần thiết"*.]
*   **💡 Gợi ý nâng cấp (Vocabulary Upgrade):**
    *   *Thay thế từ vựng thường:* "[Tìm 1 từ lặp lại nhiều nhất trong bài, ví dụ 'increase']"
    *   *Gợi ý thay thế:* 
        *   *[Nếu Band < 7]:* Gợi ý các từ cơ bản nhưng đúng (rise, growth, go up).
        *   *[Nếu Band 7+]:* Gợi ý các từ học thuật (escalate, upsurge, register a growth).
* **Yêu cầu bắt buộc về độ sâu:** Với mỗi lỗi tìm được, bạn phải giải thích theo 3 bước:
    1. Trích dẫn lỗi.
    2. Giải thích tại sao quy tắc Band Descriptors coi đây là điểm yếu.
    3. Phân tích tác động của lỗi này đến người đọc (gây hiểu lầm, làm mất tính chuyên nghiệp...).
    
> **📍 Điểm Lexical Resource:** [Điểm số/9.0]

#### **4. Grammatical Range and Accuracy (Ngữ pháp):**

*   **Độ đa dạng cấu trúc (Range Check):** [Phân tích chiến lược: Bài viết có "nghèo nàn" cấu trúc không? (Chỉ dùng câu đơn/câu ghép cơ bản). Thí sinh có sử dụng được các cấu trúc Band 8+ không: *Passive Voice (Bị động)*, *Reduced Relative Clause (Rút gọn mệnh đề)*, *Nominalization (Danh từ hóa)*?]
*   **Độ chính xác (Accuracy Check):** [Ước lượng tỷ lệ câu không lỗi (Error-free sentences): Dưới 50% (Band 5), 50-70% (Band 6-7), hay trên 80% (Band 8+)? Lỗi sai chủ yếu là lỗi hệ thống (Systematic - sai quy tắc) hay lỗi sơ suất (Slips)?].Nếu bài viết có trên 80% số câu hoàn toàn sạch lỗi (Error-free) và lỗi duy nhất là một lỗi nhỏ (như "most highest") -> **Vẫn giữ mức Band 8.5 - 9.0**. Đừng ép thí sinh dùng cấu trúc lạ nếu cấu trúc hiện tại đã quá đủ để truyền đạt thông tin một cách tinh tế. Band 9 không bắt buộc phải có "Đảo ngữ" hay "Câu điều kiện". Range được thể hiện qua việc sử dụng linh hoạt: Mệnh đề quan hệ, câu phân từ (Reduced clauses), danh từ hóa (Nominalization), và các cấu trúc so sánh phức tạp. 
*   **Dấu câu (Punctuation):** [Nhận xét việc dùng dấu phẩy, dấu chấm. Có mắc lỗi *Comma Splice* (Dấu phẩy nối câu) kinh điển không?]
*   **⚠️ Lỗi hệ thống cần sửa:** [Chỉ ra lỗ hổng kiến thức ngữ pháp lớn nhất của thí sinh. Ví dụ: *"Bạn rất yếu về Mệnh đề quan hệ"* hoặc *"Bạn chưa nắm vững cách dùng Mạo từ"*.]
*   **💡 Thử thách viết lại (Sentence Transformation):**
    *   *Câu gốc (Simple/Error):* "[Trích 1 câu đơn giản hoặc có lỗi trong bài]"
    *   *Nâng cấp câu:* 
        *   *[Nếu Band thấp]:* Ghép thành câu ghép/câu phức cơ bản (dùng because, although) để đảm bảo đúng.
        *   *[Nếu Band cao]:* Dùng cấu trúc nâng cao (Mệnh đề phân từ, Đảo ngữ, Nominalization).
* **Yêu cầu bắt buộc về độ sâu:** Với mỗi lỗi tìm được, bạn phải giải thích theo 3 bước:
    1. Trích dẫn lỗi.
    2. Giải thích tại sao quy tắc Band Descriptors coi đây là điểm yếu.
    3. Phân tích tác động của lỗi này đến người đọc (gây hiểu lầm, làm mất tính chuyên nghiệp...).
    
> **📍 Điểm Grammatical Range & Accuracy:** [Điểm số/9.0]

---
### **TỔNG ĐIỂM (OVERALL BAND SCORE):** Quy tắc làm tròn điểm bài viết theo chuẩn IELTS:
    *   Làm tròn đến nửa band gần nhất (.0 hoặc .5).
    *   **NGOẠI LỆ BẮT BUỘC:**
        *   Điểm trung bình có đuôi **.25** -> BẮT BUỘC làm tròn **XUỐNG** số nguyên (Ví dụ: 8.25 -> 8.0).
        *   Điểm trung bình có đuôi **.75** -> BẮT BUỘC làm tròn **XUỐNG** .5 (Ví dụ: 8.75 -> 8.5).

---
### **LỜI KHUYÊN CHIẾN THUẬT TỪ GIÁM KHẢO (EXAMINER'S TIPS):**
1.  **Đưa ra các lời khuyên:** Hãy đưa ra các lời khuyên chiến thuật dựa trên những lỗi sai thực tế trong bài.
2.  **Economy:** Cách cắt giảm số từ thừa (nếu bài > 200 từ).
3.  **Introduction Power:** Cách đổi Noun Phrase -> Noun Clause trong mở bài.
4.  **Grouping:** Cách nhóm thông tin thông minh hơn (nhóm theo xu hướng Lớn vs Nhỏ).
5.  **Overview:** Cách viết Overview tốt hơn.

#### **5. DỮ LIỆU PHÂN TÍCH (ANALYSIS DATA):**

Sau khi đánh giá xong, bạn **BẮT BUỘC** phải trích xuất dữ liệu dưới dạng một **JSON Object duy nhất**.

**QUAN TRỌNG:** Trong trường "type" (Tên lỗi), bạn CHỈ ĐƯỢC PHÉP được dùng các thuật ngữ tiếng Anh chuẩn học thuật dưới đây:

**A. [COHERENCE & COHESION] - Macro Errors:**
# Organization & Progression (Tổ chức & Phát triển)
`Illogical Grouping` (Sắp xếp phi logic), `Missing Overview` (Thiếu tổng quan), `Fragmented Flow` (Mạch văn đứt gãy), `Lack of Progression` (Không phát triển ý), `Incoherent Paragraphing` (Chia đoạn không mạch lạc).
# Linking & Reference (Liên kết & Tham chiếu)
`Mechanical Linking` (Từ nối máy móc), `Overuse of Connectors` (Lạm dụng từ nối), `Ambiguous Referencing` (Tham chiếu mơ hồ), `Repetitive Structure` (Lặp cấu trúc), `Data Inaccuracy` (Sai số liệu/Logic).

**B. [GRAMMAR] - Micro Errors:**
# Sentence Structure (Cấu trúc câu)
`Comma Splice` (Lỗi dấu phẩy), `Run-on Sentence` (Câu dính liền), `Sentence Fragment` (Câu thiếu thành phần), `Faulty Parallelism` (Lỗi song song), `Misplaced Modifier` (Bổ ngữ sai chỗ), `Word Order` (Trật tự từ).
# Morphology & Syntax (Hình thái & Cú pháp)
`Subject-Verb Agreement` (Hòa hợp chủ vị), `Tense Inconsistency` (Sai thì), `Passive Voice Error` (Lỗi bị động), `Relative Clause Error` (Lỗi mệnh đề quan hệ).
# Mechanics (Cơ học)
`Article Error` (Mạo từ), `Preposition Error` (Giới từ), `Singular/Plural` (Số ít/nhiều), `Countable/Uncountable` (Danh từ đếm được/không), `Punctuation` (Dấu câu).

**C. [VOCABULARY] - Lexical Errors:**
# Meaning & Use (Nghĩa & Cách dùng)
`Imprecise Word Choice` (Dùng từ thiếu chính xác), `Incompatible Collocation` (Kết hợp từ sai), `Word Form Error` (Sai loại từ), `Selectional Restriction Violation` (Vi phạm quy tắc chọn lọc từ).
# Style & Register (Văn phong)
`Informal Register` (Văn phong suồng sã), `Pretentious Language` (Dùng từ sáo rỗng/làm màu), `Redundancy` (Thừa từ/Lặp ý), `Forced Paraphrasing` (Paraphrase gượng ép).

**CATEGORY MAPPING RULE:**
*   Group A -> `category`: "Coherence & Cohesion"
*   Group B -> `category`: "Grammar"
*   Group C -> `category`: "Vocabulary"

**TỰ CHẤM LẠI BẢN SỬA (INTERNAL RE-GRADING - BƯỚC QUAN TRỌNG NHẤT):**
   - Hãy quên rằng bạn vừa sửa bài này. Hãy đóng vai một Giám khảo độc lập thứ 2 chấm lại bản 'annotated_essay' vừa tạo.
   - **Luật Nội dung (Content Rule):** Bản sửa chỉ sửa ngữ pháp/từ vựng, KHÔNG THỂ sửa lỗi thiếu số liệu/thiếu so sánh của bài gốc. Nếu bài gốc TA 6.0, bản sửa TA vẫn là 6.0 (hoặc tối đa 7.0 nếu diễn đạt rõ hơn).
   - **Kết luận:** Điểm 'revised_score' PHẢI là điểm thực tế của bản sửa, KHÔNG ĐƯỢC mặc định là 9.0.
Cấu trúc JSON:
```json
{
  "original_score": {
      "task_achievement": "Điểm TA của bài làm gốc (User's essay)",
      "cohesion_coherence": "Điểm CC của bài làm gốc",
      "lexical_resource": "Điểm LR của bài làm gốc",
      "grammatical_range": "Điểm GRA của bài làm gốc",
      "overall": "Điểm Overall của bài làm gốc (Average)"
  },
  "errors": [
    {
      "category": "Grammar" hoặc "Vocabulary",
      "type": "Tên Lỗi",
      "impact_level": "High" | "Medium" | "Low",
      "explanation": "Giải thích ngắn gọn lỗi.",
      "original": "đoạn văn bản sai",
      "correction": "đoạn văn bản đúng (VIẾT IN HOA)"
    }
  ],
  "annotated_essay": "Phiên bản bài làm đã được sửa lỗi (giữ nguyên cấu trúc các đoạn văn). Bọc từ sai trong thẻ <del>...</del> và từ sửa đúng trong thẻ <ins class='grammar'>...</ins> hoặc <ins class='vocab'>...</ins>. Nội dung sửa đúng phải viết IN HOA.",
   "revised_score": {
      "word_count_check": "BẮT BUỘC GHI SỐ TỪ CỦA BẢN SỬA (Ví dụ: '220 words - Too long')",
      "logic_re_evaluation": "Giải thích tại sao bị trừ điểm (Ví dụ: 'Dù sạch lỗi ngữ pháp nhưng bài viết dài 220 từ, vi phạm nguyên tắc súc tích, nên TA chỉ đạt 8.0').",
      "task_achievement": "Điểm TA thực tế (phạt nặng nếu dài dòng)",
      "cohesion_coherence": "Điểm CC",
      "lexical_resource": "Điểm LR",
      "grammatical_range": "Điểm GRA",
      "overall": "Điểm trung bình (Làm tròn theo Quy tắc làm tròn điểm bài viết theo chuẩn IELTS)"
          *   Làm tròn đến nửa band gần nhất (.0 hoặc .5).
          *   **NGOẠI LỆ BẮT BUỘC:**
              *   Điểm trung bình có đuôi **.25** -> BẮT BUỘC làm tròn **XUỐNG** số nguyên (Ví dụ: 8.25 -> 8.0).
              *   Điểm trung bình có đuôi **.75** -> BẮT BUỘC làm tròn **XUỐNG** .5 (Ví dụ: 8.75 -> 8.5).
  }
}
```
"""

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def clean_json(text):
    # Tìm đoạn văn bản nằm giữa dấu ngoặc nhọn { ... } đầu tiên và cuối cùng
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        content = match.group(1).strip()
        # Loại bỏ các ký tự điều khiển lỗi
        content = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)
        return content
    return None

def parse_guide_response(text):
    j_str = clean_json(text)
    if not j_str: return None
    try:
        return json.loads(j_str)
    except:
        # Nếu lỗi JSON, thử quét tay các trường quan trọng (fallback)
        return {
            "task_type": "IELTS Task 1",
            "intro_guide": "Hãy paraphrase đề bài bằng từ đồng nghĩa.",
            "overview_guide": "Nêu xu hướng chung và đặc điểm nổi bật.",
            "body1_guide": "Mô tả chi tiết nhóm số liệu 1.",
            "body2_guide": "Mô tả chi tiết nhóm số liệu 2."
        }

def process_grading_response(full_text):
    """
    Hàm xử lý kết quả chấm điểm (CHUẨN TỪ APP CHẤM ĐIỂM).
    Tách biệt:
    1. Markdown Text (Phân tích chi tiết ở đầu).
    2. JSON Data (Điểm số và lỗi ở cuối).
    """
    json_str = clean_json(full_text)
    
    # Mặc định
    markdown_part = full_text
    data = {
        "errors": [], 
        "annotatedEssay": None, 
        "revisedScore": None, 
        "originalScore": {
            "task_achievement": "-", "cohesion_coherence": "-", 
            "lexical_resource": "-", "grammatical_range": "-", "overall": "-"
        }
    }
    
    if json_str:
        # Tách phần Markdown (trước JSON)
        markdown_part = full_text.split("```json")[0].strip()
        # Nếu AI không dùng code block, thử split bằng ký tự '{' đầu tiên của JSON
        if "original_score" in markdown_part: # Dấu hiệu JSON bị lẫn
             parts = full_text.split("{", 1)
             markdown_part = parts[0].strip()

        try:
            parsed = json.loads(json_str)
            data["errors"] = parsed.get("errors", [])
            data["annotatedEssay"] = parsed.get("annotated_essay")
            data["revisedScore"] = parsed.get("revised_score")
            data["originalScore"] = parsed.get("original_score", {})
        except json.JSONDecodeError:
            pass

    return markdown_part, data

# --- FILE EXPORT ---
def register_vietnamese_font():
    try:
        font_reg = "Roboto-Regular.ttf"
        font_bold = "Roboto-Bold.ttf"
        if not os.path.exists(font_reg):
            r = requests.get("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf")
            with open(font_reg, "wb") as f: f.write(r.content)
        if not os.path.exists(font_bold):
            r = requests.get("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf")
            with open(font_bold, "wb") as f: f.write(r.content)
        pdfmetrics.registerFont(TTFont('Roboto', font_reg))
        pdfmetrics.registerFont(TTFont('Roboto-Bold', font_bold))
        addMapping('Roboto', 0, 0, 'Roboto')
        addMapping('Roboto', 1, 0, 'Roboto-Bold')
        return True
    except: return False

def create_docx(data, topic, essay, analysis):
    doc = Document()
    doc.add_heading('IELTS ASSESSMENT REPORT', 0).alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_heading('1. DETAILED ANALYSIS', level=1)
    doc.add_paragraph(analysis) # Phân tích chi tiết từ Markdown
    
    # Thêm bảng điểm
    doc.add_heading('2. SCORE BREAKDOWN', level=1)
    scores = data.get("originalScore", {})
    p = doc.add_paragraph()
    p.add_run(f"Overall Band: {scores.get('overall', '-')}\n").bold = True
    p.add_run(f"TA: {scores.get('task_achievement', '-')}, CC: {scores.get('cohesion_coherence', '-')}, LR: {scores.get('lexical_resource', '-')}, GRA: {scores.get('grammatical_range', '-')}")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

def create_pdf(data, topic, essay, analysis):
    register_vietnamese_font()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph("IELTS ASSESSMENT REPORT", styles['Title'])]
    
    # Analysis
    elements.append(Paragraph("DETAILED ANALYSIS", styles['Heading1']))
    # Clean markdown basic symbols for PDF
    safe_text = html.escape(analysis).replace('\n', '<br/>').replace('**', '').replace('#', '')
    elements.append(Paragraph(safe_text, styles['Normal']))
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# 4. UI: QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ==========================================
if "step" not in st.session_state: st.session_state.step = 1 
if "guide_data" not in st.session_state: st.session_state.guide_data = None
if "grading_result" not in st.session_state: st.session_state.grading_result = None
if "saved_topic" not in st.session_state: st.session_state.saved_topic = ""
if "saved_img" not in st.session_state: st.session_state.saved_img = None

# ==========================================
# 5. GIAO DIỆN CHÍNH (THEO YÊU CẦU MỚI)
# ==========================================

# TIÊU ĐỀ CHÍNH
st.markdown('<div class="main-header">🎓 IELTS Writing Task 1 – Examiner-Guided</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Learning & Scoring Based on IELTS Band Descriptors</div>', unsafe_allow_html=True)

if st.session_state.step == 1:
    
    # STEP 1 – Task 1 Question (Đã đổi lên trên)
    st.markdown('<div class="step-header">STEP 1 – Task 1 Question</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-desc">Paste the official task question here</div>', unsafe_allow_html=True)
    question_input = st.text_area("Question", height=150, placeholder="The chart below shows...", key="q_input", label_visibility="collapsed")

    # STEP 2 – Visual Data (Đã đổi xuống dưới)
    st.markdown('<div class="step-header">STEP 2 – Visual Data </div>', unsafe_allow_html=True)
    st.markdown('<div class="step-desc">Upload chart / graph / table / diagram / map </div>', unsafe_allow_html=True)
    uploaded_image = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key="img_input", label_visibility="collapsed")
    
    img_data = None
    if uploaded_image:
        img_data = Image.open(uploaded_image)
        st.image(img_data, caption='Uploaded Visual Data', width=400)

    # STEP 3 – Examiner Focus (Giữ nguyên vị trí)
    st.markdown('<div class="step-header">STEP 3 – Examiner Focus</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color: #F1F5F9; padding: 15px; border-radius: 8px; border: 1px solid #E2E8F0;">
        <div style="font-weight: 500; color: #334155;">✓ Task type identification</div>
        <div style="font-weight: 500; color: #334155;">✓ Key trends & overview logic</div>
        <div style="font-weight: 500; color: #334155;">✓ Data selection & comparison</div>
        <div style="font-weight: 500; color: #334155;">✓ Band scoring (TA – CC – LR – GRA)</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Nút bấm xử lý (vẫn sử dụng question_input và img_data đã khai báo ở trên)
    if st.button("🚀  Analyze & Guide (Start Learning)", type="primary", use_container_width=True):
        if not question_input or not img_data:
            st.warning("⚠️ Vui lòng nhập đầy đủ Đề bài và tải Ảnh lên để bắt đầu.")
        else:
            st.session_state.saved_topic = question_input
            st.session_state.saved_img = img_data
                   
            with st.spinner("Examiner đang phân tích loại biểu đồ và lên chiến thuật..."):
                    # Prompt Tutor Vạn Năng: Tự động thích ứng theo từng dạng bài
                    prompt_guide = """
                    Bạn là một Siêu Giáo viên IELTS Writing (Band 9.0). Nhiệm vụ của bạn là phân tích hình ảnh đầu vào và viết hướng dẫn thực hành chi tiết.
                    
                    **BƯỚC 1: NHẬN DIỆN LOẠI BÀI (QUAN TRỌNG)**
                    Hãy nhìn hình ảnh và xác định nó thuộc loại nào:
                    1. **Change Over Time** (Line, Bar, Table có năm tháng): Cần từ vựng xu hướng (increase, decrease).
                    2. **Static Chart** (Pie, Table 1 năm): Cần từ vựng so sánh (higher, lower, accounts for).
                    3. **Map (Bản đồ):** Cần từ vựng phương hướng (North, South) và sự thay đổi (demolished, constructed). Tuyệt đối không dùng "increase/decrease" cho nhà cửa.
                    4. **Process (Quy trình):** Cần câu Bị động (Passive voice) và từ nối trình tự (First, Then, Finally).
                    5. **Mixed (Kết hợp):** Cần hướng dẫn cách liên kết 2 biểu đồ.

                    **BƯỚC 2: VIẾT HƯỚNG DẪN (OUTPUT JSON)**
                    Dựa vào loại bài đã nhận diện, hãy viết nội dung hướng dẫn bằng Tiếng Việt (dùng thẻ HTML <ul>, <li>, <b> để trình bày đẹp):

                    1. **"intro_guide"**: 
                       - Hướng dẫn paraphrase đề bài cụ thể.
                       - Nếu là Map: Gợi ý dùng "illustrates the transformation/development...".
                       - Nếu là Process: Gợi ý dùng "demonstrates the procedure/stages...".
                       - Nếu là Data: Gợi ý dùng "compares the data/figures...".

                    2. **"overview_guide"**:
                       - **Map:** Nhấn mạnh sự thay đổi tổng quan (Vd: "trở nên hiện đại hơn", "nhiều tiện ích hơn").
                       - **Process:** Đếm tổng số bước, điểm đầu và điểm cuối.
                       - **Data:** Tìm xu hướng chung (Trend) hoặc Số liệu cao nhất/thấp nhất.
                       - Cung cấp mẫu câu mở đầu Overview "Overall, it is clear that...".

                    3. **"body1_guide" & "body2_guide"**:
                       - **Map:** Chia theo khu vực (Bắc/Nam) hoặc Giai đoạn (Trước/Sau). Hướng dẫn dùng thì Quá khứ đơn/Hiện tại hoàn thành.
                       - **Process:** Chia giai đoạn (ví dụ: Chuẩn bị vs Sản xuất). Nhắc học sinh dùng Passive Voice.
                       - **Data:** Hướng dẫn Grouping (Nhóm các đường tăng vào Body 1, giảm vào Body 2). Gợi ý cấu trúc so sánh phức tạp.
                       - Cung cấp từ vựng "ăn điểm" cụ thể cho bài này (Key Vocab).

                    **FORMAT JSON OUTPUT:**
                    {
                        "task_type": "Tên loại bài (VD: Map / Process Diagram / Mixed Charts)",
                        "intro_guide": "HTML string...",
                        "overview_guide": "HTML string...",
                        "body1_guide": "HTML string (Gợi ý Grouping + Grammar + Vocab)",
                        "body2_guide": "HTML string (Gợi ý Grouping + Grammar + Vocab)"
                    }
                    """
                    
                    # Gọi AI với Prompt Vạn Năng
                    res, _ = generate_content_with_failover(prompt_guide + "\nĐề bài: " + question_input, img_data, json_mode=True)
                    if res:
                        data = parse_guide_response(res.text)
                    # Dù AI trả về gì, ta cũng phải gán guide_data để App không bị kẹt ở Step 1
                        st.session_state.guide_data = data if data else {
                            "task_type": "Task 1", "intro_guide": "AI Error - Please try again", 
                            "overview_guide": "", "body1_guide": "", "body2_guide": ""
                    }
                    st.session_state.step = 2
                    st.rerun() # Buộc Streamlit vẽ lại giao diện Phase 2 ngay lập tức

# ==========================================
# 6. UI: PHASE 2 - WRITING PRACTICE (ULTIMATE STICKY)
# ==========================================
if st.session_state.step == 2 and st.session_state.guide_data:
    
    # --- 1. CSS "ĐÓNG ĐĂNG" CỘT TRÁI ---
    st.markdown("""
        <style>
            /* Nhắm vào container chứa cả 2 cột */
            [data-testid="stHorizontalBlock"] {
                align-items: flex-start !important;
            }

            /* Nhắm vào cột đầu tiên (Cột Trái) */
            [data-testid="stHorizontalBlock"] > div:nth-child(1) {
                position: -webkit-sticky !important;
                position: sticky !important;
                top: 2rem !important;
                z-index: 999 !important;
            }

            /* Cố định chiều cao vùng hiển thị đề bài để không bị trôi */
            [data-testid="stHorizontalBlock"] > div:nth-child(1) > div:nth-child(1) {
                max-height: 95vh !important;
                overflow-y: auto !important;
                padding-right: 10px !important;
            }

            /* Tùy chỉnh thanh cuộn cho cột trái (nếu có) */
            [data-testid="stHorizontalBlock"] > div:nth-child(1) > div:nth-child(1)::-webkit-scrollbar {
                width: 4px;
            }
            [data-testid="stHorizontalBlock"] > div:nth-child(1) > div:nth-child(1)::-webkit-scrollbar-thumb {
                background: #cccccc;
                border-radius: 10px;
            }
            
            /* Tăng khoảng cách giữa các ô nhập liệu bên phải cho dễ nhìn */
            .stTextArea {
                margin-bottom: 1rem !important;
            }
        </style>
    """, unsafe_allow_html=True)

    data = st.session_state.guide_data

    # --- 2. HÀM RENDER (Giữ nguyên để tránh lỗi NameError) ---
    def render_writing_section(title, guide_key, input_key):
        st.markdown(f"#### {title}")
        with st.expander(f"💡 Hướng dẫn viết {title}", expanded=False):
            g_text = data.get(guide_key, "Không có hướng dẫn.")
            st.markdown(f"<div class='guide-box'>{g_text}</div>", unsafe_allow_html=True)
        return st.text_area(label=title, height=200, key=input_key, placeholder=f"Bắt đầu viết {title} tại đây...", label_visibility="collapsed")

    # --- 3. CHIA CỘT LAYOUT (4-6) ---
    col_left, col_right = st.columns([4, 6], gap="large")

    with col_left:
        st.subheader("📄 Đề bài & Hình ảnh")
        # Khung chứa đề bài
        st.markdown(f"""
            <div style="background-color: #F1F5F9; padding: 20px; border-radius: 10px; border: 1px solid #CBD5E1; line-height: 1.6; color: #1E293B; margin-bottom: 15px;">
                <b>Question:</b><br><i>{st.session_state.saved_topic}</i>
            </div>
        """, unsafe_allow_html=True)
        
        # Hình ảnh biểu đồ
        if st.session_state.saved_img:
            st.image(st.session_state.saved_img, use_container_width=True)
        
        st.info(f"📌 **Dạng bài:** {data.get('task_type')}")

    with col_right:
        st.subheader("✍️ Khu vực viết bài")
        
        # Bộ đếm từ
        def count_w(k): return len(st.session_state.get(k, "").split())
        current_wc = count_w("in_intro") + count_w("in_overview") + count_w("in_body1") + count_w("in_body2")
        
        st.markdown(f"""
            <div style="text-align: right; margin-top: -45px;">
                <span style="background-color: #10B981; color: white; padding: 5px 15px; border-radius: 15px; font-weight: bold; font-size: 14px;">
                    Word count: {current_wc}
                </span>
            </div>
        """, unsafe_allow_html=True)

        # Render các ô nhập liệu
        intro_text = render_writing_section("Introduction", "intro_guide", "in_intro")
        overview_text = render_writing_section("Overview", "overview_guide", "in_overview")
        body1_text = render_writing_section("Body 1", "body1_guide", "in_body1")
        body2_text = render_writing_section("Body 2", "body2_guide", "in_body2")

        st.markdown("---")
        
        # Nút chấm điểm (Sử dụng Prompt gốc của bạn)
        if st.button("🎓 Gửi bài chấm điểm (Examiner Pro)", type="primary", use_container_width=True):
            if current_wc < 30:
                st.warning("⚠️ Bài viết quá ngắn, AI không thể chấm điểm chính xác.")
            else:
                with st.status("👨‍🏫 Giám khảo đang chấm bài...") as status:
                    total_essay = f"{intro_text}\n\n{overview_text}\n\n{body1_text}\n\n{body2_text}".strip()
                    # Sử dụng biến saved_topic để tránh lỗi NameError
                    prompt_grade = GRADING_PROMPT_TEMPLATE.replace('{{TOPIC}}', st.session_state.saved_topic).replace('{{ESSAY}}', total_essay)
                    
                    res_grade, _ = generate_content_with_failover(prompt_grade, st.session_state.saved_img, json_mode=False)
                    
                    if res_grade:
                        # process_grading_response là hàm bóc tách Text và JSON bạn đã có
                        mk_text, p_data = process_grading_response(res_grade.text)
                        st.session_state.grading_result = {
                            "data": p_data, "markdown": mk_text,
                            "essay": total_essay, "topic": st.session_state.saved_topic
                        }
                        st.session_state.step = 3
                        status.update(label="✅ Đã chấm xong!", state="complete", expanded=False)
                        st.rerun()
                    else:
                        status.update(label="❌ Lỗi kết nối AI", state="error")

# ==========================================
# 7. UI: PHASE 3 - GRADING RESULT (FINAL POLISHED)
# ==========================================
if st.session_state.step == 3 and st.session_state.grading_result:
    
    # --- 1. CSS TINH CHỈNH CUỐI CÙNG ---
    st.markdown("""
        <style>
            /* 1. Layout 2 cột */
            [data-testid="stHorizontalBlock"] {
                align-items: flex-start !important;
            }

            /* 2. Style cho 2 cái Hộp lớn (Container) */
            /* Streamlit tự tạo container có viền, ta chỉ cần chỉnh background app cho nổi bật */
            .stApp {
                background-color: #ffffff;
            }

            /* 3. Style Bài viết: Tự động xuống dòng, không cuộn ngang */
            .essay-review-box {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 15px; /* Tăng padding cho dễ đọc */
                
                font-family: 'Inter', sans-serif;
                font-size: 0.95rem;
                line-height: 1.6;
                color: #334155;
                
                /* QUAN TRỌNG: Ép xuống dòng */
                white-space: pre-wrap !important;       /* Giữ dòng mới nhưng wrap text */
                word-wrap: break-word !important;       /* Ngắt từ dài */
                overflow-wrap: break-word !important;   /* Hỗ trợ trình duyệt hiện đại */
                max-width: 100%;                        /* Không vượt quá chiều rộng hộp cha */
            }

            /* 4. Thanh cuộn đẹp */
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        </style>
    """, unsafe_allow_html=True)

    res = st.session_state.grading_result
    g_data = res["data"]
    analysis_text = res["markdown"]
    
    # --- 2. CHIA CỘT (Không cần tiêu đề to nữa) ---
    c1, c2 = st.columns([4, 6], gap="medium")

    # === HỘP TRÁI: THÔNG TIN ĐỐI CHIẾU ===
    with c1:
        # Hộp chứa có chiều cao cố định để tạo thanh cuộn
        with st.container(height=750, border=True):
            st.markdown("#### 📄 Thông tin đối chiếu")
            
            # Ảnh
            if st.session_state.saved_img:
                st.image(st.session_state.saved_img, use_container_width=True)
            
            st.markdown("---")
            
            # Đề bài
            with st.expander("📌 Đề bài (Prompt)", expanded=False):
                st.info(st.session_state.saved_topic)
                
            # Bài viết (Đã áp dụng class mới để không tràn)
            st.markdown("**✍️ Bài viết của bạn:**")
            st.markdown(f'<div class="essay-review-box">{html.escape(res["essay"])}</div>', unsafe_allow_html=True)

    # === HỘP PHẢI: KẾT QUẢ CHẤM ===
    with c2:
        with st.container(height=750, border=True):
            st.markdown("#### 👨‍🏫 Examiner Analysis")
            
            # Bảng điểm
            scores = g_data.get("originalScore", {})
            st.markdown(f"""
            <div style="background-color: #ecfdf5; border: 1px solid #6ee7b7; border-radius: 10px; padding: 15px; display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px;">
                <div style="text-align: center;">
                    <span style="color: #047857; font-weight: bold; font-size: 0.9rem;">BAND SCORE</span><br>
                    <span style="color: #059669; font-weight: 900; font-size: 2.5rem; line-height: 1;">{scores.get("overall", "-")}</span>
                </div>
                <div style="display: flex; gap: 15px; text-align: center;">
                    <div><small style="color:#047857;">TA</small><br><b style="color:#059669; font-size:1.1rem;">{scores.get("task_achievement", "-")}</b></div>
                    <div><small style="color:#047857;">CC</small><br><b style="color:#059669; font-size:1.1rem;">{scores.get("cohesion_coherence", "-")}</b></div>
                    <div><small style="color:#047857;">LR</small><br><b style="color:#059669; font-size:1.1rem;">{scores.get("lexical_resource", "-")}</b></div>
                    <div><small style="color:#047857;">GRA</small><br><b style="color:#059669; font-size:1.1rem;">{scores.get("grammatical_range", "-")}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Tabs chi tiết
            tab1, tab2, tab3, tab4 = st.tabs(["📝 Phân tích chuyên sâu", "🔴 Lỗi Ngữ pháp và Từ vựng", "🔵 Lỗi Mạch lạc", "✍️ Bài sửa"])
            
            with tab1:
                st.markdown(analysis_text if analysis_text and len(analysis_text) > 50 else "Chưa có dữ liệu phân tích.")

            with tab2:
                micro = [e for e in g_data.get('errors', []) if e.get('category') in ['Grammar', 'Vocabulary', 'Ngữ pháp', 'Từ vựng']]
                if not micro: st.success("✅ Tuyệt vời! Không có lỗi ngữ pháp lớn.")
                for i, err in enumerate(micro):
                    badge = "#DCFCE7" if err.get('category') in ['Grammar','Ngữ pháp'] else "#FEF9C3"
                    st.markdown(f"""
                    <div class="error-card">
                        <b>#{i+1} {err.get('type')}</b>
                        <div style="background:{badge}; padding:5px; border-radius:4px; margin:5px 0;">
                            <s>{err.get('original')}</s> ➔ <b>{err.get('correction')}</b>
                        </div>
                        <small><i>{err.get('explanation')}</i></small>
                    </div>
                    """, unsafe_allow_html=True)

            with tab3:
                macro = [e for e in g_data.get('errors', []) if e.get('category') not in ['Grammar', 'Vocabulary', 'Ngữ pháp', 'Từ vựng']]
                if not macro: st.success("✅ Cấu trúc tốt.")
                for err in macro:
                    st.markdown(f"""
                    <div class="error-card" style="border-left:4px solid #3b82f6;">
                        <b>{err.get('type')}</b>
                        <p>{err.get('explanation')}</p>
                        <p>👉 <b>{err.get('correction')}</b></p>
                    </div>
                    """, unsafe_allow_html=True)

            with tab4:
                st.markdown(f'<div class="annotated-text">{g_data.get("annotatedEssay", "")}</div>', unsafe_allow_html=True)

            st.markdown("---")
            
            # Download & Reset
            d1, d2 = st.columns(2)
            docx = create_docx(g_data, res['topic'], res['essay'], analysis_text)
            d1.download_button("📥 Tải báo cáo (.docx)", docx, "IELTS_Report.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            
            if st.button("🔄 Làm bài mới (Reset)", use_container_width=True):
                for k in ["step", "guide_data", "grading_result", "saved_topic", "saved_img"]: st.session_state[k] = None
                st.session_state.step = 1
                st.rerun()
