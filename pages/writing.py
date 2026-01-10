import streamlit as st

# 1. Cấu hình trang
st.set_page_config(page_title="YouPass Clone", layout="wide", page_icon="📝")

# ----------------------------------------------------------------
# CSS - TRANG TRÍ GIAO DIỆN GIỐNG HÌNH
# ----------------------------------------------------------------
st.markdown("""
<style>
    /* 1. Tùy chỉnh Sidebar cho giống menu */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa; /* Màu nền xám nhạt */
        border-right: 1px solid #ddd;
    }
    
    /* 2. Top Bar (Thanh tìm kiếm) */
    .top-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    
    /* 3. Thẻ bài tập (Card) phức tạp hơn */
    .exam-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
        display: flex;
        gap: 15px;
        transition: 0.3s;
        position: relative; /* Để đặt cái nhãn Tag tuyệt đối */
    }
    .exam-card:hover {
        border-color: #2ecc71; /* Viền xanh lá khi di chuột */
        box-shadow: 0 5px 15px rgba(46, 204, 113, 0.2);
    }

    /* Ảnh thumbnail bên trái */
    .exam-thumb {
        width: 120px;
        height: 80px;
        object-fit: cover;
        border-radius: 6px;
        flex-shrink: 0;
    }

    /* Nhãn (Tag) đè lên ảnh hoặc góc thẻ - Màu xanh đậm */
    .exam-tag {
        background-color: #1e272e; /* Màu đen xanh */
        color: white;
        padding: 3px 8px;
        font-size: 10px;
        font-weight: bold;
        border-radius: 4px;
        position: absolute;
        top: 10px;
        left: 10px;
        z-index: 10;
    }
    
    /* Nhãn điểm (Badge) màu đỏ/cam */
    .score-badge {
        background-color: #ff4757;
        color: white;
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 10px;
        margin-left: 10px;
        font-weight: bold;
    }

    /* Nội dung bên phải */
    .exam-content {
        flex-grow: 1;
    }
    .exam-title {
        color: #0984e3; /* Màu xanh dương giống link */
        font-weight: bold;
        font-size: 16px;
        text-decoration: none;
        margin-bottom: 5px;
        display: block;
    }
    .exam-desc {
        font-size: 13px;
        color: #636e72;
        line-height: 1.4;
        display: -webkit-box;
        -webkit-line-clamp: 2; /* Cắt bớt nếu dài quá 2 dòng */
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    
    /* Ẩn cái ghim link */
    [data-testid="stHeaderAction"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------
# SIDEBAR - MENU BÊN TRÁI
# ----------------------------------------------------------------
with st.sidebar:
    st.image("https://raw.githubusercontent.com/linhchutvn/test/main/logo.png", width=120)
    st.markdown("### YouPass Collect")
    
    st.info("💡 Review đề thi thật")

    # Menu dạng Radio button để giả lập việc chọn mục
    st.markdown("---")
    st.markdown("**📖 Reading**")
    reading_mode = st.radio("Chế độ Reading", ["Bài lẻ", "Full đề"], label_visibility="collapsed")
    
    st.markdown("---")
    st.markdown("**🎧 Listening**")
    listening_mode = st.radio("Chế độ Listening", ["Bài lẻ ", "Full đề "], label_visibility="collapsed") # Thêm dấu cách để key khác nhau
    
    st.markdown("---")
    st.markdown("**✏️ Writing**")
    writing_mode = st.radio("Chế độ Writing", ["Task 1", "Task 2", "Task 1 Builder"], label_visibility="collapsed")

# ----------------------------------------------------------------
# MAIN CONTENT - NỘI DUNG CHÍNH
# ----------------------------------------------------------------

# 1. TOP BAR: Tabs và Search
c1, c2 = st.columns([1, 1])
with c1:
    # Giả lập Tabs bằng pills (Streamlit bản mới) hoặc radio ngang
    # Ở đây mình dùng radio ngang cho đơn giản
    tab_view = st.radio("View", ["Bài chưa làm", "Bài đã làm"], horizontal=True, label_visibility="collapsed")

with c2:
    search_txt = st.text_input("Search", placeholder="🔍 Tìm theo tên bài tập", label_visibility="collapsed")

st.markdown(f"#### 🕒 Xem lịch sử làm bài: {writing_mode}") # Tiêu đề thay đổi theo menu

# 2. DỮ LIỆU BÀI TẬP (Mô phỏng hình ảnh bạn gửi)
# Loại hình: Map, Bar Chart, Line Graph, Table...
exercises = [
    {
        "type": "Table",
        "title": "The table below illustrates weekly consumption by age...",
        "date": "10/08/2023",
        "desc": "The table below illustrates weekly consumption by age group of dairy products in a European country...",
        "img": "https://via.placeholder.com/150x100?text=Table",
        "score": "Band 5.5"
    },
    {
        "type": "Line Graph",
        "title": "[24/02/2024] Going to the cinema",
        "date": "24/02/2024",
        "desc": "The graph shows the percentage of people visiting the cinema once a month or more between 1984 to 2003...",
        "img": "https://via.placeholder.com/150x100?text=Line+Graph",
        "score": "Band 7.0"
    },
    {
        "type": "Map",
        "title": "[YouPass Collect] - Coal mining site redevelopment...",
        "date": "Unknown",
        "desc": "The maps below show a coal mining site before and after redevelopment. Summarise the information...",
        "img": "https://via.placeholder.com/150x100?text=Map",
        "score": ""
    },
    {
        "type": "Bar Chart",
        "title": "[YouPass Collect] - Higher education qualifications by...",
        "date": "2001",
        "desc": "The chart below shows the percentage of males and females with higher education qualifications...",
        "img": "https://via.placeholder.com/150x100?text=Bar+Chart",
        "score": ""
    },
     {
        "type": "Pie Chart",
        "title": "[YouPass Collect] - UK migration reasons in 2007",
        "date": "2007",
        "desc": "The pie charts show the main reasons for migration to and from the UK in 2007...",
        "img": "https://via.placeholder.com/150x100?text=Pie+Chart",
        "score": ""
    },
     {
        "type": "Process",
        "title": "[YouPass Collect] - Water-filter Assembly",
        "date": "Unknown",
        "desc": "The diagram below shows how a simple water filter is constructed and how it functions...",
        "img": "https://via.placeholder.com/150x100?text=Process",
        "score": ""
    },
]

# 3. HIỂN THỊ DẠNG LƯỚI (2 Cột)
# Nếu muốn giống hình (2 cột mỗi hàng)
grid = st.columns(2)

for i, ex in enumerate(exercises):
    with grid[i % 2]:
        # Logic hiển thị Badge điểm số nếu có
        score_html = f'<span class="score-badge">{ex["score"]}</span>' if ex["score"] else ""
        
        st.markdown(f"""
        <div class="exam-card">
            <!-- Nhãn loại bài (Tag) -->
            <span class="exam-tag">{ex['type']}</span>
            
            <!-- Ảnh thumbnail -->
            <img src="{ex['img']}" class="exam-thumb">
            
            <!-- Nội dung bên phải -->
            <div class="exam-content">
                <a href="#" class="exam-title">
                    {ex['title']} {score_html}
                </a>
                <div class="exam-desc">{ex['desc']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
