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
    model_priority = [
        #"gemini-3.1-pro-preview",        
        #"gemini-2.5-pro",
        "gemini-2.5-flash",        
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-1.5-flash"
    ]
    
    last_error = ""
    # 💡 BỔ SUNG: Khởi tạo vùng thông báo để không bị lỗi NameError
    status_msg = st.empty() 

    for index, current_key in enumerate(keys_to_try):
        try:
            # --- BƯỚC 1: Khởi tạo kết nối & Né chặn IP ---
            if index > 0:
                status_msg.warning(f"⏳ Luồng #{index} bận. Đang tối ưu kết nối, vui lòng đợi 3 giây...")
                time.sleep(3) 
            
            client = genai.Client(api_key=current_key)
            
            # --- BƯỚC 2: Lấy danh sách model ---
            raw_models = list(client.models.list())
            available_models = [m.name.replace("models/", "") for m in raw_models]
            
            # --- BƯỚC 3: Tìm model tốt nhất ---
            sel_model = None
            for target in model_priority:
                if target in available_models:
                    sel_model = target
                    break
            
            if not sel_model:
                sel_model = "gemini-1.5-flash" 

            # --- BƯỚC 4: Hiển thị thông tin Debug ---
            masked_key = f"****{current_key[-4:]}"
            st.toast(f"⚡ Connected: {sel_model}", icon="🤖")
            
            with st.expander(f"🔌 Connection Details (Key #{index + 1})", expanded=False):
                st.write(f"**Active Model:** `{sel_model}`")
                st.write(f"**Active API Key:** `{masked_key}`")
            
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
Bạn là một Giáo sư ngôn ngữ học dạy kỹ năng tóm tắt học thuật (Academic Summary). Hãy phân tích văn bản bài viết THEO TỪNG ĐOẠN và trả về định dạng JSON nghiêm ngặt sau.

⚠️ QUY TRÌNH XÁC ĐỊNH LUẬN ĐIỂM TRỌNG TÂM (THESIS STATEMENT IDENTIFICATION):
Đây là hệ thống phân tích logic áp dụng cho mọi loại văn bản. Bắt buộc thực hiện quá trình suy luận học thuật trong trường "step0_reasoning_scratchpad":
1. Tổng hợp cốt lõi (Core Synthesis): Đọc toàn bộ văn bản. Xác định các thành tố logic: Đặt vấn đề (Problem), Luận cứ chứng minh (Arguments/Body), và Giải pháp/Kết luận (Solution/Conclusion).
2. Đánh giá tính bao quát (Comprehensiveness): Tìm kiếm MỘT câu văn hiển ngôn (Explicit sentence) đóng vai trò là "Tiền đề bao quát" (Overarching Premise) hoặc "Ý tưởng chủ đạo" (Controlling Idea) chi phối toàn bộ các thành tố logic đã xác định ở Bước 1.
3. Tiêu chí loại trừ học thuật (Exclusion Criteria):
   - Loại bỏ "Câu dẫn nhập" (Background Statement / Hook): Các câu chỉ cung cấp bối cảnh, thiếu vắng ý tưởng chủ đạo.
   - Loại bỏ "Câu chủ đề cục bộ" (Topic Sentence / Transitional Statement): Ví dụ câu "Mỗi loại có ưu nhược điểm riêng" chỉ chi phối đoạn Thân bài (Micro-level), nhưng bỏ sót thông điệp định hướng toàn bài (Macro-level).
   - Loại bỏ "Câu kết luận mở rộng" (Call to action): Nếu nó chứa ý tưởng mới chưa từng được lập luận trong thân bài.
4. Quyết định cuối cùng: 
   - Nếu có 1 câu văn đạt chuẩn Tiền đề bao quát: Trích xuất nguyên văn.
   - NẾU KHÔNG CÓ CÂU NÀO ĐẠT CHUẨN 100%: Hệ thống phải tự tổng hợp (Synthesize) một câu "Luận điểm ngụ ý" (Implied Thesis) bằng tiếng Anh, bao trùm toàn vẹn thông điệp của văn bản. Bắt đầu bằng tiền tố "[Implied Thesis] - ".

{
    "step0_reasoning_scratchpad": {
        "1_core_message": "TIẾNG VIỆT: Phân tích các thành tố logic cốt lõi của bài (Vấn đề -> Luận cứ -> Giải pháp).",
        "2_candidate_filtering": "TIẾNG VIỆT: Đánh giá các câu văn tiềm năng. Áp dụng Tiêu chí loại trừ học thuật để bác bỏ các câu chỉ mang tính cục bộ (Topic Sentences).",
        "3_final_decision": "TIẾNG VIỆT: Kết luận rút ra Tiền đề bao quát (Trích xuất hiển ngôn hay Tự tổng hợp ngụ ý?)."
    },
    
    "extracted_text": "Trích xuất toàn bộ nội dung chữ tiếng Anh. Thay dấu ngoặc kép thành nháy đơn.",
    
    "step1_skimming": {
        "topic": "Chủ đề chính của bài",
        "keywords": ["từ khóa 1", "từ khóa 2"]
    },
    
    "thesis_actual": "COPY CHÍNH XÁC CÂU GỐC, HOẶC TỰ VIẾT [Implied Thesis] dựa trên quyết định ở bước 3_final_decision.",
    
    "step1_paragraph_analysis": [
        {
            "para_num": 1,
            "role": "Mở bài / Thân bài / Kết bài",
            "analysis": "TIẾNG VIỆT: Phân tích vai trò tu từ (Rhetorical function) của đoạn văn này.",
            "key_sentence": "COPY 1 CÂU CHỦ ĐỀ CỤC BỘ (Topic Sentence) của đoạn. Không có thì để rỗng.",
            "is_thesis": true/false (Chỉ True nếu thesis_actual là câu hiển ngôn nằm trong đoạn này)
        }
    ],
    
    "step1_reference_result": "1 câu tiếng Việt diễn giải thông điệp cốt lõi của toàn bài để học sinh tham khảo.",
    
    "step2_outline": {
        "raw_points": [
            {"para": 2, "point": "Luận cứ thô trích từ bài (LOẠI BỎ tuyệt đối các dẫn chứng minh họa, số liệu)"}
        ],
        "deep_analysis": "TIẾNG VIỆT: Phân tích cấu trúc logic: Tại sao phải nhóm các luận cứ này lại với nhau?",
        "refined_points": [
            "Point 1: [ENGLISH ONLY] - Paraphrased detail", 
            "Point 2: [ENGLISH ONLY] - Paraphrased detail"
        ]
    },
    
    "details_to_omit_guide": "TIẾNG VIỆT: Hướng dẫn tổng quan về cách nhận diện thông tin thứ cấp (Secondary details) trong bài.",
    "details_to_omit": [
        {
            "para_num": 1,
            "phrase": "COPY CHÍNH XÁC Y NGUYÊN 1 CỤM TỪ THỨ CẤP CẦN LOẠI BỎ",
            "type": "Phân loại học thuật (Ví dụ: Examples, Statistics, Descriptive Details, Quotations, Anecdotes, Repetitions)",
            "deep_reason": "TIẾNG VIỆT: Phân tích sắc bén: Tại sao việc giữ lại cụm từ này làm suy yếu tính cô đọng của một bản tóm tắt học thuật?"
        }
    ],
    
    "step3_drafting_reference": {
        "intro": {
            "original_text": "COPY lại câu Thesis gốc.",
            "transformations": [
                {
                    "method": "TIẾNG VIỆT: Tên phương pháp (VD: Chọn Reporting Verb / Grammar Toolbox - Đổi từ loại / Synonyms)",
                    "original_part": "Cụm từ gốc (hoặc 'Không có')",
                    "new_part": "Cụm từ mới",
                    "explanation": "TIẾNG VIỆT: Tại sao lại biến đổi như vậy? (VD: Đổi 'prioritize' thành danh từ 'prioritization' để cấu trúc câu khách quan hơn)."
                }
            ],
            "final_sentence": "Viết 1 CÂU MỞ ĐẦU mẫu (Khoảng 20-25 từ). LƯU Ý TỐI QUAN TRỌNG: Câu này BẮT BUỘC PHẢI BẮT ĐẦU bằng công thức 'The article/text + [Reporting verb] + that...'. Tuyệt đối không được viết câu khẳng định trực tiếp bỏ qua nguồn tài liệu."
        },
        "body": {
            "original_text": "Các ý tinh gọn từ Dàn ý (Outline).",
            "transformations": [
                {
                    "method": "TIẾNG VIỆT: Nêu rõ Tên kỹ thuật (VD: Grammar Toolbox - Đổi từ loại / Synonyms - Từ đồng nghĩa / Chunking / Transition Words)",
                    "original_part": "LƯU Ý TỐI QUAN TRỌNG: BẮT BUỘC PHẢI LÀ MỘT CỤM TỪ RẤT NGẮN (từ 2 đến 7 chữ). TUYỆT ĐỐI KHÔNG copy nguyên cả câu dài vào đây. (Ví dụ: 'reduce ecological footprint')",
                    "new_part": "Cụm từ mới tương ứng (Ví dụ: 'minimize environmental impact')",
                    "explanation": "TIẾNG VIỆT: Phân tích cực kỳ chi tiết: Tại sao chọn từ này? Đổi cấu trúc ngữ pháp như thế nào? (Ví dụ: 'Thay vì dùng động từ reduce, ta dùng minimize. Cụm ecological footprint đổi thành environmental impact để đa dạng từ vựng')."
                },
                {
                    "method": "...",
                    "original_part": "TẠO RA ĐẦY ĐỦ CÁC BƯỚC BIẾN ĐỔI NHỎ LI TI NHƯ VẬY CHO TOÀN BỘ ĐOẠN THÂN BÀI. THỰC HIỆN THEO TỪNG ĐOẠN THÂN BÀI",
                    "new_part": "...",
                    "explanation": "..."
                }
            ],
            "final_sentence": "ENGLISH ONLY: Viết ĐOẠN THÂN BÀI mẫu. LƯU Ý TỐI QUAN TRỌNG: Không được liệt kê nhồi nhét. BẮT BUỘC phải viết thành 3 đến 4 câu văn phức tạp (complex sentences), sử dụng từ nối (First, Additionally, Finally...) ở đầu mỗi câu để triển khai RÕ RÀNG từng Point đã lập ở Outline."
        },
        "concl": {
            "original_text": "Thông điệp cốt lõi cần chốt lại.",
            "transformations": [
                {
                    "method": "TIẾNG VIỆT: Tên phương pháp (VD: Tell a Friend / Transition Words)",
                    "original_part": "Cụm gốc",
                    "new_part": "Cụm mới",
                    "explanation": "TIẾNG VIỆT: Giải thích cách chốt ý gọn gàng, tránh lặp lại từ vựng của Mở bài."
                }
            ],
            "final_sentence": "Viết 1 CÂU KẾT LUẬN mẫu (Khoảng 15-20 từ)."
        }
    }
}
Dữ liệu đầu vào:
"""
# ================= BỔ SUNG GRADING_PROMPT BỊ THIẾU =================

GRADING_PROMPT = """
Bạn là một giám khảo chấm thi tiếng Anh khắt khe. Hãy chấm điểm bản tóm tắt của học sinh dựa trên văn bản gốc. 
Hệ thống chấm điểm tổng là 1.0 ĐIỂM, được chia thành 3 tiêu chí:

1. Main Ideas (0.4 pt): Tóm tắt có bám sát các ý chính và thông điệp cốt lõi của bài gốc không? Đủ ý trọn 0.4, thiếu ý trừ dần.
2. Own wording (0.4 pt): Học sinh có dùng từ ngữ của riêng mình (paraphrase) không? Nếu copy y nguyên cả câu từ bài gốc -> 0 điểm phần này. Nếu có đổi cấu trúc, đổi từ vựng -> 0.4 điểm.
3. Word limit (0.2 pt): Yêu cầu là "khoảng 100 - 120 từ". HỆ THỐNG ĐÃ ĐẾM CHÍNH XÁC BÀI NÀY CÓ {{WORD_COUNT}} TỪ. Đừng tự đếm lại. Nếu số từ {{WORD_COUNT}} nằm trong biên độ 90 đến 130 từ, hãy cho trọn vẹn 0.2 pt.

⚠️ YÊU CẦU TỐI QUAN TRỌNG VỀ "BẢN HOÀN THIỆN" & "ĐỐI CHIẾU":
- NẾU HỌC SINH ĐẠT 1.0/1.0 ĐIỂM: Hãy giữ NGUYÊN VĂN bài của học sinh làm "model_summary". Trong phần "detailed_comparison", chỉ cần viết 1 mục khen ngợi (action: "KHEN NGỢI"), giải thích tại sao bài viết này xuất sắc.
- NẾU HỌC SINH MẮC LỖI (Thiếu ý/Sai độ dài/Copy): "model_summary" PHẢI LÀ BẢN SỬA LỖI TỪ CHÍNH BÀI CỦA HỌC SINH. Giữ lại những câu học sinh viết tốt. Chỉ sửa/thêm đúng những phần bị thiếu ý hoặc lặp từ.
- Ở phần "detailed_comparison", nhặt ra 2-4 chỗ bạn vừa sửa. NẾU thiếu ý, ghi rõ action là "BỔ SUNG Ý".

Trả về BẮT BUỘC định dạng JSON sau:
{
    "total_score": "0.8/1.0",
    "score_ideas": "0.3/0.4",
    "feedback_ideas": "Nhận xét chi tiết: Bài thiếu ý gì? Hoặc đã đủ ý ra sao?",
    "score_wording": "0.3/0.4",
    "feedback_wording": "Nhận xét về paraphrase...",
    "score_word_limit": "0.2/0.2",
    "feedback_word_limit": "Số lượng từ là {{WORD_COUNT}} từ, nằm trong/ngoài khoảng cho phép...",
    "model_summary": "Giữ nguyên bài HS (nếu 1.0) HOẶC Viết lại bài HS có sửa lỗi/bổ sung ý (nếu < 1.0).",
    "detailed_comparison": [
        {
            "action": "BỔ SUNG Ý / NÂNG CẤP / KHEN NGỢI",
            "student_text": "Đoạn của học sinh (hoặc 'Không có' nếu là Bổ sung ý mới)",
            "suggested_text": "Đoạn đề xuất tốt hơn / Đoạn ý bị thiếu cần thêm vào",
            "explanation": "Lý do sửa / Lý do khen."
        }
    ],
    "grammar_spelling_errors": [
        {
            "error": "Từ/Cụm từ sai chính tả hoặc ngữ pháp",
            "correction": "Cách sửa đúng",
            "reason": "Giải thích lỗi ngữ pháp"
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
st.markdown('<div class="sub-header">Luyện tập kỹ năng Viết Tóm tắt theo Quy trình 4 Bước chuẩn Học thuật </div>', unsafe_allow_html=True)

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
# APP STEP 2: BƯỚC 1 - HIỂU (PHÂN TÍCH CHI TIẾT)
# ---------------------------------------------------------
elif st.session_state.app_step == 2:
    data = st.session_state.ai_analysis
    col1, col2 = st.columns([4, 6], gap="large")
    
    with col1: 
        render_annotated_sidebar(st.session_state.original_text)
    
    with col2:
        st.markdown('<div class="step-header">BƯỚC 1: HIỂU - Đọc và Nắm bắt Toàn diện</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Lời khuyên từ Giáo sư:</b> Nền tảng của một bài tóm tắt thành công không nằm ở kỹ năng viết, mà ở khả năng <b>đọc hiểu sâu sắc</b>. Hãy cùng thầy đi qua 3 giai đoạn phân tích văn bản này.</div>', unsafe_allow_html=True)
        
        # --- GIAI ĐOẠN 1 ---
        st.markdown("#### 🧭 Giai đoạn 1: Đọc Định Hướng (Skimming)")
        with st.container(border=True):
            skim_data = data.get('step1_skimming', {})
            st.markdown(f"**🎯 Chủ đề (Topic):** {skim_data.get('topic', '')}")
            st.markdown(f"**🔑 Từ khóa lặp lại (Keywords):** {', '.join(skim_data.get('keywords', []))}")
            st.caption('👉 *Mục tiêu: Nắm bắt nhanh "nhân vật chính" của bài viết mà chưa cần sa đà vào chi tiết.*')

        # --- GIAI ĐOẠN 2 ---
        st.markdown("#### 🔍 Giai đoạn 2: Đọc Sâu và Phân Tích Từng Đoạn (Close Reading)")
        st.info("Cầm bút highlight lên! Cùng soi kính lúp xem mỗi đoạn tác giả cất giấu 'vàng' ở đâu.")
        
        para_analysis = data.get('step1_paragraph_analysis', [])
        for para in para_analysis:
            # Nhận diện xem câu này là Ý chính (Point) hay Luận điểm (Thesis)
            is_thesis = para.get('is_thesis', False)
            badge_color = "#EF4444" if is_thesis else "#3B82F6"
            badge_text = "⭐ LUẬN ĐIỂM CHÍNH (THESIS)" if is_thesis else "Ý CHÍNH HỖ TRỢ (POINT)"
            
            with st.expander(f"Đoạn {para.get('para_num', '?')}: {para.get('role', '')}", expanded=True):
                st.markdown(f"**Giáo sư phân tích:** {para.get('analysis', '')}")
                
                key_sentence = para.get('key_sentence', '').strip()
                if key_sentence:
                    st.markdown(f"""
                    <div style="background-color: #F8FAFC; border-left: 4px solid {badge_color}; padding: 10px; margin-top: 10px;">
                        <span style="font-size: 0.8rem; font-weight: bold; color: {badge_color};">{badge_text}</span><br>
                        <mark style="background-color: #FEF08A; padding: 2px 4px; border-radius: 3px; font-weight: 500;">"{key_sentence}"</mark>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("*Đoạn này chỉ chứa chi tiết phụ, không có câu ý chính.*")

        # --- GIAI ĐOẠN 3 ---
        st.markdown("#### 🧠 Giai đoạn 3: Tổng hợp (Tự kiểm tra)")
        st.markdown('Đã đến lúc "gấp tài liệu lại". Bằng trí nhớ và sự hiểu biết từ Giai đoạn 2, em hãy tự đúc kết lại thông điệp cốt lõi nhất của toàn bộ bài viết.')
        
        with st.container(border=True):
            st.markdown("**Nhiệm vụ của em:** Tự viết lại **Luận điểm chính (Thesis Statement)** vào ô dưới đây (Có thể chép lại câu gốc Tiếng Anh hoặc diễn đạt bằng lời của em). Câu này sẽ là 'kim chỉ nam' cho toàn bộ bài tóm tắt ở Bước 3.")
            
            # 1. Để ô nhập liệu lên trên cùng
            thesis_input = st.text_area("Luận điểm cốt lõi của bài là gì?", value=st.session_state.user_thesis, height=100, label_visibility="collapsed")
            
            # 2. Giấu đáp án vào trong Expander để học sinh đối chiếu SAU KHI làm
            with st.expander("👀 Đã viết xong? Bấm vào đây để đối chiếu với Đáp án của Giáo sư"):
                st.markdown("**1. Câu Luận điểm (Thesis Statement) gốc trích từ bài:**")
                st.info(f"*{data.get('thesis_actual', 'Bài viết không có câu Thesis lộ diện rõ ràng, cần tự tổng hợp.')}*")
                
                st.markdown("**2. Giáo sư diễn giải ý nghĩa cốt lõi:**")
                st.success(f"*{data.get('step1_reference_result', '')}*")
        
        # --- NÚT ĐIỀU HƯỚNG ---
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Tiếp tục: Bước 2 (Chắt Lọc & Loại bỏ) ➡️", type="primary"):
            if not thesis_input.strip():
                st.warning("⚠️ Em hãy thử tự viết ra luận điểm (dù chỉ là vài từ khóa) trước khi sang bước sau nhé!")
            else:
                st.session_state.user_thesis = thesis_input
                st.session_state.app_step = 3
                st.rerun()

# ---------------------------------------------------------
# APP STEP 3: BƯỚC 2 - CHẮT LỌC (HỆ THỐNG HÓA & CẮT BỎ)
# ---------------------------------------------------------
elif st.session_state.app_step == 3:
    data = st.session_state.ai_analysis
    col1, col2 = st.columns([4, 6], gap="large")
    
    with col1: 
        # Hiển thị bài gốc với các nét gạch đỏ
        render_annotated_sidebar(st.session_state.original_text, data.get('details_to_omit'))
    
    with col2:
        st.markdown('<div class="step-header">BƯỚC 2: CHẮT LỌC - Rút Ý Chính & Loại Bỏ Chi Tiết Phụ</div>', unsafe_allow_html=True)
        st.markdown('<div class="theory-box"><b>Nhiệm vụ:</b> Biến các ý tưởng rời rạc thành một Dàn ý (Outline) vững chắc, đồng thời dùng "dao mổ" để dọn dẹp các chi tiết thừa thãi.</div>', unsafe_allow_html=True)
        
        tab_outline, tab_cut = st.tabs(["📑 2.1: Hệ Thống Hóa Dàn Ý", "✂️ 2.2: Lớp Học Giải Phẫu (Cắt Bỏ)"])
        
        # --- TAB 1: LẬP DÀN Ý ---
        with tab_outline:
            st.markdown("#### 🧱 Từ Danh sách thô đến Dàn ý tinh gọn")
            outline_data = data.get('step2_outline', {})
            
            with st.container(border=True):
                st.markdown("**1. Danh sách thô (Các ý nhặt được từ Bước 1):**")
                for pt in outline_data.get('raw_points', []):
                    st.markdown(f"- {pt}")
                
                st.markdown("---")
                st.markdown("**2. Lời khuyên Xử lý & Gộp ý (Grouping) từ Giáo sư:**")
                st.info(f"💡 {outline_data.get('grouping_advice', 'Hãy gộp các ý có chung chủ đề lại với nhau để dàn ý gọn gàng hơn.')}")
            
            st.markdown("**3. Nhiệm vụ của em:** Dựa vào những gợi ý trên, hãy tự viết lại một **Dàn ý tinh gọn** (khoảng 3-5 gạch đầu dòng) vào ô dưới đây để chuẩn bị viết nháp.")
            
            # Ô nhập liệu của học sinh (Đẩy lên trên đáp án)
            points_input = st.text_area("Dàn ý (Outline) của em:", value=st.session_state.user_points, height=180, label_visibility="collapsed")
            
            # GIẤU ĐÁP ÁN VÀO TRONG EXPANDER
            with st.expander("👀 Đã lập dàn ý xong? Bấm vào đây để tham khảo Dàn ý tinh gọn của Giáo sư"):
                st.markdown("**Dàn ý tinh gọn (Refined Outline):**")
                refined_pts = outline_data.get('refined_points', [])
                if refined_pts:
                    for idx, pt in enumerate(refined_pts):
                        st.success(f"**Point {idx + 1}:** {pt}")
                else:
                    st.warning("Hệ thống chưa tạo được dàn ý tinh gọn. Em hãy tự làm nhé!")
            
        # --- TAB 2: GIẢI PHẪU CẮT BỎ ---
        with tab_cut:
            st.markdown("#### 🔪 The Surgeon's Cut (Loại bỏ chi tiết phụ)")
            st.markdown(f"*{data.get('details_to_omit_guide', '')}*")
            st.markdown("Hãy nhìn sang văn bản gốc ở cột trái (các phần bị gạch đỏ). Dưới đây là giải thích chi tiết cho từng đoạn:")
            
            omissions = data.get('details_to_omit', [])
            # Lấy danh sách các số thứ tự đoạn văn (loại bỏ trùng lặp và sắp xếp tăng dần)
            paras = sorted(list(set([item.get('para_num', 1) for item in omissions])))
            
            for p_num in paras:
                with st.expander(f"Đoạn {p_num}: Cần cắt bỏ những gì?", expanded=True):
                    para_omissions = [item for item in omissions if item.get('para_num') == p_num]
                    for idx, item in enumerate(para_omissions):
                        st.markdown(f"**{idx + 1}. Bỏ:** <del style='color: #EF4444; background-color: #FEE2E2;'>{item.get('phrase')}</del>", unsafe_allow_html=True)
                        st.markdown(f"🏷️ **Dấu hiệu:** `{item.get('type', 'Detail')}`")
                        st.markdown(f"👉 **Tại sao cắt?** <span style='color: #D97706;'>{item.get('reason')}</span>", unsafe_allow_html=True)
                        if idx < len(para_omissions) - 1:
                            st.markdown("<hr style='margin: 10px 0; border-top: 1px dashed #E2E8F0;'>", unsafe_allow_html=True)
        
        # --- NÚT ĐIỀU HƯỚNG ---
        st.markdown("<br>", unsafe_allow_html=True)
        col_b1, col_b2 = st.columns(2)
        if col_b1.button("⬅️ Quay lại Bước 1"): st.session_state.app_step = 2; st.rerun()
        if col_b2.button("Tiếp tục: Bước 3 (Soạn Thảo) ➡️", type="primary"):
            if not points_input.strip():
                st.warning("⚠️ Em chưa lập Dàn ý! Hãy quay lại Tab '2.1 Hệ Thống Hóa Dàn Ý' để viết nhé.")
            else:
                st.session_state.user_points = points_input
                st.session_state.app_step = 4
                st.rerun()

# ---------------------------------------------------------
# APP STEP 4: BƯỚC 3 - VIẾT NHÁP (HUẤN LUYỆN PARAPHRASE & LẮP RÁP)
# ---------------------------------------------------------
elif st.session_state.app_step == 4:
    data = st.session_state.ai_analysis
    
    # -- Cột Trái: Giữ nguyên Dàn ý & Nguồn để học sinh đối chiếu --
    col1, col2 = st.columns([4, 6], gap="large")
    with col1:
        st.markdown("### 🗂️ Nguyên liệu của bạn")
        with st.container(height=650, border=True):
            st.success("**Luận điểm chính (Thesis):**\n\n" + st.session_state.user_thesis)
            st.info("**Các ý hỗ trợ (Points):**\n\n" + st.session_state.user_points)
            with st.expander("📄 Xem lại văn bản gốc", expanded=False):
                render_annotated_sidebar(st.session_state.original_text, data.get('details_to_omit'))
                
    # -- Cột Phải: Dây chuyền Viết từng bước --
    with col2:
        st.markdown('<div class="step-header">BƯỚC 3: VIẾT - Huấn Luyện Kỹ Năng Paraphrase</div>', unsafe_allow_html=True)
        
        # HỘP CÔNG CỤ PARAPHRASE TỪ GIÁO TRÌNH (TRANG 15-18)
        with st.expander("🛠️ BÍ QUYẾT PARAPHRASE TỪ GIÁO SƯ (Bấm để xem) 🛠️", expanded=False):
            st.markdown("""
            Tuyệt đối không sao chép quá 4 từ liên tiếp từ bản gốc. Hãy dùng 3 vũ khí sau:
            
            **1. Kể cho bạn nghe (Tell a Friend):** Dùng cho ý ngắn.
            - *Cách làm:* Đọc hiểu ý ➔ Nhắm mắt/Che bài lại ➔ Tưởng tượng giải thích cho bạn bè nghe bằng từ ngữ đơn giản ➔ Viết ra.
            
            **2. Phân đoạn (Chunking Method):** Dùng cho câu dài, phức tạp.
            - *Cách làm:* Cắt câu gốc thành 2-3 khúc nhỏ ➔ Tìm từ đồng nghĩa cho từng khúc ➔ Ghép lại (Có thể đảo trật tự các khúc).
            
            **3. Hộp công cụ Ngữ pháp (Grammar Toolbox):**
            - Đổi Từ loại: Danh từ ➔ Động từ (VD: *The development of...* ➔ *To develop...*)
            - Đổi Thể: Chủ động ↔ Bị động.
            """)
            
        tab_intro, tab_body, tab_concl, tab_final = st.tabs(["1. Câu Mở Đầu", "2. Thân Bài", "3. Câu Kết", "4. 🧩 Lắp Ráp & Nộp Bài"])
        
        draft_refs = data.get('step3_drafting_reference', {})
        
        # Hàm hỗ trợ in ra các bước biến đổi chi tiết
        def render_transformations(section_data):
            st.markdown(f"**📝 Văn bản gốc:** *{section_data.get('original_text', '')}*")
            st.markdown("**🛠️ Phân tích từng bước Paraphrase:**")
            for t in section_data.get('transformations', []):
                st.markdown(f"""
                - 🎯 **{t.get('method', '')}**: 
                  <span style='color: #EF4444; text-decoration: line-through;'>{t.get('original_part', '')}</span> ➔ **<span style='color: #10B981;'>{t.get('new_part', '')}</span>**
                  <br><i style='color: #64748B; font-size: 0.9em;'>👉 Giải thích: {t.get('explanation', '')}</i>
                """, unsafe_allow_html=True)

        # --- TAB 1: CÂU MỞ ĐẦU ---
        with tab_intro:
            st.markdown("#### 🚪 Viết Câu Mở Đầu (Opening Sentence)")
            st.markdown("""
            👉 **Nhịp 1 (Xác định):** Nhìn vào ô màu Xanh lá cây (Thesis/Main Idea) bên cột trái.
            
            👉 **Nhịp 2 (Công thức):** Ráp vào ma trận chuẩn học thuật sau:
            | Nguồn tài liệu | Động từ báo cáo (Reporting Verbs) | Thông điệp cốt lõi |
            | :--- | :--- | :--- |
            | The article / text | **[Thông tin]** discusses, elaborates on...<br>**[Tranh luận]** argues, claims, asserts... | + **[Thesis đã paraphrase]** |
            """, unsafe_allow_html=True)
            
            st.session_state.user_draft_intro = st.text_area("👉 Nhịp 3: Viết Câu mở đầu hoàn chỉnh của em:", 
                                                             value=st.session_state.user_draft_intro, height=120, key="intro_box")
            
            with st.expander("👀 Bí quá? Vào Lớp học Thực chiến của Giáo sư"):
                intro_data = draft_refs.get('intro', {})
                render_transformations(intro_data)
                st.info(f"💡 **Câu hoàn chỉnh:** {intro_data.get('final_sentence', '')}")
            
        # --- TAB 2: THÂN BÀI ---
        with tab_body:
            st.markdown("#### 🧱 Viết Thân Bài (Body Paragraph)")
            st.markdown("""
            👉 **Nhịp 1 (Xác định):** Nhìn vào ô màu Xanh dương (Các ý hỗ trợ) bên cột trái.
            
            👉 **Nhịp 2 (Kỹ thuật Chunking & Transition):** 
            - Cắt nhỏ từng ý ra, thay từ đồng nghĩa (Synonyms) hoặc đổi Từ loại (Danh từ ↔ Động từ).
            - Dùng **Từ nối**: <span class='transition-word'>First, Additionally, Furthermore, However, Consequently...</span> để khâu chúng lại.
            """, unsafe_allow_html=True)
            
            st.session_state.user_draft_body = st.text_area("👉 Nhịp 3: Viết đoạn Thân bài hoàn chỉnh của em:", 
                                                            value=st.session_state.user_draft_body, height=200, key="body_box")
            
            with st.expander("👀 Bí quá? Vào Lớp học Thực chiến của Giáo sư"):
                body_data = draft_refs.get('body', {})
                render_transformations(body_data)
                st.info(f"💡 **Đoạn hoàn chỉnh:** {body_data.get('final_sentence', '')}")
            
        # --- TAB 3: CÂU KẾT LUẬN ---
        with tab_concl:
            st.markdown("#### 🏁 Viết Câu Kết Luận (Concluding Sentence)")
            st.markdown("""
            👉 **Nhịp 1 (Xác định):** Tìm thông điệp cốt lõi hoặc mục đích cuối cùng của tác giả.
            
            👉 **Nhịp 2 (Kỹ thuật Tell a friend):** Dùng văn phong mộc mạc của em để tóm gọn lại thông điệp cuối mà không lặp từ với Câu Mở Đầu.
            - *Từ nối:* <span class='transition-word'>Ultimately, In conclusion, To sum up,...</span>
            """, unsafe_allow_html=True)
            
            st.session_state.user_draft_concl = st.text_area("👉 Nhịp 3: Viết Câu kết luận hoàn chỉnh của em:", 
                                                             value=st.session_state.user_draft_concl, height=100, key="concl_box")

            with st.expander("👀 Bí quá? Vào Lớp học Thực chiến của Giáo sư"):
                concl_data = draft_refs.get('concl', {})
                render_transformations(concl_data)
                st.info(f"💡 **Câu hoàn chỉnh:** {concl_data.get('final_sentence', '')}")

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
                
            st.info("Hệ thống đã tự động ghép 3 phần em vừa viết. Hãy đọc lại một mạch, cắt bỏ các từ lặp lại, sửa dấu câu cho mượt mà trước khi nộp cho Giáo sư AI.")
            
            draft_input = st.text_area("Bản Tóm Tắt Hoàn Chỉnh của bạn:", value=current_draft, height=250)
            
            # Đếm từ
            wc = len(draft_input.split()) if draft_input else 0
            wc_color = "#10B981" if 85 <= wc <= 130 else "#EF4444" 
            st.markdown(f"<div style='text-align:right; color: #64748B;'>Số từ: <b style='color: {wc_color};'>{wc}</b> (Mục tiêu: ~100-120 từ)</div>", unsafe_allow_html=True)
            
            # Buttons điều hướng
            st.markdown("<br>", unsafe_allow_html=True)
            col_b1, col_b2 = st.columns(2)
            if col_b1.button("⬅️ Quay lại Bước 2 (Chắt lọc)"): 
                st.session_state.app_step = 3
                st.rerun()
                
            if col_b2.button("Nộp bài & Chấm điểm 🎓", type="primary"):
                if wc < 30: 
                    st.error("Bài viết quá ngắn. Em chưa hoàn thành các Tab Mở đầu, Thân bài, Kết luận đúng không?")
                else:
                    st.session_state.user_draft = draft_input # Lưu lại bản cuối cùng
                    st.session_state.final_word_count = wc # Lưu số từ chính xác
                    
                    with st.spinner("👨‍🏫 Giáo sư AI đang phân tích từng câu chữ và chấm điểm bài của em..."):
                        grade_prompt = GRADING_PROMPT.replace("{{ORIGINAL}}", st.session_state.original_text).replace("{{STUDENT}}", draft_input).replace("{{WORD_COUNT}}", str(wc))
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
# APP STEP 5: BƯỚC 4 - KẾT QUẢ
# ---------------------------------------------------------
elif st.session_state.app_step == 5:
    res = st.session_state.ai_grading
    
    # Ép Python đếm lại số từ ở màn hình này để đồng nhất 100% với màn hình trước
    final_wc = len(st.session_state.user_draft.split()) if st.session_state.user_draft else 0
    
    st.markdown('<div class="step-header">BƯỚC 4: HOÀN THIỆN - Đánh giá & Rà soát (The Final Polish)</div>', unsafe_allow_html=True)
    
    col_score, col_detail = st.columns([3, 7], gap="medium")
    
    with col_detail:
        tab1, tab2, tab3 = st.tabs(["📊 Bảng điểm (Rubric)", "💡 Phiên bản Hoàn thiện", "🔄 Rà soát Ngữ pháp & Chính tả"])
        
        with tab1:
            st.markdown(f"""
            <div style="background-color: white; border-left: 4px solid #3B82F6; padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #1E3A8A;">1. Central and Main Ideas (Max: 0.4 pt)</h4>
                <p style="font-size: 1.2rem; font-weight: bold; color: #2563EB;">Điểm đạt: {res.get('score_ideas', '0.0/0.4')}</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Nhận xét:</b> {res.get('feedback_ideas', '')}</p>
            </div>
            
            <div style="background-color: white; border-left: 4px solid #F59E0B; padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #B45309;">2. Own Wording / No Copying (Max: 0.4 pt)</h4>
                <p style="font-size: 1.2rem; font-weight: bold; color: #D97706;">Điểm đạt: {res.get('score_wording', '0.0/0.4')}</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Nhận xét:</b> {res.get('feedback_wording', '')}</p>
            </div>
            
            <div style="background-color: white; border-left: 4px solid #10B981; padding: 15px; margin-bottom: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                <h4 style="margin-top: 0; color: #065F46;">3. Word Limit (~100 - 120 words) (Max: 0.2 pt)</h4>
                <p style="font-size: 1.2rem; font-weight: bold; color: #059669;">Điểm đạt: {res.get('score_word_limit', '0.0/0.2')}</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Số từ thực tế:</b> {final_wc} words</p>
                <p style="margin-bottom: 0; color: #334155;"><b>Nhận xét:</b> {res.get('feedback_word_limit', '')}</p>
            </div>
            """, unsafe_allow_html=True)

        with tab2:
            is_perfect = "1.0/1.0" in res.get('total_score', '')
            
            if is_perfect:
                st.markdown("##### 🏆 Chúc mừng! Bài viết của em đã đạt mức hoàn hảo!")
                st.info("Giáo sư không cần phải sửa đổi bất kỳ cấu trúc nào trong bài viết của em. Dưới đây là bài viết gốc của em:")
            else:
                st.markdown("##### 1. Phiên bản Hoàn thiện (Giáo sư sửa từ bài của em)")
                st.caption("*Giáo sư đã giữ nguyên văn phong của em, chỉ bổ sung các ý bị thiếu hoặc nâng cấp các cụm từ copy.*")
            
            st.markdown('<div style="background:#EFF6FF; padding:20px; border-radius:8px; font-family: Merriweather, serif; line-height: 1.8; border: 1px solid #BFDBFE; margin-bottom: 20px;">' + res.get('model_summary', '') + '</div>', unsafe_allow_html=True)
            
            st.markdown("##### 2. Bài học rút ra từ Giáo sư")
            comparisons = res.get('detailed_comparison', [])
            if comparisons:
                for item in comparisons:
                    action = item.get('action', 'NÂNG CẤP').upper()
                    
                    color_bg = "#F3F4F6"
                    color_border = "#9CA3AF"
                    icon = "🔧"
                    if "NÂNG CẤP" in action or "SỬA" in action: color_bg = "#FEF3C7"; color_border = "#F59E0B"; icon = "🛠️"
                    elif "BỔ SUNG Ý" in action or "THÊM" in action: color_bg = "#E0F2FE"; color_border = "#3B82F6"; icon = "➕"
                    elif "KHEN NGỢI" in action: color_bg = "#DCFCE7"; color_border = "#10B981"; icon = "⭐"

                    st.markdown(f"""
                    <div style="background-color: {color_bg}; border-left: 4px solid {color_border}; padding: 12px; margin-bottom: 12px; border-radius: 4px;">
                        <div style="font-weight: bold; margin-bottom: 5px;">{icon} Lệnh: {action}</div>
                        <div style="display: flex; gap: 10px; margin-bottom: 5px;">
                            <div style="flex: 1; text-decoration: line-through; color: #6B7280;">{item.get('student_text', '')}</div>
                            <div style="flex: 1; font-weight: bold; color: #111827;">➔ {item.get('suggested_text', '')}</div>
                        </div>
                        <div style="font-size: 0.9rem; color: #4B5563;"><i>Phân tích: {item.get('explanation', '')}</i></div>
                    </div>
                    """, unsafe_allow_html=True)
            
        with tab3:
            st.markdown("#### 🕵️ Kính lúp Soi lỗi Ngữ pháp & Chính tả")
            errors = res.get('grammar_spelling_errors', [])
            
            if not errors or len(errors) == 0:
                st.success("🎉 Tuyệt vời! Giáo sư không tìm thấy bất kỳ lỗi chính tả hay ngữ pháp cơ bản nào trong bài của em.")
            else:
                st.warning(f"⚠️ Phát hiện {len(errors)} lỗi cần khắc phục trong bản nháp của em:")
                for e in errors:
                    st.markdown(f"""
                    - ❌ Sai: **<span style='color: #EF4444;'>{e.get('error', '')}</span>**
                    - ✅ Sửa thành: **<span style='color: #10B981;'>{e.get('correction', '')}</span>**
                    - 💡 Lý do: *{e.get('reason', '')}*
                    """, unsafe_allow_html=True)
                    st.markdown("---")
            
            st.info("💡 **Mẹo:** Trong các kỳ thi thực tế, sai ngữ pháp (đặc biệt là chia động từ và số nhiều) sẽ làm em bị trừ điểm rất nặng. Hãy luôn rà soát kỹ trước khi nộp bài nhé!")
            
    st.markdown("---")
    if st.button("🔄 Luyện tập Đề mới", type="primary", use_container_width=True): 
        reset_app()
