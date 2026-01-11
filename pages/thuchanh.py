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

# Thư viện Word & PDF
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

# ==========================================
# 1. CẤU HÌNH & CSS (STYLE CỦA APP CHẤM ĐIỂM)
# ==========================================
st.set_page_config(page_title="IELTS Writing Master", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Merriweather:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Merriweather', serif !important; color: #0F172A !important; }
    
    /* Style cho Tutor Phase */
    .guide-box {
        background-color: #f8f9fa;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        color: #31333F;
    }

    /* Style cho Error Cards (Giống MessageBubble.tsx) */
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
    
    /* Highlight Styles */
    del { color: #9CA3AF; text-decoration: line-through; margin-right: 4px; text-decoration-thickness: 2px; }
    ins.grammar { background-color: #4ADE80; color: #022C22; text-decoration: none; padding: 2px 6px; border-radius: 4px; font-weight: 700; border: 1px solid #22C55E; }
    ins.vocab { background-color: #FDE047; color: #000; text-decoration: none; padding: 2px 6px; border-radius: 4px; font-weight: 700; border: 1px solid #FCD34D; }
    
    div.stButton > button { font-weight: bold; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIC AI & PROMPTS
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
            # Chỉ bật JSON mode nếu KHÔNG PHẢI là model Thinking (để tránh lỗi tương thích)
            # VÀ prompt yêu cầu JSON cụ thể (Tutor phase). 
            # Với Grading phase, ta cần lấy cả Text + JSON nên tắt json_mode
            if json_mode and "thinking" not in sel_model.lower():
                gen_config["response_mime_type"] = "application/json"
            
            if "thinking" in sel_model.lower():
                 gen_config["thinking_config"] = {"include_thoughts": True, "thinking_budget": 1024}

            response = temp_model.generate_content(content_parts, generation_config=gen_config)
            return response, sel_model 
            
        except Exception:
            continue
    return None, None

# --- PROMPT CHẤM ĐIỂM "KHỦNG" (NGUYÊN BẢN TỪ CODE BẠN GỬI) ---
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
*   **Quy tắc "Truy quét kiệt quệ" (Exhaustive Listing):**
    *   Tuyệt đối KHÔNG gộp lỗi. Nếu thí sinh sai 10 lỗi mạo từ, liệt kê đủ 10 mục.
    *   Danh sách lỗi trong JSON là bằng chứng pháp lý.

### 3. QUY TRÌNH CHẤM ĐIỂM & TỰ SỬA LỖI (SCORING & SELF-CORRECTION)
**Bước 1: Deep Scan & Lập danh sách lỗi (JSON Errors Array)**
**Bước 2: Tạo bản sửa lỗi (Annotated Essay)**
**Bước 3: Chấm lại bản sửa lỗi (JSON Output - Internal Re-grading)**

Sau khi đánh giá xong (viết phần phân tích chi tiết bằng lời văn), bạn **BẮT BUỘC** phải trích xuất dữ liệu kết quả cuối cùng dưới dạng một **JSON Object duy nhất** ở cuối câu trả lời.

Cấu trúc JSON:
```json
{
  "original_score": {
      "task_achievement": "Điểm TA của bài làm gốc",
      "cohesion_coherence": "Điểm CC của bài làm gốc",
      "lexical_resource": "Điểm LR của bài làm gốc",
      "grammatical_range": "Điểm GRA của bài làm gốc",
      "overall": "Điểm Overall của bài làm gốc"
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
      "word_count_check": "...",
      "logic_re_evaluation": "...",
      "task_achievement": "...",
      "cohesion_coherence": "...",
      "lexical_resource": "...",
      "grammatical_range": "...",
      "overall": "..."
  }
}
```

Thông tin bài làm:
a/ Đề bài (Task 1 question): {{TOPIC}}
b/ Bài làm của thí sinh (Written report): {{ESSAY}}
"""

# ==========================================
# 3. HELPER FUNCTIONS (COPY TỪ APP CHẤM ĐIỂM)
# ==========================================

def clean_json(text):
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match: return match.group(1).strip()
    # Nếu không có markdown code block, tìm cặp ngoặc {} ngoài cùng
    match_raw = re.search(r"\{[\s\S]*\}", text)
    if match_raw: return match_raw.group(0).strip()
    return None

def parse_guide_response(text):
    """Parse JSON cho phần Tutor (chỉ JSON thuần)"""
    try:
        j_str = clean_json(text)
        return json.loads(j_str) if j_str else None
    except: return None

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
            # Lưu lại input
            st.session_state.saved_topic = question_input
            st.session_state.saved_img = img_data
            
            with st.spinner("AI đang phân tích chiến thuật..."):
                prompt_guide = """
                Phân tích đề bài IELTS Writing Task 1. Trả về JSON:
                { "task_type": "...", "intro_guide": "...", "overview_guide": "...", "body1_guide": "...", "body2_guide": "..." }
                Viết hướng dẫn chi tiết bằng tiếng Việt.
                """
                # Bước này dùng JSON Mode để lấy hướng dẫn
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
            status.write("🔍 Đang áp dụng tiêu chuẩn Band 9.0...")
            
            # Thay thế biến vào Prompt
            prompt_grade = GRADING_PROMPT_TEMPLATE.replace('{{TOPIC}}', st.session_state.saved_topic).replace('{{ESSAY}}', full_essay)
            
            # Bước này KHÔNG dùng json_mode=True, để AI tự do viết Text phân tích trước rồi mới đến JSON
            res_grade, _ = generate_content_with_failover(prompt_grade, st.session_state.saved_img, json_mode=False)
            
            status.write("📝 Tổng hợp báo cáo...")
            if res_grade:
                # Xử lý kết quả bằng hàm chuẩn của App chấm điểm
                mk_text, p_data = process_grading_response(res_grade.text)
                st.session_state.grading_result = {
                    "data": p_data, 
                    "markdown": mk_text, # Lưu phần text phân tích riêng
                    "essay": full_essay, 
                    "topic": st.session_state.saved_topic
                }
                st.session_state.step = 3
                status.update(label="✅ Đã chấm xong!", state="complete", expanded=False)
                st.rerun()
            else:
                status.update(label="❌ Lỗi kết nối AI", state="error")

# ==========================================
# 7. UI: PHASE 3 - GRADING RESULT (EXAMINER UI)
# ==========================================
if st.session_state.step == 3 and st.session_state.grading_result:
    res = st.session_state.grading_result
    g_data = res["data"]
    analysis_text = res["markdown"] # Lấy text phân tích từ biến đã tách
    
    st.markdown("## 🛡️ KẾT QUẢ ĐÁNH GIÁ (EXAMINER REPORT)")
    
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
    
    # TAB 1: HIỂN THỊ PHẦN TEXT PHÂN TÍCH
    with tab_analysis:
        if analysis_text and len(analysis_text) > 50:
            st.markdown(analysis_text) # Hiển thị Markdown chuẩn
        else:
            st.warning("Không có dữ liệu phân tích chi tiết.")

    # TAB 2: LỖI MICRO (GRAMMAR/VOCAB)
    with tab_errors:
        errors = g_data.get("errors", [])
        micro = [e for e in errors if e.get('category') in ['Grammar', 'Vocabulary', 'Ngữ pháp', 'Từ vựng']]
        if not micro: st.success("Không tìm thấy lỗi ngữ pháp đáng kể.")
        for i, err in enumerate(micro):
            badge = "#DCFCE7" if err.get('category') in ['Grammar','Ngữ pháp'] else "#FEF9C3"
            
            # Sử dụng HTML thẻ div để render card đẹp như App Chấm điểm
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

    # TAB 3: LỖI MACRO (COHERENCE)
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

    # TAB 4: BÀI SỬA
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

    # 4. Export Buttons
    st.markdown("---")
    d1, d2 = st.columns(2)
    
    docx = create_docx(g_data, res['topic'], res['essay'], analysis_text)
    d1.download_button("📄 Download Report (.docx)", docx, "IELTS_Report.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
    
    pdf = create_pdf(g_data, res['topic'], res['essay'], analysis_text)
    d2.download_button("📕 Download Report (.pdf)", pdf, "IELTS_Report.pdf", "application/pdf", use_container_width=True)
    
    if st.button("🔄 Làm bài mới (Reset)", use_container_width=True):
        st.session_state.step = 1
        st.session_state.guide_data = None
        st.session_state.grading_result = None
        st.session_state.saved_topic = ""
        st.session_state.saved_img = None
        st.rerun()
