import streamlit as st
from google import genai
from google.genai import types
import json
import re
import time
import random
import os
from PIL import Image

# ==========================================
# 1. CẤU HÌNH TRANG & CSS
# ==========================================
st.set_page_config(page_title="Summary Master", page_icon="📝", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Merriweather:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stAppHeader, footer, .stDeployButton, #MainMenu { display: none; visibility: hidden; }

    .main-header { font-family: 'Merriweather', serif; color: #0F172A; font-weight: 700; font-size: 2.2rem; margin-top: -2rem; }
    .sub-header { color: #64748B; font-size: 1.1rem; margin-bottom: 1rem; border-bottom: 1px solid #E2E8F0; padding-bottom: 0.5rem; }
    .step-header { font-weight: 700; font-size: 1.3rem; color: #1E293B; margin-top: 1.5rem; margin-bottom: 0.5rem; background-color: #F8FAFC; padding: 10px; border-left: 5px solid #3B82F6; border-radius: 4px;}
    
    .guide-box { background-color: #EFF6FF; border: 1px dashed #93C5FD; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #1E3A8A; font-size: 0.95rem;}
    .theory-box { background-color: #FFFBEB; border-left: 4px solid #F59E0B; padding: 10px 15px; margin-bottom: 15px; font-size: 0.9rem;}
    
    /* Sticky Left Column */
    [data-testid="stHorizontalBlock"] { align-items: flex-start !important; }
    [data-testid="stHorizontalBlock"] > div:nth-child(1) { position: -webkit-sticky !important; position: sticky !important; top: 2rem !important; z-index: 999 !important; }
    [data-testid="stHorizontalBlock"] > div:nth-child(1) > div:nth-child(1) { max-height: 90vh !important; overflow-y: auto !important; padding-right: 10px !important; }
    
    /* Button Customization */
    div.stButton > button { background-color: #3B82F6; color: white; font-weight: bold; border-radius: 8px; padding: 0.5rem 1.5rem; border: none; }
    div.stButton > button:hover { background-color: #2563EB; }
    div.stButton > button:active { background-color: #1D4ED8; }
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

def clean_json(text):
    match = re.search(r"(\{[\s\S]*\})", text)
    return match.group(1).strip() if match else None

def generate_content_with_failover(prompt, image=None, json_mode=False):
    keys_to_try = list(ALL_KEYS)
    random.shuffle(keys_to_try) 
    
    model_priority = [
        #"gemini-3-flash-preview",        
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-pro", 
        "gemini-1.5-flash"
    ]
    
    last_error = ""
    
    status_msg = st.empty() 

    for index, current_key in enumerate(keys_to_try):
        try:
            if index > 0:
                status_msg.warning(f"⏳ Đang chuyển luồng AI #{index}...")
                time.sleep(2) 
            
            client = genai.Client(api_key=current_key)
            sel_model = "gemini-2.5-flash" # Default
            for target in model_priority:
                if target in [m.name.replace("models/", "") for m in client.models.list()]:
                    sel_model = target; break
            
            content_parts = [image, prompt] if image else [prompt]
            config_args = {"temperature": 0.2}
            if json_mode: config_args["response_mime_type"] = "application/json"

            status_msg.info("🚀 AI đang phân tích văn bản...")
            response = client.models.generate_content(
                model=sel_model, contents=content_parts, config=types.GenerateContentConfig(**config_args)
            )
            status_msg.empty()
            return response.text 
            
        except Exception as e:
            continue
                
    status_msg.empty()
    st.error("❌ Kết nối AI thất bại. Vui lòng thử lại sau.")
    return None

# ==========================================
# 3. HỆ THỐNG PROMPTS
# ==========================================

# Prompt 1: Phân tích trước bài đọc để làm gia sư (Dùng cho Bước 2 & 3)
ANALYSIS_PROMPT = """
Bạn là một chuyên gia dạy kỹ năng tóm tắt (Summary). Hãy phân tích bài đọc sau đây và trả về JSON chứa dữ liệu để hướng dẫn học sinh.
{
    "topic": "Chủ đề chính của bài viết (1 câu ngắn)",
    "thesis_guide": "Gợi ý nơi tìm Luận điểm chính (VD: Hãy nhìn vào câu cuối đoạn 1...)",
    "thesis_actual": "Luận điểm chính xác trích từ bài",
    "supporting_points": ["Ý chính 1", "Ý chính 2", "Ý chính 3..."],
    "details_to_omit_guide": "Hướng dẫn học sinh các từ khóa nhận diện chi tiết thừa trong bài này (VD: Hãy chú ý loại bỏ các ví dụ bắt đầu bằng such as... hoặc các số liệu phần trăm...)",
    "details_to_omit": ["Cụm chi tiết thừa 1", "Cụm chi tiết thừa 2"]
}
Bài đọc:
"""

# Prompt 2: Chấm điểm bài tóm tắt (Dùng cho Bước 5)
GRADING_PROMPT = """
Bạn là giám khảo chấm bài Summary. Hãy so sánh Bản tóm tắt của học sinh với Bài gốc. Đánh giá dựa trên 4 tiêu chí khắt khe:
1. Compare (Nội dung cốt lõi): Có đủ ý không? Có bị sai lệch ý tác giả không?
2. Conciseness (Ngắn gọn): Có loại bỏ thành công ví dụ, số liệu, chi tiết thừa không? Có độ dài phù hợp (khoảng 1/4 - 1/3 bài gốc) không?
3. Objectivity (Khách quan): Có bị đưa ý kiến cá nhân (I think, I agree) vào không?
4. Accuracy (Ngữ pháp/Từ vựng/Paraphrase): Học sinh có copy nguyên văn (word-by-word) không hay đã paraphrase tốt?

Trả về JSON:
{
    "score": "Điểm / 10",
    "content_feedback": "Nhận xét về nội dung (Đủ ý/Thiếu ý)",
    "conciseness_feedback": "Nhận xét về việc chắt lọc chi tiết thừa",
    "grammar_paraphrase_feedback": "Nhận xét về lỗi câu chữ và kỹ năng Paraphrase",
    "model_summary": "Viết một bản tóm tắt mẫu hoàn hảo (khoảng 80-120 từ, dùng từ nối tốt, khách quan)"
}
Bài gốc: {{ORIGINAL}}
Bản tóm tắt của học sinh: {{STUDENT}}
"""

# ==========================================
# 4. QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ==========================================
if "app_step" not in st.session_state: st.session_state.app_step = 1
if "original_text" not in st.session_state: st.session_state.original_text = ""
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "user_thesis" not in st.session_state: st.session_state.user_thesis = ""
if "user_points" not in st.session_state: st.session_state.user_points = ""
if "user_draft" not in st.session_state: st.session_state.user_draft = ""
if "ai_grading" not in st.session_state: st.session_state.ai_grading = None

def next_step(): st.session_state.app_step += 1
def reset_app():
    for key in st.session_state.keys(): del st.session_state[key]
    st.rerun()

# ==========================================
# 5. GIAO DIỆN CÁC BƯỚC
# ==========================================
st.markdown('<div class="main-header">📝 Summary Master Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Luyện tập kỹ năng Viết Tóm tắt theo Quy trình 4 Bước chuẩn Học thuật</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# APP STEP 1: NHẬP VĂN BẢN
# ---------------------------------------------------------
if st.session_state.app_step == 1:
    st.markdown('<div class="step-header">BƯỚC CHUẨN BỊ: Nhập Văn Bản Gốc</div>', unsafe_allow_html=True)
    st.info("💡 Hãy dán nội dung bài báo, đoạn văn hoặc tài liệu bạn muốn tóm tắt vào đây. Hệ thống AI sẽ đọc trước và chuẩn bị kế hoạch hướng dẫn bạn.")
    
    input_text = st.text_area("Nội dung bài viết:", height=300, placeholder="Dán văn bản tiếng Anh vào đây (Ví dụ: bài đọc IELTS, báo cáo...)")
    
    if st.button("🚀 Bắt đầu Phân tích", width="stretch", type="primary"):
        if len(input_text.split()) < 50:
            st.warning("⚠️ Văn bản quá ngắn (dưới 50 từ). Vui lòng nhập đoạn văn dài hơn để tóm tắt hiệu quả.")
        else:
            with st.spinner("Đang " + "đọc lướt" + " và " + "đọc sâu" + " văn bản..."):
                res = generate_content_with_failover(ANALYSIS_PROMPT + input_text, json_mode=True)
                if res:
                    try:
                        st.session_state.ai_analysis = json.loads(clean_json(res))
                        st.session_state.original_text = input_text
                        st.session_state.app_step = 2
                        st.rerun()
                    except:
                        st.error("Lỗi trích xuất dữ liệu AI. Vui lòng thử lại.")

# ---------------------------------------------------------
# APP STEP 2: PDF BƯỚC 1 - HIỂU
# ---------------------------------------------------------
elif st.session_state.app_step == 2:
    data = st.session_state.ai_analysis
    
    col1, col2 = st.columns([4, 6], gap="large")
    with col1:
        st.markdown("### 📄 Văn bản gốc")
        st.markdown(f'<div style="background:#F1F5F9; padding:15px; border-radius:8px; max-height: 70vh; overflow-y:auto;">{st.session_state.original_text}</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="step-header">BƯỚC 1: HIỂU - Đọc và Nắm bắt cốt lõi</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Mục tiêu:</b> Không chỉ đọc chữ, mà phải hiểu cấu trúc. Tìm bằng được Topic và Luận điểm chính (Thesis Statement).</div>', unsafe_allow_html=True)
        
        # AI Gợi ý
        with st.expander("🤖 Gia sư AI gợi ý Skimming (Đọc lướt):", expanded=True):
            st.markdown(f"**Chủ đề bài viết (Topic):** {data.get('topic')}")
            st.markdown(f"**Gợi ý tìm Thesis:** {data.get('thesis_guide')}")
        
        st.markdown("---")
        st.markdown("**Nhiệm vụ của bạn:** Dựa vào bài đọc và gợi ý, hãy copy/paste hoặc tự viết lại Luận điểm chính (Thesis Statement) vào ô dưới đây.")
        
        thesis_input = st.text_area("Luận điểm chính của bài là gì?", value=st.session_state.user_thesis, height=100)
        
        if st.button("Tiếp tục: Bước 2 (Chắt lọc) ➡️", type="primary"):
            st.session_state.user_thesis = thesis_input
            st.session_state.app_step = 3
            st.rerun()

# ---------------------------------------------------------
# APP STEP 3: PDF BƯỚC 2 - CHẮT LỌC
# ---------------------------------------------------------
elif st.session_state.app_step == 3:
    data = st.session_state.ai_analysis
    
    col1, col2 = st.columns([4, 6], gap="large")
    with col1:
        st.markdown("### 📄 Văn bản gốc")
        st.markdown(f'<div style="background:#F1F5F9; padding:15px; border-radius:8px; max-height: 70vh; overflow-y:auto;">{st.session_state.original_text}</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="step-header">BƯỚC 2: CHẮT LỌC - Rút Ý chính & Bỏ Chi tiết phụ</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Quy tắc vàng:</b> Tóm tắt là giữ lại "cái gì" (what), không phải "như thế nào" (how). Mạnh dạn dùng dao mổ cắt bỏ Ví dụ, Số liệu, Giai thoại.</div>', unsafe_allow_html=True)
        
        with st.expander("🤖 Gia sư AI hướng dẫn dọn dẹp (The Surgeon's Cut):", expanded=True):
            st.markdown(f"**Dấu hiệu cần cắt bỏ:** {data.get('details_to_omit_guide')}")
            st.markdown("**Ví dụ các chi tiết tôi tìm thấy bạn KHÔNG NÊN đưa vào tóm tắt:**")
            for item in data.get('details_to_omit', []):
                st.markdown(f"- ❌ <s>{item}</s>", unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("**Nhiệm vụ của bạn:** Hãy hệ thống hóa các Ý chính hỗ trợ (Supporting Points). Liệt kê chúng dưới dạng Gạch đầu dòng (Chưa cần viết thành đoạn văn).")
        
        points_input = st.text_area("Dàn ý tinh gọn (Các ý chính):", value=st.session_state.user_points, height=150, placeholder="- Ý chính 1...\n- Ý chính 2...")
        
        col_b1, col_b2 = st.columns(2)
        if col_b1.button("⬅️ Quay lại Bước 1"):
            st.session_state.app_step = 2; st.rerun()
        if col_b2.button("Tiếp tục: Bước 3 (Viết nháp) ➡️", type="primary"):
            st.session_state.user_points = points_input
            st.session_state.app_step = 4
            st.rerun()

# ---------------------------------------------------------
# APP STEP 4: PDF BƯỚC 3 - VIẾT NHÁP
# ---------------------------------------------------------
elif st.session_state.app_step == 4:
    col1, col2 = st.columns([4, 6], gap="large")
    with col1:
        st.markdown("### 🗂️ Dàn ý của bạn")
        st.success("**Luận điểm chính:**\n" + st.session_state.user_thesis)
        st.info("**Các ý hỗ trợ:**\n" + st.session_state.user_points)
        
    with col2:
        st.markdown('<div class="step-header">BƯỚC 3: VIẾT - Soạn thảo Bản nháp & Paraphrase</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Mục tiêu:</b> Lắp ráp dàn ý thành 1 đoạn văn mạch lạc. Sử dụng "Từ nối" (First, Furthermore, Consequently...) và áp dụng kỹ thuật Paraphrase (Tell a Friend / Chunking) để diễn đạt bằng lời của bạn. Dưy trì thái độ Khách quan tuyệt đối.</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("**Nhiệm vụ của bạn:** Viết bản tóm tắt hoàn chỉnh. Hãy bắt đầu bằng Câu Mở Đầu giới thiệu Tác phẩm/Tác giả và Luận điểm chính.")
        
        draft_input = st.text_area("Bản Tóm tắt của bạn (Khoảng 1/4 độ dài bài gốc):", value=st.session_state.user_draft, height=250)
        
        # Word count logic
        wc = len(draft_input.split()) if draft_input else 0
        st.markdown(f"<div style='text-align:right; color: #64748B;'>Số từ hiện tại: <b>{wc}</b></div>", unsafe_allow_html=True)
        
        col_b1, col_b2 = st.columns(2)
        if col_b1.button("⬅️ Quay lại Bước 2"):
            st.session_state.app_step = 3; st.rerun()
        
        if col_b2.button("Hoàn thiện & Gửi chấm điểm 🎓", type="primary"):
            if wc < 20:
                st.warning("Bài viết quá ngắn. Hãy triển khai thêm ý.")
            else:
                st.session_state.user_draft = draft_input
                with st.spinner("👨‍🏫 Giám khảo đang đối chiếu bài tóm tắt của bạn với văn bản gốc..."):
                    grade_prompt = GRADING_PROMPT.replace("{{ORIGINAL}}", st.session_state.original_text).replace("{{STUDENT}}", draft_input)
                    res = generate_content_with_failover(grade_prompt, json_mode=True)
                    if res:
                        st.session_state.ai_grading = json.loads(clean_json(res))
                        st.session_state.app_step = 5
                        st.rerun()

# ---------------------------------------------------------
# APP STEP 5: PDF BƯỚC 4 - KẾT QUẢ & HOÀN THIỆN
# ---------------------------------------------------------
elif st.session_state.app_step == 5:
    res = st.session_state.ai_grading
    
    st.markdown('<div class="step-header">BƯỚC 4: HOÀN THIỆN - Đánh giá & Rà soát cuối cùng</div>', unsafe_allow_html=True)
    
    col_score, col_detail = st.columns([3, 7], gap="medium")
    
    with col_score:
        st.markdown(f"""
        <div style="background: #ECFDF5; border: 2px solid #10B981; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h3 style="color: #047857; margin-bottom: 0;">ĐIỂM ĐÁNH GIÁ</h3>
            <h1 style="color: #059669; font-size: 3.5rem; margin-top: 0;">{res.get('score', 'N/A')}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("✍️ Bản tóm tắt của bạn", expanded=True):
            st.write(st.session_state.user_draft)
    
    with col_detail:
        tab1, tab2, tab3 = st.tabs(["📝 Nhận xét chi tiết", "💡 Bài tóm tắt Mẫu (Giám khảo)", "🔄 Rà soát lỗi cơ bản"])
        
        with tab1:
            st.markdown(f"**1. Độ bao quát (Compare):**\n{res.get('content_feedback')}")
            st.markdown("---")
            st.markdown(f"**2. Tính súc tích (Conciseness):**\n{res.get('conciseness_feedback')}")
            st.markdown("---")
            st.markdown(f"**3. Ngôn từ & Khách quan (Accuracy):**\n{res.get('grammar_paraphrase_feedback')}")
            
        with tab2:
            st.markdown('<div style="background: #EFF6FF; padding: 15px; border-radius: 8px; font-family: Merriweather, serif; line-height: 1.6;">' + res.get('model_summary', '') + '</div>', unsafe_allow_html=True)
            st.caption("Hãy so sánh bài của bạn với bài mẫu để học cách dùng từ nối và gộp ý (Chunking).")
            
        with tab3:
            st.markdown("""
            **Tự kiểm tra trước khi nộp bài thực tế (Proofreading Check):**
            - [ ] Đã kiểm tra lỗi chính tả (Spelling).
            - [ ] Đã kiểm tra sự hòa hợp Chủ ngữ - Động từ (S-V Agreement).
            - [ ] Đã dùng thì Hiện tại đơn (Simple Present) để báo cáo quan điểm tác giả chưa? (VD: The author argues...)
            - [ ] Dấu phẩy đã đặt đúng sau các từ nối chưa? (VD: Furthermore, ...)
            """)
    
    st.markdown("---")
    if st.button("🔄 Làm bài Tóm tắt mới", type="primary"):
        reset_app()
