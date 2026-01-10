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
    h1, h2, h3 { font-family: 'Merriweather', serif !important; color: #0F172A !important; }
    
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
    .error-card:hover { box-shadow: 0 4px 6px rgba(0,0,0,0.05); border-color: #D1D5DB; }
    
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
    
    div.stButton > button { font-weight: bold; border-radius: 8px; }
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
            if json_mode and "thinking" not in sel_model.lower():
                gen_config["response_mime_type"] = "application/json"
            if "thinking" in sel_model.lower():
                 gen_config["thinking_config"] = {"include_thoughts": True, "thinking_budget": 1024}

            response = temp_model.generate_content(content_parts, generation_config=gen_config)
            return response, sel_model 
            
        except Exception:
            continue
    return None, None

# --- PROMPT "KHỦNG" CỦA BẠN (ĐÃ KHÔI PHỤC ĐẦY ĐỦ) ---
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
**Bước 2: Tạo bản sửa lỗi (Annotated Essay)**
**Bước 3: Chấm lại bản sửa lỗi (JSON Output - Internal Re-grading)**

YÊU CẦU OUTPUT LÀ MỘT JSON OBJECT DUY NHẤT chứa dữ liệu dưới đây. 
Tuyệt đối KHÔNG trả về markdown bên ngoài JSON. Mọi phân tích chữ viết phải nằm trong các trường "analysis" của JSON.

```json
{
  "original_score": {
      "task_achievement": "Điểm TA",
      "cohesion_coherence": "Điểm CC",
      "lexical_resource": "Điểm LR",
      "grammatical_range": "Điểm GRA",
      "overall": "Điểm Overall"
  },
  "detailed_analysis": {
      "task_achievement": "VIẾT PHÂN TÍCH CHI TIẾT TA VÀO ĐÂY (Markdown allowed, >200 từ)",
      "cohesion_coherence": "VIẾT PHÂN TÍCH CHI TIẾT CC VÀO ĐÂY (Markdown allowed, >200 từ)",
      "lexical_resource": "VIẾT PHÂN TÍCH CHI TIẾT LR VÀO ĐÂY (Markdown allowed, >200 từ)",
      "grammatical_range": "VIẾT PHÂN TÍCH CHI TIẾT GRA VÀO ĐÂY (Markdown allowed, >200 từ)"
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
  "annotated_essay": "Phiên bản bài làm đã được sửa lỗi...",
   "revised_score": {
      "task_achievement": "Điểm TA sau sửa",
      "cohesion_coherence": "Điểm CC sau sửa",
      "lexical_resource": "Điểm LR sau sửa",
      "grammatical_range": "Điểm GRA sau sửa",
      "overall": "Điểm Overall sau sửa",
      "logic_re_evaluation": "Giải thích..."
  }
}
```
"""

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

def clean_json(text):
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match: return match.group(1).strip()
    if text.strip().startswith("{"): return text.strip()
    return None

def parse_guide_response(text):
    try:
        j_str = clean_json(text)
        return json.loads(j_str) if j_str else None
    except: return None

def parse_grading_response(full_text):
    """
    Hàm Deep Search: Quét toàn bộ cấu trúc JSON để tìm nội dung phân tích
    bất kể AI giấu nó ở đâu (root, detailed_analysis, gap_analysis...)
    """
    json_str = clean_json(full_text)
    data = {"errors": [], "annotatedEssay": None, "revisedScore": None, "originalScore": {}, "analysisMarkdown": ""}
    
    if json_str:
        try:
            parsed = json.loads(json_str)
            data.update(parsed)
            data["originalScore"] = parsed.get("original_score", {})
            data["annotatedEssay"] = parsed.get("annotated_essay")
            data["revisedScore"] = parsed.get("revised_score")
            
            # --- LOGIC DEEP SEARCH (QUÉT SÂU) ---
            sections = []
            
            # 1. Định nghĩa các nguồn dữ liệu tiềm năng
            sources_to_check = [
                parsed,                                      # Root object
                parsed.get("detailed_analysis", {}),         # Key tiêu chuẩn
                parsed.get("original_score", {}),            # AI hay nhầm nhét vào đây
                parsed.get("analysis", {})                   # Một key phổ biến khác
            ]

            # 2. Định nghĩa từ khóa nhận diện cho 4 tiêu chí
            criteria_keywords = {
                "Task Achievement": ["task_achievement", "ta_gap", "ta_analysis", "task_response", "achievement"],
                "Coherence & Cohesion": ["cohesion", "cc_gap", "cc_analysis", "linking", "coherence"],
                "Lexical Resource": ["lexical", "lr_gap", "lr_analysis", "vocabulary", "lexical_resource"],
                "Grammatical Range": ["grammatical", "gra_gap", "gra_analysis", "grammar", "grammatical_range"]
            }

            found_keys = set() # Tránh in trùng lặp

            for title, keywords in criteria_keywords.items():
                content_found = None
                
                # Duyệt qua từng nguồn dữ liệu
                for source in sources_to_check:
                    if not isinstance(source, dict): continue
                    
                    for k, v in source.items():
                        # Điều kiện chọn: Key chứa từ khóa VÀ Value là text dài (>50 ký tự)
                        if any(kw in k.lower() for kw in keywords) and isinstance(v, str) and len(v) > 50:
                            if k not in found_keys:
                                content_found = v
                                found_keys.add(k) # Đánh dấu đã dùng
                                break
                    if content_found: break 
                
                if content_found:
                    sections.append(f"### 📘 {title}\n{content_found}")

            # 3. Ghép kết quả
            if sections:
                data["analysisMarkdown"] = "\n\n".join(sections)
            
            # 4. Fallback: Nếu Deep Search thất bại, thử lấy key tổng
            elif parsed.get("analysis_markdown"):
                data["analysisMarkdown"] = parsed["analysis_markdown"]

        except Exception as e:
            data["analysisMarkdown"] = full_text.split("```json")[0]
            
    # Fallback cuối cùng
    if not data["analysisMarkdown"] or len(data["analysisMarkdown"]) < 20:
        if json_str:
             display_json = {k:v for k,v in parsed.items() if k not in ['annotated_essay', 'errors']} if 'parsed' in locals() else json_str
             data["analysisMarkdown"] = f"⚠️ **AI trả về định dạng lạ.** Dưới đây là nội dung thô tìm được:\n\n```json\n{json.dumps(display_json, indent=2, ensure_ascii=False)}\n```"
        else:
             data["analysisMarkdown"] = full_text

    return data

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
    doc.add_paragraph(analysis)
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
    elements.append(Paragraph("DETAILED ANALYSIS", styles['Heading1']))
    safe_text = html.escape(analysis).replace('\n', '<br/>')
    elements.append(Paragraph(safe_text, styles['Normal']))
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==========================================
# 4. UI: SESSION STATE INIT
# ==========================================
if "step" not in st.session_state: st.session_state.step = 1 
if "guide_data" not in st.session_state: st.session_state.guide_data = None
if "grading_result" not in st.session_state: st.session_state.grading_result = None
if "saved_topic" not in st.session_state: st.session_state.saved_topic = ""
if "saved_img" not in st.session_state: st.session_state.saved_img = None

# ==========================================
# 5. UI: PHASE 1 - INPUT & GUIDE
# ==========================================
st.title("🎓 IELTS Writing: Learn & Grade")

if st.session_state.step == 1:
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("1. Đề bài")
        question_input = st.text_area("Nhập câu hỏi:", height=150, placeholder="The chart below shows...", key="q_input")

    with col2:
        st.subheader("2. Hình ảnh")
        uploaded_image = st.file_uploader("Tải ảnh biểu đồ", type=['png', 'jpg', 'jpeg'], key="img_input")
        img_data = Image.open(uploaded_image) if uploaded_image else None
        if img_data: st.image(img_data, caption='Đề bài', use_container_width=True)

    if st.button("🚀 Phân tích & Hướng dẫn", type="primary"):
        if not question_input and not img_data:
            st.warning("Vui lòng nhập đề bài hoặc ảnh.")
        else:
            st.session_state.saved_topic = question_input
            st.session_state.saved_img = img_data
            
            with st.spinner("AI đang phân tích chiến thuật..."):
                prompt_guide = """
                Phân tích đề bài IELTS Writing Task 1. Trả về JSON:
                { "task_type": "...", "intro_guide": "...", "overview_guide": "...", "body1_guide": "...", "body2_guide": "..." }
                Viết hướng dẫn chi tiết bằng tiếng Việt.
                """
                res, _ = generate_content_with_failover(prompt_guide + "\n" + question_input, img_data, json_mode=True)
                if res:
                    data = parse_guide_response(res.text)
                    if data:
                        st.session_state.guide_data = data
                        st.session_state.step = 2
                        st.rerun()

# ==========================================
# 6. UI: PHASE 2 - WRITING PRACTICE
# ==========================================
if st.session_state.step == 2 and st.session_state.guide_data:
    data = st.session_state.guide_data
    st.markdown("---")
    st.success(f"📌 Loại bài: **{data.get('task_type', 'Task 1')}**")
    
    st.markdown("### ✍️ Thực hành viết bài")
    
    def render_input(title, guide, key):
        st.markdown(f"**{title}**")
        with st.expander(f"💡 Xem gợi ý", expanded=False):
            st.markdown(f"<div class='guide-box'>{guide}</div>", unsafe_allow_html=True)
        return st.text_area(f"Nhập {title}:", height=150, key=key)

    c1, c2 = st.columns(2)
    with c1:
        intro = render_input("Introduction", data.get("intro_guide"), "in_intro")
        body1 = render_input("Body 1", data.get("body1_guide"), "in_body1")
    with c2:
        over = render_input("Overview", data.get("overview_guide"), "in_overview")
        body2 = render_input("Body 2", data.get("body2_guide"), "in_body2")

    full_essay = f"{intro}\n\n{over}\n\n{body1}\n\n{body2}".strip()
    wc = len(full_essay.split())
    st.caption(f"📊 Số từ: {wc}")

    st.markdown("---")
    if st.button("✨ Gửi chấm điểm (Examiner Pro Mode)", type="primary", use_container_width=True):
        if wc < 20:
            st.warning("Bài viết quá ngắn.")
        else:
            status = st.status("👨‍🏫 Examiner đang chấm bài...", expanded=True)
            status.write("🔍 Quét lỗi ngữ pháp & Logic...")
            
            prompt_grade = GRADING_PROMPT_TEMPLATE.replace('{{TOPIC}}', st.session_state.saved_topic).replace('{{ESSAY}}', full_essay)
            
            res_grade, _ = generate_content_with_failover(prompt_grade, st.session_state.saved_img, json_mode=True)
            
            status.write("📝 Tổng hợp báo cáo...")
            if res_grade:
                p_data = parse_grading_response(res_grade.text)
                st.session_state.grading_result = {
                    "data": p_data, "essay": full_essay, "topic": st.session_state.saved_topic
                }
                st.session_state.step = 3
                status.update(label="✅ Đã chấm xong!", state="complete", expanded=False)
                st.rerun()
            else:
                status.update(label="❌ AI Đang bận, vui lòng thử lại!", state="error")

# ==========================================
# 7. UI: PHASE 3 - GRADING RESULT (EXAMINER UI)
# ==========================================
if st.session_state.step == 3 and st.session_state.grading_result:
    res = st.session_state.grading_result
    g_data = res["data"]
    
    st.markdown("## 🛡️ KẾT QUẢ ĐÁNH GIÁ CHI TIẾT")
    
    # 1. Bảng điểm Gốc
    scores = g_data.get("originalScore", {})
    st.markdown("### 📊 Điểm số hiện tại")
    cols = st.columns(5)
    cols[0].metric("Task Achievement", scores.get("task_achievement", "-"))
    cols[1].metric("Coherence", scores.get("cohesion_coherence", "-"))
    cols[2].metric("Lexical", scores.get("lexical_resource", "-"))
    cols[3].metric("Grammar", scores.get("grammatical_range", "-"))
    cols[4].metric("OVERALL", scores.get("overall", "-"))
    
    st.markdown("---")

    # 2. Tabs Chi tiết
    tab_analysis, tab_errors, tab_macro, tab_annotated = st.tabs([
        "📝 Phân tích 4 Tiêu chí", 
        "🔴 Lỗi Ngữ pháp/Từ vựng", 
        "🔵 Lỗi Mạch lạc/Logic",
        "✍️ Bài sửa (Annotated)"
    ])
    
    with tab_analysis:
        st.info("Dưới đây là nhận xét chi tiết của Giám khảo cho từng tiêu chí:")
        analysis_content = g_data.get("analysisMarkdown", "")
        if analysis_content:
            st.markdown(analysis_content)
        else:
            st.warning("Không tìm thấy nội dung phân tích chi tiết.")

    with tab_errors:
        errors = g_data.get("errors", [])
        micro = [e for e in errors if e.get('category') in ['Grammar', 'Vocabulary', 'Ngữ pháp', 'Từ vựng']]
        if not micro: st.success("Không tìm thấy lỗi ngữ pháp đáng kể.")
        for i, err in enumerate(micro):
            badge = "#DCFCE7" if err.get('category') in ['Grammar','Ngữ pháp'] else "#FEF9C3"
            st.markdown(f"""
            <div class="error-card">
                <div style="display:flex; justify-content:space-between; margin-bottom:5px;">
                    <span><b>#{i+1} [{err.get('category')}]</b>: {err.get('type')}</span>
                    <span style="background:#eee; padding:2px 8px; border-radius:10px; font-size:0.8em">{err.get('impact_level')}</span>
                </div>
                <div style="background:{badge}; padding:8px; border-radius:5px; margin-bottom:5px;">
                    <s>{err.get('original')}</s> ➔ <b>{err.get('correction')}</b>
                </div>
                <small><i>{err.get('explanation')}</i></small>
            </div>
            """, unsafe_allow_html=True)

    with tab_macro:
        macro = [e for e in errors if e.get('category') not in ['Grammar', 'Vocabulary', 'Ngữ pháp', 'Từ vựng']]
        if not macro: st.success("Cấu trúc mạch lạc tốt.")
        for err in macro:
            st.markdown(f"""
            <div class="error-card" style="border-left: 5px solid #3B82F6;">
                <b>[{err.get('category')}] {err.get('type')}</b><br>
                Vấn đề: {err.get('explanation')}<br>
                Gợi ý: <b>{err.get('correction')}</b>
            </div>
            """, unsafe_allow_html=True)

    with tab_annotated:
        st.markdown(f'<div class="annotated-text">{g_data.get("annotatedEssay", "")}</div>', unsafe_allow_html=True)

    # 3. Revised Score
    st.markdown("---")
    st.subheader("📈 Dự báo điểm sau khi sửa lỗi (Revised Score)")
    
    rev = g_data.get("revisedScore", {})
    if rev:
        r_cols = st.columns(5)
        r_cols[0].metric("TA (Rev)", rev.get("task_achievement", "-"))
        r_cols[1].metric("CC (Rev)", rev.get("cohesion_coherence", "-"))
        r_cols[2].metric("LR (Rev)", rev.get("lexical_resource", "-"))
        r_cols[3].metric("GRA (Rev)", rev.get("grammatical_range", "-"))
        r_cols[4].metric("OVERALL (Rev)", rev.get("overall", "-"))
        
        if rev.get("logic_re_evaluation"):
            st.info(f"💡 **Lưu ý của Giám khảo:** {rev.get('logic_re_evaluation')}")
    else:
        st.warning("Không có dữ liệu điểm dự báo.")

    # 4. Export Buttons
    st.markdown("---")
    d1, d2 = st.columns(2)
    
    full_report_text = g_data.get("analysisMarkdown", "")
    
    docx = create_docx(g_data, res['topic'], res['essay'], full_report_text)
    d1.download_button("📄 Download Report (.docx)", docx, "IELTS_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
    
    pdf = create_pdf(g_data, res['topic'], res['essay'], full_report_text)
    d2.download_button("📕 Download Report (.pdf)", pdf, "IELTS_Report.pdf", "application/pdf", use_container_width=True)
    
    if st.button("🔄 Làm bài mới (Reset)", use_container_width=True):
        st.session_state.step = 1
        st.session_state.guide_data = None
        st.session_state.grading_result = None
        st.session_state.saved_topic = ""
        st.session_state.saved_img = None
        st.rerun()
