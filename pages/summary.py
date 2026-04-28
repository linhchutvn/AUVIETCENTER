import streamlit as st
from google import genai
from google.genai import types
import json
import re
import time
import random
from PIL import Image

# ==========================================
# 1. CẤU HÌNH TRANG & CSS
# ==========================================
st.set_page_config(page_title="Summary Master Pro", page_icon="📝", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Merriweather:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stAppHeader, footer, .stDeployButton, #MainMenu { display: none; visibility: hidden; }

    .main-header { font-family: 'Merriweather', serif; color: #0F172A; font-weight: 700; font-size: 2.2rem; margin-top: -2rem; }
    .sub-header { color: #64748B; font-size: 1.1rem; margin-bottom: 1rem; border-bottom: 1px solid #E2E8F0; padding-bottom: 0.5rem; }
    .step-header { font-weight: 700; font-size: 1.3rem; color: #1E293B; margin-top: 1.5rem; margin-bottom: 0.5rem; background-color: #F8FAFC; padding: 10px; border-left: 5px solid #3B82F6; border-radius: 4px;}
    
    .guide-box { background-color: #EFF6FF; border: 1px dashed #3B82F6; padding: 15px; border-radius: 8px; margin-bottom: 15px; color: #1E3A8A; font-size: 0.95rem;}
    .theory-box { background-color: #FFFBEB; border-left: 4px solid #F59E0B; padding: 10px 15px; margin-bottom: 15px; font-size: 0.9rem;}
    
    /* Sticky Left Column */
    [data-testid="stHorizontalBlock"] { align-items: flex-start !important; }
    [data-testid="stHorizontalBlock"] > div:nth-child(1) { position: -webkit-sticky !important; position: sticky !important; top: 2rem !important; z-index: 999 !important; }
    
    /* Button Customization */
    div.stButton > button { background-color: #3B82F6; color: white; font-weight: bold; border-radius: 8px; padding: 0.5rem 1.5rem; border: none; }
    div.stButton > button:hover { background-color: #2563EB; }
    
    /* Highlight Tools */
    .reporting-verb { color: #D97706; font-weight: bold; }
    .transition-word { color: #059669; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIC AI & XỬ LÝ DỮ LIỆU
# ==========================================
try:
    ALL_KEYS = st.secrets["GEMINI_API_KEYS"]
except Exception:
    st.error("⚠️ Thầy/Cô chưa cấu hình secrets.toml chứa GEMINI_API_KEYS!")
    st.stop()

def clean_json(text):
    if not text: return None
    text = str(text).replace("```json\n", "").replace("```json", "").replace("```", "").strip()
    match = re.search(r"(\{[\s\S]*\})", text)
    return match.group(1).strip() if match else text

def generate_content_with_failover(prompt, image=None, json_mode=False):
    keys_to_try = list(ALL_KEYS)
    random.shuffle(keys_to_try) 
    model_priority = ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"]
    status_msg = st.empty() 

    for index, current_key in enumerate(keys_to_try):
        try:
            if index > 0:
                status_msg.warning(f"⏳ Luồng #{index} bận. Đang thử luồng khác...")
                time.sleep(2) 
            
            client = genai.Client(api_key=current_key)
            raw_models = list(client.models.list())
            available_models = [m.name.replace("models/", "") for m in raw_models]
            sel_model = next((m for m in model_priority if m in available_models), "gemini-1.5-flash")
            
            content_parts = [image, prompt] if image else [prompt]
            config_args = {"temperature": 0.2, "max_output_tokens": 8000}
            if json_mode and "thinking" not in sel_model.lower():
                config_args["response_mime_type"] = "application/json"

            status_msg.info(f"🚀 Cố vấn AI đang xử lý dữ liệu...")
            response = client.models.generate_content(
                model=sel_model, contents=content_parts, config=types.GenerateContentConfig(**config_args)
            )
            status_msg.empty()
            return response.text if response else None
            
        except Exception as e:
            continue
                
    status_msg.empty()
    st.error(f"❌ Tất cả luồng kết nối đều thất bại. Vui lòng thử lại sau.")
    return None

# ==========================================
# 3. HỆ THỐNG PROMPTS (ĐÃ ĐƯỢC GIÁO SƯ CHỈNH SỬA)
# ==========================================
ANALYSIS_PROMPT = """
Bạn là một Giáo sư dạy kỹ năng tóm tắt (Summary). Người dùng cung cấp văn bản hoặc hình ảnh chứa văn bản. Hãy phân tích và trả về định dạng JSON nghiêm ngặt sau:
{
    "extracted_text": "Trích xuất toàn bộ nội dung chữ tiếng Anh từ hình ảnh. Thay dấu ngoặc kép thành nháy đơn để tránh lỗi hiển thị.",
    "topic": "Chủ đề chính của bài viết (1 câu ngắn)",
    "thesis_guide": "Gợi ý nơi tìm Luận điểm chính (Thường ở cuối đoạn mở đầu hoặc kết luận)",
    "thesis_actual": "Luận điểm chính xác trích từ bài",
    "supporting_points": ["Ý chính 1", "Ý chính 2", "Ý chính 3"],
    "details_to_omit_guide": "Hướng dẫn học sinh nhận diện các chi tiết thừa trong bài này",
    "details_to_omit": [
        {
            "phrase": "COPY CHÍNH XÁC Y NGUYÊN 100% MỘT CỤM TỪ NGẮN CẦN CẮT BỎ TỪ BÀI GỐC (Chỉ lấy cụm từ đặc trưng, không lấy cả câu dài để code Python dễ Replace)",
            "type": "Phân loại lỗi (Ví dụ: Examples, Statistics, Descriptive Details, Quotes, Repetitions)",
            "reason": "Giải thích ngắn gọn tại sao phải cắt bỏ cụm từ này theo chuẩn Academic Summary."
        }
    ]
}
Dữ liệu đầu vào:
"""

# ĐÃ FIX LỖI: Thêm mảng "detailed_comparison" vào JSON schema để UI gọi ra không bị lỗi.
GRADING_PROMPT = """
Bạn là một giám khảo chấm thi tiếng Anh khắt khe. Hãy chấm điểm bản tóm tắt của học sinh dựa trên văn bản gốc. 
Hệ thống chấm điểm tổng là 1.0 ĐIỂM, được chia thành 3 tiêu chí:

1. Main Ideas (0.4 pt): Tóm tắt có bám sát các ý chính và thông điệp cốt lõi của bài gốc không? Đủ ý trọn 0.4, thiếu ý trừ dần.
2. Own wording (0.4 pt): Học sinh có dùng từ ngữ của riêng mình (paraphrase) không? Nếu copy y nguyên cả câu từ bài gốc -> 0 điểm phần này. Nếu có đổi cấu trúc, đổi từ vựng -> 0.4 điểm.
3. Word limit (0.2 pt): Yêu cầu là "khoảng 100 - 120 từ". Độ dài lý tưởng là 100 - 120 từ (đạt 0.2 pt). Quá dài/ngắn trừ điểm.

YÊU CẦU ĐẶC BIỆT VỀ "ĐỐI CHIẾU & NÂNG CẤP":
Bạn BẮT BUỘC phải nhặt ra 2-4 chỗ trong bài của học sinh cần SỬA, THÊM, hoặc NÂNG CẤP TỪ VỰNG so với bài mẫu.
Lưu ý: Chỉ đề xuất từ vựng ở mức độ TRUNG BÌNH KHÁ (B1, B2). Không dùng từ quá học thuật (C1, C2).

Trả về BẮT BUỘC định dạng JSON sau:
{
    "total_score": "0.8/1.0",
    "score_ideas": "0.3/0.4",
    "feedback_ideas": "Nhận xét chi tiết về việc chọn lọc ý chính...",
    "score_wording": "0.3/0.4",
    "feedback_wording": "Nhận xét chi tiết về kỹ năng paraphrase...",
    "actual_word_count": "Đếm chính xác số từ",
    "score_word_limit": "0.2/0.2",
    "feedback_word_limit": "Nhận xét về độ dài...",
    "model_summary": "Viết một bản tóm tắt mẫu hoàn hảo (chính xác 100 - 120 từ, paraphrase xuất sắc, đủ ý).",
    "detailed_comparison": [
        {
            "action": "NÂNG CẤP (hoặc THÊM, SỬA)",
            "student_text": "Trích đoạn của học sinh",
            "suggested_text": "Đoạn đề xuất tốt hơn (B1-B2)",
            "explanation": "Lý do vì sao đề xuất này tốt hơn."
        }
    ]
}
Bài gốc: {{ORIGINAL}}
Bản tóm tắt của học sinh: {{STUDENT}}
""" 

# ==========================================
# 4. QUẢN LÝ TRẠNG THÁI (SESSION STATE)
# ==========================================
if "app_step" not in st.session_state: st.session_state.app_step = 1
if "original_text" not in st.session_state: st.session_state.original_text = ""
if "original_img" not in st.session_state: st.session_state.original_img = None
if "ai_analysis" not in st.session_state: st.session_state.ai_analysis = None
if "user_thesis" not in st.session_state: st.session_state.user_thesis = ""
if "user_points" not in st.session_state: st.session_state.user_points = ""
if "user_draft" not in st.session_state: st.session_state.user_draft = ""
if "ai_grading" not in st.session_state: st.session_state.ai_grading = None
if "user_draft_intro" not in st.session_state: st.session_state.user_draft_intro = ""
if "user_draft_body" not in st.session_state: st.session_state.user_draft_body = ""
if "user_draft_concl" not in st.session_state: st.session_state.user_draft_concl = ""
    
def reset_app():
    for key in st.session_state.keys(): del st.session_state[key]
    st.rerun()

def render_annotated_sidebar(original_text, omit_data=None):
    st.markdown("### 📄 Nguồn bài gốc")
    with st.container(height=650, border=True):
        if st.session_state.original_img:
            st.image(st.session_state.original_img, use_container_width=True)
            st.markdown("---")
        
        display_text = original_text
        
        if omit_data:
            # Sắp xếp các chuỗi dài thay thế trước để không bị dính vào nhau
            omit_data = sorted(omit_data, key=lambda x: len(x.get('phrase', '')), reverse=True)
            for item in omit_data:
                phrase = item.get('phrase', '').strip()
                if phrase and phrase in display_text:
                    styled_phrase = f'<del title="{item.get("reason", "")}" style="color: #EF4444; background-color: #FEE2E2; text-decoration-thickness: 2px; cursor: help;">{phrase}</del>'
                    display_text = display_text.replace(phrase, styled_phrase)

        st.markdown(f'<div style="background:#F8FAFC; padding:15px; border-radius:8px; font-size: 0.95rem; line-height: 1.8;">{display_text}</div>', unsafe_allow_html=True)

# ==========================================
# 5. GIAO DIỆN CÁC BƯỚC
# ==========================================
st.markdown('<div class="main-header">📝 Summary Master Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Luyện tập kỹ năng Viết Tóm tắt theo Quy trình 4 Bước chuẩn Học thuật (Tích hợp AI)</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# APP STEP 1: NHẬP ĐỀ BÀI
# ---------------------------------------------------------
if st.session_state.app_step == 1:
    st.markdown('<div class="step-header">BƯỚC CHUẨN BỊ: Nhập Đề Bài</div>', unsafe_allow_html=True)
    st.info("💡 Bạn có thể **Tải ảnh lên (hỗ trợ kéo thả / Paste Ctrl+V)** HOẶC **Dán đoạn văn bản** vào ô bên dưới.")
    
    col_input1, col_input2 = st.columns(2, gap="large")
    
    with col_input1:
        st.markdown("**Cách 1: Tải ảnh chụp đoạn văn**")
        uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        img_data = None
        if uploaded_file:
            img_data = Image.open(uploaded_file)
            st.image(img_data, caption="Ảnh đề bài đã tải", use_container_width=True)

    with col_input2:
        st.markdown("**Cách 2: Dán trực tiếp văn bản tiếng Anh**")
        input_text = st.text_area("Text Input", height=200, placeholder="Dán văn bản tiếng Anh vào đây...", label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 Phân tích & Bắt đầu bài học", width="stretch", type="primary"):
        if not input_text.strip() and not img_data:
            st.warning("⚠️ Vui lòng tải hình ảnh HOẶC dán văn bản để bắt đầu.")
        else:
            with st.spinner("Giáo sư AI đang đọc tài liệu và thiết kế giáo án riêng cho bạn..."):
                final_prompt = ANALYSIS_PROMPT + (f"\n\nText từ người dùng:\n{input_text}" if input_text else "")
                res = generate_content_with_failover(final_prompt, image=img_data, json_mode=True)
                
                if res:
                    try:
                        ai_data = json.loads(clean_json(res))
                        st.session_state.ai_analysis = ai_data
                        st.session_state.original_text = ai_data.get("extracted_text", input_text)
                        st.session_state.original_img = img_data
                        st.session_state.app_step = 2
                        st.rerun()
                    except Exception as e:
                        st.error("❌ Lỗi giải mã dữ liệu JSON từ AI.")
                        with st.expander("Chi tiết lỗi (Dành cho Debug):"):
                            st.write(str(e))
                            st.code(res)

# ---------------------------------------------------------
# APP STEP 2: BƯỚC 1 - HIỂU
# ---------------------------------------------------------
elif st.session_state.app_step == 2:
    data = st.session_state.ai_analysis
    col1, col2 = st.columns([4, 6], gap="large")
    
    with col1: render_annotated_sidebar(st.session_state.original_text)
    
    with col2:
        st.markdown('<div class="step-header">BƯỚC 1: HIỂU - Đọc và Nắm bắt cốt lõi</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Mục tiêu:</b> Không thể tóm tắt thứ mà bạn không hiểu. Hãy dùng kỹ năng Skimming để tìm <b>Topic</b> và <b>Thesis Statement</b> (Thường nằm ở cuối đoạn mở đầu).</div>', unsafe_allow_html=True)
        
        with st.expander("🤖 Gia sư AI gợi ý Skimming (Đọc lướt):", expanded=True):
            st.markdown(f"🎯 **Chủ đề bài viết:** {data.get('topic')}")
            st.markdown(f"📍 **Gợi ý tìm Thesis:** {data.get('thesis_guide')}")
            
        st.markdown("---")
        st.markdown("**Nhiệm vụ của bạn:** Viết lại Luận điểm chính (Thesis Statement) vào ô dưới đây (Bằng lời của bạn hoặc chép nguyên văn đều được).")
        thesis_input = st.text_area("Luận điểm chính của bài là gì?", value=st.session_state.user_thesis, height=100)
        
        if st.button("Tiếp tục: Bước 2 (Chắt lọc) ➡️", type="primary"):
            st.session_state.user_thesis = thesis_input; st.session_state.app_step = 3; st.rerun()

# ---------------------------------------------------------
# APP STEP 3: BƯỚC 2 - CHẮT LỌC 
# ---------------------------------------------------------
elif st.session_state.app_step == 3:
    data = st.session_state.ai_analysis
    col1, col2 = st.columns([4, 6], gap="large")
    
    with col1: render_annotated_sidebar(st.session_state.original_text, data.get('details_to_omit'))
    
    with col2:
        st.markdown('<div class="step-header">BƯỚC 2: CHẮT LỌC - Rút Ý chính & Bỏ Chi tiết phụ</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Quy tắc vàng:</b> Tóm tắt là giữ lại <b>"cái gì" (what)</b>, không phải <b>"như thế nào" (how in detail)</b>. Hãy nhìn sang cột trái, các chi tiết thừa đã được AI dùng "dao mổ" gạch bỏ màu đỏ. Rê chuột vào phần gạch đỏ để xem lý do.</div>', unsafe_allow_html=True)
        
        with st.expander("🤖 Lớp học Giải phẫu Văn bản (Tại sao lại gạch bỏ?):", expanded=True):
            st.markdown(f"**💡 Hướng dẫn nhận diện:** {data.get('details_to_omit_guide')}")
            st.markdown("---")
            for idx, item in enumerate(data.get('details_to_omit', [])):
                st.markdown(f"**{idx + 1}. Bỏ cụm:** <del style='color: gray;'>{item.get('phrase')}</del>", unsafe_allow_html=True)
                st.markdown(f"🏷️ **Phân loại:** `{item.get('type', 'Details')}`")
                st.markdown(f"👉 **Lý do:** <span style='color: #D97706;'>{item.get('reason')}</span>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
        st.markdown("---")
        st.markdown("**Nhiệm vụ của bạn:** Bỏ qua phần màu đỏ, hãy hệ thống hóa các Ý chính hỗ trợ (Supporting Points) còn lại thành các gạch đầu dòng.")
        points_input = st.text_area("Dàn ý tinh gọn của bạn:", value=st.session_state.user_points, height=150)
        
        col_b1, col_b2 = st.columns(2)
        if col_b1.button("⬅️ Quay lại Bước 1"): st.session_state.app_step = 2; st.rerun()
        if col_b2.button("Tiếp tục: Bước 3 (Viết nháp) ➡️", type="primary"):
            st.session_state.user_points = points_input; st.session_state.app_step = 4; st.rerun()

# ---------------------------------------------------------
# APP STEP 4: BƯỚC 3 - VIẾT NHÁP (DÂY CHUYỀN LẮP RÁP)
# ---------------------------------------------------------
elif st.session_state.app_step == 4:
    data = st.session_state.ai_analysis
    
    # -- Cột Trái: Giữ nguyên Dàn ý & Nguồn để học sinh đối chiếu --
    col1, col2 = st.columns([4, 6], gap="large")
    with col1:
        st.markdown("### 🗂️ Dàn ý cốt lõi của bạn")
        with st.container(height=650, border=True):
            st.success("**Luận điểm chính (Thesis):**\n\n" + st.session_state.user_thesis)
            st.info("**Các ý hỗ trợ (Points):**\n\n" + st.session_state.user_points)
            with st.expander("📄 Xem lại văn bản gốc (Đã gạch bỏ chi tiết phụ)", expanded=False):
                render_annotated_sidebar(st.session_state.original_text, data.get('details_to_omit'))
                
    # -- Cột Phải: Dây chuyền Viết từng bước --
    with col2:
        st.markdown('<div class="step-header">BƯỚC 3: VIẾT - Dây Chuyền Lắp Ráp (Drafting)</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box">Hãy chia nhỏ để trị! Chúng ta sẽ viết từng phần riêng biệt, sau đó hệ thống sẽ giúp bạn ghép lại thành một bài hoàn chỉnh.</div>', unsafe_allow_html=True)
        
        tab_intro, tab_body, tab_concl, tab_final = st.tabs(["1. Câu Mở Đầu", "2. Thân Bài", "3. Câu Kết", "4. 🧩 Lắp Ráp & Nộp Bài"])
        
        # --- TAB 1: CÂU MỞ ĐẦU ---
        with tab_intro:
            st.markdown("#### 🚪 Viết Câu Mở Đầu (Opening Sentence)")
            st.markdown("""
            **Công thức:** `Tên Tác phẩm` + `Reporting Verb` + `Thesis (đã paraphrase)`
            * <span class='reporting-verb'>Reporting Verbs:</span> states, explains, describes (Trung lập) | argues, claims, asserts (Lập luận).
            * **Ví dụ:** *"The passage explains that green cities focus on protecting the environment..."*
            """, unsafe_allow_html=True)
            
            st.session_state.user_draft_intro = st.text_area("Viết 1 câu mở đầu dựa trên Luận điểm (Thesis) bên trái:", 
                                                             value=st.session_state.user_draft_intro, height=120, key="intro_box")
            
        # --- TAB 2: THÂN BÀI ---
        with tab_body:
            st.markdown("#### 🧱 Viết Thân Bài (Body Paragraph)")
            st.markdown("""
            **Nhiệm vụ:** Chuyển các gạch đầu dòng (Points) bên trái thành các câu hoàn chỉnh.
            * **Từ nối (Transitions):** Đừng liệt kê rời rạc. Hãy dùng <span class='transition-word'>First, Additionally, Furthermore, However, Consequently...</span>
            * **Vũ khí Paraphrase:** 
                * *Kể cho bạn nghe:* Đọc ý chính, nhắm mắt lại và viết ra bằng từ ngữ đơn giản.
                * *Hộp công cụ Ngữ pháp:* Đổi Danh từ ↔ Động từ, đổi Chủ động ↔ Bị động.
            """, unsafe_allow_html=True)
            
            st.session_state.user_draft_body = st.text_area("Viết các câu thân bài, nhớ dùng TỪ NỐI giữa các ý:", 
                                                            value=st.session_state.user_draft_body, height=200, key="body_box")
            
        # --- TAB 3: CÂU KẾT LUẬN ---
        with tab_concl:
            st.markdown("#### 🏁 Viết Câu Kết Luận (Concluding Sentence)")
            st.markdown("""
            **Mục tiêu:** Tóm lại thông điệp cốt lõi nhất, hoặc lời kêu gọi hành động của tác giả. KHÔNG lặp lại y chang câu mở đầu.
            * **Từ nối gợi ý:** <span class='transition-word'>In conclusion, Ultimately, To sum up,...</span>
            * **Ví dụ:** *"Ultimately, the main goal of these actions is to build a better future."*
            """, unsafe_allow_html=True)
            
            st.session_state.user_draft_concl = st.text_area("Viết 1 câu kết luận cho bài tóm tắt:", 
                                                             value=st.session_state.user_draft_concl, height=120, key="concl_box")

        # --- TAB 4: LẮP RÁP & NỘP BÀI ---
        with tab_final:
            st.markdown("#### ✨ Đánh Bóng Bản Nháp (The Final Polish)")
            
            # Tự động ghép nối nếu người dùng đã nhập liệu
            auto_assembled = f"{st.session_state.user_draft_intro} {st.session_state.user_draft_body} {st.session_state.user_draft_concl}".strip()
            
            # Nếu user chưa gõ gì vào ô Final nhưng có data ghép nối, thì điền auto_assembled vào
            if not st.session_state.user_draft and auto_assembled:
                current_draft = auto_assembled
            else:
                current_draft = st.session_state.user_draft
                
            st.info("Hệ thống đã tự động ghép các phần bạn vừa viết. Hãy đọc lại một mạch, chỉnh sửa cho mượt mà (cắt các từ lặp, nối câu...) trước khi nộp cho Giáo sư AI.")
            
            draft_input = st.text_area("Bản Tóm Tắt Hoàn Chỉnh của bạn:", value=current_draft, height=250)
            
            # Đếm từ
            wc = len(draft_input.split()) if draft_input else 0
            wc_color = "#10B981" if 85 <= wc <= 130 else "#EF4444" # Cho phép biên độ an toàn từ 85-130 từ
            st.markdown(f"<div style='text-align:right; color: #64748B;'>Số từ: <b style='color: {wc_color};'>{wc}</b> (Mục tiêu: ~100-120 từ)</div>", unsafe_allow_html=True)
            
            # Buttons điều hướng
            st.markdown("<br>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("⬅️ Quay lại Bước 2 (Lập Dàn Ý)"): 
                st.session_state.app_step = 3
                st.rerun()
                
            if col_b2.button("Nộp bài & Chấm điểm 🎓", type="primary"):
                if wc < 30: 
                    st.error("Bài viết quá ngắn. Bạn chưa hoàn thành các Tab Mở đầu, Thân bài, Kết luận đúng không?")
                else:
                    st.session_state.user_draft = draft_input # Lưu lại bản cuối cùng
                    with st.spinner("👨‍🏫 Giáo sư AI đang phân tích từng câu chữ và chấm điểm bài của bạn..."):
                        grade_prompt = GRADING_PROMPT.replace("{{ORIGINAL}}", st.session_state.original_text).replace("{{STUDENT}}", draft_input)
                        res = generate_content_with_failover(grade_prompt, json_mode=True)
                        if res:
                            try:
                                st.session_state.ai_grading = json.loads(clean_json(res))
                                st.session_state.app_step = 5
                                st.rerun()
                            except Exception as e:
                                st.error("Lỗi phân tích JSON từ AI lúc chấm điểm.")
                                st.write(e)

# ---------------------------------------------------------
# APP STEP 5: BƯỚC 4 - KẾT QUẢ & ĐÁNH BÓNG
# ---------------------------------------------------------
elif st.session_state.app_step == 5:
    res = st.session_state.ai_grading
    st.markdown('<div class="step-header">BƯỚC 4: HOÀN THIỆN - Đánh giá & Rà soát (The Final Polish)</div>', unsafe_allow_html=True)
    
    col_score, col_detail = st.columns([3, 7], gap="medium")
    
    with col_score:
        st.markdown(f"""
        <div style="background: #ECFDF5; border: 2px solid #10B981; border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
            <h3 style="color: #047857; margin-bottom: 0;">TỔNG ĐIỂM</h3>
            <h1 style="color: #059669; font-size: 3.5rem; margin-top: 0;">{res.get('total_score', 'N/A')}</h1>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("✍️ Bản tóm tắt của bạn", expanded=True): 
            st.write(st.session_state.user_draft)
            st.caption(f"Độ dài bài viết: **{res.get('actual_word_count', 'N/A')} words**")
    
    with col_detail:
        tab1, tab2, tab3 = st.tabs(["📊 Bảng điểm (Rubric)", "💡 Đối chiếu & Nâng cấp (B1-B2)", "🔄 Rà soát lỗi"])
        
        with tab1:
            st.markdown(f"""
            <div style="background-color: white; border-left: 4px solid #3B82F6; padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #1E3A8A;">1. Central and Main Ideas (Max: 0.4 pt)</h4>
                <p style="font-size: 1.2rem; font-weight: bold; color: #2563EB;">Điểm đạt: {res.get('score_ideas', '0.0/0.4')}</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Nhận xét:</b> {res.get('feedback_ideas', '')}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background-color: white; border-left: 4px solid #F59E0B; padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #B45309;">2. Own Wording / No Copying (Max: 0.4 pt)</h4>
                <p style="font-size: 1.2rem; font-weight: bold; color: #D97706;">Điểm đạt: {res.get('score_wording', '0.0/0.4')}</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Nhận xét:</b> {res.get('feedback_wording', '')}</p>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(f"""
            <div style="background-color: white; border-left: 4px solid #10B981; padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #065F46;">3. Word Limit (~100 - 120 words) (Max: 0.2 pt)</h4>
                <p style="font-size: 1.2rem; font-weight: bold; color: #059669;">Điểm đạt: {res.get('score_word_limit', '0.0/0.2')}</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Số từ thực tế:</b> {res.get('actual_word_count', '')} words</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Nhận xét:</b> {res.get('feedback_word_limit', '')}</p>
            </div>
            """, unsafe_allow_html=True)

        with tab2:
            st.markdown("##### 1. Bản tóm tắt mẫu từ Giáo Sư")
            st.markdown('<div style="background:#EFF6FF; padding:20px; border-radius:8px; font-family: Merriweather, serif; line-height: 1.8; border: 1px solid #BFDBFE; margin-bottom: 20px;">' + res.get('model_summary', '') + '</div>', unsafe_allow_html=True)
            
            st.markdown("##### 2. Bài học rút ra (Sửa / Thêm / Nâng cấp)")
            comparisons = res.get('detailed_comparison', [])
            if comparisons:
                for item in comparisons:
                    action = item.get('action', 'NÂNG CẤP').upper()
                    
                    color_bg = "#F3F4F6"
                    color_border = "#9CA3AF"
                    icon = "🔧"
                    if "NÂNG CẤP" in action: color_bg = "#E0F2FE"; color_border = "#3B82F6"; icon = "✨"
                    elif "THÊM" in action: color_bg = "#DCFCE7"; color_border = "#10B981"; icon = "➕"
                    elif "SỬA" in action: color_bg = "#FEF3C7"; color_border = "#F59E0B"; icon = "🛠️"

                    st.markdown(f"""
                    <div style="background-color: {color_bg}; border-left: 4px solid {color_border}; padding: 12px; margin-bottom: 12px; border-radius: 4px;">
                        <div style="font-weight: bold; margin-bottom: 5px;">{icon} Lệnh: {action}</div>
                        <div style="display: flex; gap: 10px; margin-bottom: 5px;">
                            <div style="flex: 1; text-decoration: line-through; color: #6B7280;">{item.get('student_text', '')}</div>
                            <div style="flex: 1; font-weight: bold; color: #111827;">➔ {item.get('suggested_text', '')}</div>
                        </div>
                        <div style="font-size: 0.9rem; color: #4B5563;"><i>Lý do: {item.get('explanation', '')}</i></div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Bài của bạn đã rất tốt, gần sát với bài mẫu!")
            
        with tab3:
            st.markdown("""
            ### ✅ Checklist trước khi rời khỏi lớp học:
            - [ ] **Spelling:** Đã rà soát lỗi chính tả từng từ chưa?
            - [ ] **Grammar:** Đã dùng thì Hiện tại đơn (Simple Present) cho các động từ tường thuật (states, explains) chưa?
            - [ ] **Subject-Verb Agreement:** Chủ ngữ số ít đi với động từ thêm 's/es' chưa?
            - [ ] **Read Aloud:** Hãy đọc to thành tiếng bản tóm tắt của bạn. Nếu thấy lủng củng ở đâu, hãy sửa ngay ở đó!
            """)
            
    st.markdown("---")
    if st.button("🔄 Luyện tập Đề mới", type="primary", use_container_width=True): 
        reset_app()
