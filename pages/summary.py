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
    
    /* Button Customization */
    div.stButton > button { background-color: #3B82F6; color: white; font-weight: bold; border-radius: 8px; padding: 0.5rem 1.5rem; border: none; }
    div.stButton > button:hover { background-color: #2563EB; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. LOGIC AI & XỬ LÝ DỮ LIỆU
# ==========================================
try:
    ALL_KEYS = st.secrets["GEMINI_API_KEYS"]
except Exception:
    st.error("⚠️ Chưa cấu hình secrets.toml chứa GEMINI_API_KEYS!")
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

            status_msg.info(f"🚀 AI đang xử lý dữ liệu...")
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
# 3. HỆ THỐNG PROMPTS ĐÃ ĐƯỢC CẬP NHẬT
# ==========================================
ANALYSIS_PROMPT = """
Bạn là một chuyên gia dạy kỹ năng tóm tắt (Summary). Người dùng cung cấp văn bản hoặc hình ảnh chứa văn bản. Hãy phân tích và trả về định dạng JSON nghiêm ngặt sau:
{
    "extracted_text": "Trích xuất toàn bộ nội dung chữ tiếng Anh từ hình ảnh. Đảm bảo thay dấu ngoặc kép thành nháy đơn.",
    "topic": "Chủ đề chính của bài viết (1 câu ngắn)",
    "thesis_guide": "Gợi ý nơi tìm Luận điểm chính",
    "thesis_actual": "Luận điểm chính xác trích từ bài",
    "supporting_points": ["Ý chính 1", "Ý chính 2", "Ý chính 3"],
    "details_to_omit_guide": "Hướng dẫn học sinh nhận diện các chi tiết thừa trong bài này",
    "details_to_omit": [
        {
            "phrase": "COPY CHÍNH XÁC Y NGUYÊN 100% CỤM TỪ HOẶC CÂU CẦN CẮT BỎ TỪ BÀI GỐC (Điều này rất quan trọng để hệ thống tìm và gạch bỏ)",
            "reason": "Giải thích ngắn gọn tại sao phải cắt bỏ cụm từ này (Ví dụ: Đây là danh sách liệt kê chi tiết cụ thể / Đây là số liệu thống kê không cần thiết / Đây là giai thoại...)"
        },
        {
            "phrase": "COPY CHÍNH XÁC Y NGUYÊN 100% CỤM TỪ THỨ 2",
            "reason": "Lý do..."
        }
    ]
}
Dữ liệu đầu vào:
"""

GRADING_PROMPT = """
Bạn là một giám khảo chấm thi tiếng Anh khắt khe. Hãy chấm điểm bản tóm tắt của học sinh dựa trên văn bản gốc. 
Hệ thống chấm điểm tổng là 1.0 ĐIỂM, được chia thành 3 tiêu chí cụ thể như sau:

1. Main Ideas (0.4 pt): Tóm tắt có bám sát các ý chính và thông điệp cốt lõi của bài gốc không? Đủ ý trọn 0.4, thiếu ý trừ dần.
2. Own wording (0.4 pt): Học sinh có dùng từ ngữ của riêng mình (paraphrase) không? Nếu copy y nguyên cả câu từ bài gốc -> 0 điểm phần này. Nếu có đổi cấu trúc, đổi từ vựng -> 0.4 điểm.
3. Word limit (0.2 pt): Yêu cầu là "khoảng 100 - 120 từ" (about 100 - 120 words). Độ dài lý tưởng là 100 - 120 từ (đạt 0.2 pt). Nếu quá dài hoặc quá ngắn, trừ còn 0.1 hoặc 0.0.

YÊU CẦU ĐẶC BIỆT VỀ "ĐỐI CHIẾU & NÂNG CẤP":
Sau khi viết bài mẫu (model_summary), bạn BẮT BUỘC phải so sánh bài của học sinh với bài mẫu đó. Hãy nhặt ra 3-4 chỗ trong bài của học sinh cần SỬA, THÊM, hoặc NÂNG CẤP TỪ VỰNG. 
Lưu ý: Chỉ đề xuất từ vựng ở mức độ TRUNG BÌNH KHÁ (B1, B2). Không dùng từ quá học thuật (C1, C2). (Ví dụ: thay vì dùng "using less energy", hãy khuyên dùng "reducing energy consumption" (B2) thay vì "curtailing energy expenditure" (C2)).

Trả về BẮT BUỘC định dạng JSON sau:
{
    "total_score": "Tổng điểm (Ví dụ: 0.8/1.0)",
    "score_ideas": "Điểm ý chính (Ví dụ: 0.3/0.4)",
    "feedback_ideas": "Nhận xét chi tiết về việc chọn lọc ý chính (Chỉ ra ý nào bị thiếu hoặc thừa).",
    "score_wording": "Điểm từ vựng (Ví dụ: 0.3/0.4)",
    "feedback_wording": "Nhận xét chi tiết về kỹ năng paraphrase. Trích dẫn cụ thể câu nào học sinh đang chép nguyên văn (nếu có).",
    "actual_word_count": "Đếm chính xác số từ trong bài của học sinh",
    "score_word_limit": "Điểm độ dài (Ví dụ: 0.2/0.2)",
    "feedback_word_limit": "Nhận xét về độ dài so với yêu cầu 100 - 120 từ.",
    "model_summary": "Viết một bản tóm tắt mẫu hoàn hảo (chính xác khoảng 100 - 120 từ, paraphrase xuất sắc, đủ ý)."
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

def reset_app():
    for key in st.session_state.keys(): del st.session_state[key]
    st.rerun()

# ĐÃ CẬP NHẬT: Hàm Render hiển thị văn bản có khả năng "Gạch bỏ" động
def render_annotated_sidebar(original_text, omit_data=None):
    st.markdown("### 📄 Nguồn bài gốc")
    with st.container(height=650, border=True):
        if st.session_state.original_img:
            st.image(st.session_state.original_img, use_container_width=True)
            st.markdown("---")
        
        display_text = original_text
        
        # Nếu có danh sách từ cần bỏ (Truyền vào ở Bước 2 và 3)
        if omit_data:
            for item in omit_data:
                phrase = item.get('phrase', '').strip()
                # Tìm và thay thế bằng thẻ gạch ngang nền đỏ
                if phrase and phrase in display_text:
                    styled_phrase = f'<del style="color: #EF4444; background-color: #FEE2E2; text-decoration-thickness: 2px;">{phrase}</del>'
                    display_text = display_text.replace(phrase, styled_phrase)

        st.markdown(f'<div style="background:#F8FAFC; padding:15px; border-radius:8px; font-size: 0.95rem; line-height: 1.8;">{display_text}</div>', unsafe_allow_html=True)

# ==========================================
# 5. GIAO DIỆN CÁC BƯỚC
# ==========================================
st.markdown('<div class="main-header">📝 Summary Master Pro</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Luyện tập kỹ năng Viết Tóm tắt theo Quy trình 4 Bước chuẩn Học thuật</div>', unsafe_allow_html=True)

# ---------------------------------------------------------
# APP STEP 1: NHẬP ĐỀ BÀI
# ---------------------------------------------------------
if st.session_state.app_step == 1:
    st.markdown('<div class="step-header">BƯỚC CHUẨN BỊ: Nhập Đề Bài</div>', unsafe_allow_html=True)
    st.info("💡 Bạn có thể **Tải ảnh lên (hỗ trợ kéo thả / Paste Ctrl+V)** HOẶC **Dán đoạn văn bản** vào ô bên dưới.")
    
    col_input1, col_input2 = st.columns(2, gap="large")
    
    with col_input1:
        st.markdown("**Cách 1: Tải ảnh chụp đoạn văn (Hỗ trợ Paste)**")
        uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        img_data = None
        if uploaded_file:
            img_data = Image.open(uploaded_file)
            st.image(img_data, caption="Ảnh đề bài đã tải", use_container_width=True)

    with col_input2:
        st.markdown("**Cách 2: Dán trực tiếp văn bản tiếng Anh**")
        input_text = st.text_area("Text Input", height=200, placeholder="Dán văn bản tiếng Anh vào đây...", label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🚀 Bắt đầu Phân tích", width="stretch", type="primary"):
        if not input_text.strip() and not img_data:
            st.warning("⚠️ Vui lòng tải hình ảnh HOẶC dán văn bản để bắt đầu.")
        else:
            with st.spinner("Đang xử lý dữ liệu và lên kế hoạch hướng dẫn..."):
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
    
    # Bước này hiển thị text bình thường chưa gạch bỏ
    with col1: render_annotated_sidebar(st.session_state.original_text)
    
    with col2:
        st.markdown('<div class="step-header">BƯỚC 1: HIỂU - Đọc và Nắm bắt cốt lõi</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Mục tiêu:</b> Không chỉ đọc chữ, mà phải hiểu cấu trúc. Tìm Topic và Luận điểm chính (Thesis Statement).</div>', unsafe_allow_html=True)
        with st.expander("🤖 Gia sư AI gợi ý Skimming (Đọc lướt):", expanded=True):
            st.markdown(f"**Chủ đề bài viết:** {data.get('topic')}")
            st.markdown(f"**Gợi ý tìm Thesis:** {data.get('thesis_guide')}")
        st.markdown("---")
        st.markdown("**Nhiệm vụ của bạn:** Viết lại Luận điểm chính (Thesis Statement) vào ô dưới đây.")
        thesis_input = st.text_area("Luận điểm chính của bài là gì?", value=st.session_state.user_thesis, height=100)
        if st.button("Tiếp tục: Bước 2 (Chắt lọc) ➡️", type="primary"):
            st.session_state.user_thesis = thesis_input; st.session_state.app_step = 3; st.rerun()

# ---------------------------------------------------------
# APP STEP 3: BƯỚC 2 - CHẮT LỌC (CẬP NHẬT HIỆU ỨNG GẠCH BỎ)
# ---------------------------------------------------------
elif st.session_state.app_step == 3:
    data = st.session_state.ai_analysis
    col1, col2 = st.columns([4, 6], gap="large")
    
    # ĐÃ CẬP NHẬT: Gửi danh sách các từ cần bỏ vào hàm Sidebar để nó tự tìm và Gạch Đỏ
    with col1: render_annotated_sidebar(st.session_state.original_text, data.get('details_to_omit'))
    
    with col2:
        st.markdown('<div class="step-header">BƯỚC 2: CHẮT LỌC - Rút Ý chính & Bỏ Chi tiết phụ</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Quy tắc vàng:</b> Giữ lại "cái gì" (what), không phải "như thế nào" (how). Hãy nhìn sang cột trái, các chi tiết thừa đã được AI dùng "dao mổ" gạch bỏ màu đỏ.</div>', unsafe_allow_html=True)
        
        # ĐÃ CẬP NHẬT: Giao diện bên phải giải thích vì sao đoạn bôi đỏ bị gạch
        with st.expander("🤖 Giải phẫu văn bản (Lý do gạch bỏ):", expanded=True):
            st.markdown(f"**Dấu hiệu nhận diện chung:** {data.get('details_to_omit_guide')}")
            st.markdown("---")
            for idx, item in enumerate(data.get('details_to_omit', [])):
                st.markdown(f"**{idx + 1}. Bỏ cụm:** <del style='color: gray;'>{item.get('phrase')}</del>", unsafe_allow_html=True)
                st.markdown(f"👉 **Lý do:** <span style='color: #D97706;'>{item.get('reason')}</span>", unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)
                
        st.markdown("---")
        st.markdown("**Nhiệm vụ của bạn:** Hệ thống hóa các Ý chính hỗ trợ (Supporting Points) còn lại thành gạch đầu dòng.")
        points_input = st.text_area("Dàn ý tinh gọn:", value=st.session_state.user_points, height=150)
        col_b1, col_b2 = st.columns(2)
        if col_b1.button("⬅️ Quay lại Bước 1"): st.session_state.app_step = 2; st.rerun()
        if col_b2.button("Tiếp tục: Bước 3 (Viết nháp) ➡️", type="primary"):
            st.session_state.user_points = points_input; st.session_state.app_step = 4; st.rerun()

# ---------------------------------------------------------
# APP STEP 4: BƯỚC 3 - VIẾT NHÁP
# ---------------------------------------------------------
elif st.session_state.app_step == 4:
    data = st.session_state.ai_analysis
    col1, col2 = st.columns([4, 6], gap="large")
    with col1:
        st.markdown("### 🗂️ Dàn ý của bạn")
        with st.container(height=650, border=True):
            st.success("**Luận điểm chính:**\n" + st.session_state.user_thesis)
            st.info("**Các ý hỗ trợ:**\n" + st.session_state.user_points)
            with st.expander("📄 Xem lại văn bản gốc (Đã gạch bỏ chi tiết phụ)", expanded=False):
                # Ở bước viết nháp, giữ nguyên giao diện gạch đỏ cho học sinh dễ bỏ qua
                render_annotated_sidebar(st.session_state.original_text, data.get('details_to_omit'))
                
    with col2:
        st.markdown('<div class="step-header">BƯỚC 3: VIẾT - Soạn thảo Bản nháp & Paraphrase</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Mục tiêu:</b> Lắp ráp dàn ý thành 1 đoạn văn. Dùng "Từ nối" và kỹ thuật Paraphrase. Đừng quên yêu cầu khoảng 100 - 120 từ!</div>', unsafe_allow_html=True)
        draft_input = st.text_area("Bản Tóm tắt của bạn:", value=st.session_state.user_draft, height=250)
        wc = len(draft_input.split()) if draft_input else 0
        st.markdown(f"<div style='text-align:right; color: #64748B;'>Số từ: <b>{wc}</b></div>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns(2)
        if col_b1.button("⬅️ Quay lại Bước 2"): st.session_state.app_step = 3; st.rerun()
        if col_b2.button("Hoàn thiện & Gửi chấm điểm 🎓", type="primary"):
            if wc < 20: st.warning("Bài viết quá ngắn. Hãy triển khai thêm ý.")
            else:
                st.session_state.user_draft = draft_input
                with st.spinner("👨‍🏫 Đang chấm điểm..."):
                    grade_prompt = GRADING_PROMPT.replace("{{ORIGINAL}}", st.session_state.original_text).replace("{{STUDENT}}", draft_input)
                    res = generate_content_with_failover(grade_prompt, json_mode=True)
                    if res:
                        try:
                            st.session_state.ai_grading = json.loads(clean_json(res))
                            st.session_state.app_step = 5; st.rerun()
                        except:
                            st.error("Lỗi chấm điểm từ AI.")

# ---------------------------------------------------------
# APP STEP 5: BƯỚC 4 - KẾT QUẢ THEO RUBRIC CHUẨN
# ---------------------------------------------------------
elif st.session_state.app_step == 5:
    res = st.session_state.ai_grading
    st.markdown('<div class="step-header">BƯỚC 4: HOÀN THIỆN - Đánh giá & Rà soát</div>', unsafe_allow_html=True)
    
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
                <h4 style="margin-top: 0; color: #065F46;">3. Word Limit (~100 words) (Max: 0.2 pt)</h4>
                <p style="font-size: 1.2rem; font-weight: bold; color: #059669;">Điểm đạt: {res.get('score_word_limit', '0.0/0.2')}</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Số từ thực tế:</b> {res.get('actual_word_count', '')} words</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Nhận xét:</b> {res.get('feedback_word_limit', '')}</p>
            </div>
            """, unsafe_allow_html=True)

        with tab2:
            st.markdown("##### 1. Bản tóm tắt mẫu (Mức độ B1-B2)")
            st.markdown('<div style="background:#EFF6FF; padding:20px; border-radius:8px; font-family: Merriweather, serif; line-height: 1.8; border: 1px solid #BFDBFE; margin-bottom: 20px;">' + res.get('model_summary', '') + '</div>', unsafe_allow_html=True)
            
            st.markdown("##### 2. Bài học rút ra từ bài mẫu (Sửa / Thêm / Nâng cấp)")
            comparisons = res.get('detailed_comparison', [])
            if comparisons:
                for item in comparisons:
                    action = item.get('action', 'NÂNG CẤP').upper()
                    
                    # Set màu sắc tùy theo hành động
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
            **Tự kiểm tra trước khi nộp bài thực tế:**
            - [ ] Đã kiểm tra lỗi chính tả (Spelling).
            - [ ] Không có chuỗi 4-5 từ nào sao chép y nguyên từ bài gốc.
            - [ ] Đếm lại số từ lần cuối (Nằm trong khoảng 100 - 120 từ).
            - [ ] Đã dùng thì Hiện tại đơn (Simple Present) cho các động từ báo cáo.
            """)
            
    st.markdown("---")
    if st.button("🔄 Làm bài Tóm tắt mới", type="primary", use_container_width=True): 
        reset_app()
