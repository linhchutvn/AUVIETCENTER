import streamlit as st
from PIL import Image

# Cấu hình trang
st.set_page_config(page_title="IELTS Writing Task 1 Practice", layout="wide")

# CSS tùy chỉnh để làm đẹp giao diện giống ảnh mẫu
st.markdown("""
<style>
    .guide-box {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .stTextArea textarea {
        font-size: 16px;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# --- PHẦN 1: LOGIC GIẢ LẬP PHÂN TÍCH ĐỀ ---
def analyze_prompt(question_text):
    """
    Hàm này giả lập việc AI phân tích đề bài dựa trên từ khóa.
    Trong thực tế, bạn có thể kết nối OpenAI API vào đây.
    """
    text = question_text.lower()
    
    if "map" in text or "located" in text:
        task_type = "Map (Bản đồ)"
        tips = {
            "intro": "Paraphrase lại đề bài. Dùng cấu trúc: 'The maps illustrate changes in... between [year] and [year]'.",
            "overview": "Nêu 2 thay đổi chính nổi bật nhất (ví dụ: mở rộng hơn, hiện đại hóa hơn, hoặc mất đi cây xanh...). Không nêu số liệu cụ thể.",
            "body1": "Mô tả chi tiết các thay đổi ở khu vực A (hoặc giai đoạn quá khứ). Sử dụng thì quá khứ đơn và cấu trúc bị động (was built, was demolished).",
            "body2": "Mô tả chi tiết các thay đổi ở khu vực B (hoặc so sánh với hiện tại/tương lai). Sử dụng từ vựng chỉ phương hướng (north, south, adjacent to...)."
        }
    elif "process" in text or "cycle" in text or "diagram" in text or "how" in text:
        task_type = "Process (Quy trình)"
        tips = {
            "intro": "Paraphrase lại đề bài. Dùng cấu trúc: 'The diagram demonstrates the process of...'.",
            "overview": "Nêu tổng quan: Có bao nhiêu bước? Bắt đầu từ đâu và kết thúc ở đâu?",
            "body1": "Mô tả chi tiết nửa đầu của quy trình. Sử dụng Sequencers (First, Subsequently, Then...). Chú ý thì hiện tại đơn và câu bị động.",
            "body2": "Mô tả chi tiết nửa sau của quy trình cho đến khi kết thúc."
        }
    else:
        task_type = "Data Chart (Biểu đồ số liệu - Line/Bar/Pie/Table)"
        tips = {
            "intro": "Paraphrase lại đề bài. Thay đổi từ vựng (Show -> Illustrate, Proportion -> Percentage...).",
            "overview": "Tìm xu hướng chung (tăng/giảm) và hạng mục cao nhất/thấp nhất. Tuyệt đối không đưa số liệu cụ thể vào đây.",
            "body1": "Nhóm các dữ liệu có xu hướng giống nhau hoặc so sánh các hạng mục ở năm đầu tiên/số liệu cao nhất. Đưa dẫn chứng số liệu cụ thể.",
            "body2": "Mô tả các nhóm dữ liệu còn lại hoặc sự thay đổi qua các năm. So sánh sự chênh lệch."
        }
    return task_type, tips

# --- PHẦN 2: GIAO DIỆN NGƯỜI DÙNG ---

st.title("📝 Luyện viết & Hướng dẫn IELTS Writing Task 1")

# Chia cột cho phần nhập liệu
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Nhập đề bài")
    question_input = st.text_area("Dán câu hỏi (Question Prompt) vào đây:", height=150, placeholder="The chart below shows...")

with col2:
    st.subheader("2. Hình ảnh biểu đồ")
    uploaded_image = st.file_uploader("Tải ảnh đề bài lên (PNG, JPG)", type=['png', 'jpg', 'jpeg'])
    if uploaded_image:
        image = Image.open(uploaded_image)
        st.image(image, caption='Đề bài', use_column_width=True)

# Nút Hướng dẫn
if "analysis_done" not in st.session_state:
    st.session_state.analysis_done = False

if st.button("🚀 Hướng dẫn & Thực hành", type="primary"):
    if not question_input:
        st.warning("Vui lòng nhập câu hỏi đề bài trước.")
    else:
        st.session_state.analysis_done = True
        # Gọi hàm phân tích
        task_type, advice = analyze_prompt(question_input)
        st.session_state.task_type = task_type
        st.session_state.advice = advice

# --- PHẦN 3: HIỂN THỊ HƯỚNG DẪN VÀ Ô NHẬP LIỆU ---

if st.session_state.analysis_done:
    st.markdown("---")
    st.success(f"📌 **Loại bài xác định:** {st.session_state.task_type}")
    
    st.markdown("### Thực hành viết bài theo cấu trúc")

    # Helper function để tạo từng phần
    def create_section(title, key_suffix, guide_text):
        st.markdown(f"#### {title}")
        
        # Hiển thị hướng dẫn
        with st.expander(f"💡 Xem hướng dẫn viết phần {title}", expanded=True):
            st.markdown(f"<div class='guide-box'><b>Gợi ý:</b> {guide_text}</div>", unsafe_allow_html=True)
        
        # Ô nhập liệu
        user_text = st.text_area(f"Nhập phần {title} của bạn ở đây:", height=150, key=f"input_{key_suffix}")
        
        # Đếm từ
        word_count = len(user_text.split()) if user_text else 0
        st.caption(f"Word count: {word_count}")
        st.markdown("<br>", unsafe_allow_html=True)
        return user_text

    # 1. Introduction
    intro_text = create_section("Introduction", "intro", st.session_state.advice['intro'])

    # 2. Overview
    overview_text = create_section("Overview", "overview", st.session_state.advice['overview'])

    # 3. Body 1
    body1_text = create_section("Body 1", "body1", st.session_state.advice['body1'])

    # 4. Body 2
    body2_text = create_section("Body 2", "body2", st.session_state.advice['body2'])

    # Tổng kết
    st.markdown("---")
    total_words = len(intro_text.split()) + len(overview_text.split()) + len(body1_text.split()) + len(body2_text.split())
    st.markdown(f"### 📊 Tổng số từ toàn bài: **{total_words}** words")
    
    if total_words < 150:
        st.warning("⚠️ Bài viết chưa đủ 150 từ. Hãy bổ sung thêm chi tiết.")
    else:
        st.success("✅ Độ dài bài viết đạt yêu cầu.")

    # Nút Copy toàn bộ bài (Optional features trick)
    full_essay = f"{intro_text}\n\n{overview_text}\n\n{body1_text}\n\n{body2_text}"
    st.text_area("Bài viết hoàn chỉnh (Copy tại đây):", value=full_essay, height=200)
