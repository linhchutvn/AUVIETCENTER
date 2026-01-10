import streamlit as st

# 1. Cấu hình trang
st.set_page_config(page_title="AUVIET CENTER", layout="wide", page_icon="🎓")

# ----------------------------------------------------------------
# CSS: GIAO DIỆN CHUYÊN NGHIỆP & ẨN SIDEBAR
# ----------------------------------------------------------------
st.markdown("""
<style>
    /* Ẩn Sidebar mặc định */
    [data-testid="stSidebar"] {display: none;}
    
    /* Đẩy nội dung lên sát mép trên (Xóa khoảng trắng mặc định của Streamlit) */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    /* Style cho Nút Đăng nhập Google đẹp hơn */
    .login-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: white;
        color: #3c4043;
        border: 1px solid #dadce0;
        border-radius: 20px; /* Bo tròn hình viên thuốc */
        padding: 5px 15px;
        text-decoration: none;
        font-weight: 500;
        font-size: 14px;
        transition: 0.3s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .login-btn:hover {
        background-color: #f7fafe;
        border-color: #d2e3fc;
        box-shadow: 0 2px 6px rgba(0,0,0,0.15);
        color: #3c4043;
    }
    
    /* CSS cho thẻ Card sản phẩm (Giữ nguyên) */
    .product-card {
        background-color: white; border: 1px solid #e0e0e0; border-radius: 10px;
        padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); margin-bottom: 20px;
        height: 100%; display: flex; flex-direction: column; justify-content: space-between;
    }
    .card-img { width: 100%; border-radius: 5px; object-fit: cover; height: 180px; margin-bottom: 10px; }
    .course-title { font-size: 18px; font-weight: bold; color: #2c3e50; min-height: 50px; }
    .course-price { color: #d63031; font-weight: bold; font-size: 16px; margin-bottom: 15px; }
    
    /* Ẩn ghim tiêu đề */
    [data-testid="stHeaderAction"] { display: none !important; }
    h1 a, h2 a, h3 a, h4 a, h5 a, h6 a { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------
# HEADER (NAVBAR) - GIAO DIỆN MỚI
# ----------------------------------------------------------------
# Chia làm 3 phần: [Logo (2)] --- [Menu (6)] --- [Login (2)]
col_brand, col_nav, col_login = st.columns([2, 5, 2], gap="small", vertical_alignment="center")

with col_brand:
    # Logo hoặc Tên thương hiệu
    st.markdown("<h3 style='margin:0; color:#0984e3;'>🎓 AU VIET</h3>", unsafe_allow_html=True)

with col_nav:
    # Menu nằm giữa
    nav1, nav2 = st.columns(2)
    with nav1:
        st.page_link("app.py", label="Trang chủ", icon="🏠", use_container_width=True, disabled=True)
    with nav2:
        st.page_link("pages/writing.py", label="Luyện tập 4 kỹ năng", icon="📝", use_container_width=True)

with col_login:
    # Nút đăng nhập nằm bên phải
    # Dùng HTML để căn phải (float: right)
    st.markdown("""
        <div style="text-align: right;">
            <a href="https://accounts.google.com" target="_blank" class="login-btn">
                <img src="https://www.svgrepo.com/show/475656/google-color.svg" width="18" height="18" style="margin-right:8px;">
                Đăng nhập
            </a>
        </div>
    """, unsafe_allow_html=True)

st.divider() # Đường kẻ ngang phân cách Header

# ----------------------------------------------------------------
# NỘI DUNG CHÍNH (BODY)
# ----------------------------------------------------------------

# BANNER
try:
    st.image("banner.JPG", use_column_width=True)
except:
    st.image("https://via.placeholder.com/1200x300?text=AU+VIET+CENTER", use_column_width=True)

st.write("") 

# THANH TÌM KIẾM
st.markdown("##### 🔍 Tìm kiếm & Lọc") 
search_col, filter_col = st.columns([3, 1])

# Dữ liệu khóa học
courses = [
    {"id": 1, "title": "Khoá học IELTS Speaking", "price": "FREE", "img": "https://raw.githubusercontent.com/linhchutvn/test/main/SPEAKING.png", "category": "Speaking", "link": "https://www.youtube.com/playlist?list=PLI3S3xWA78UXXz0m6QoGyc-8UvHeAYTYT"},
    {"id": 2, "title": "Khoá học IELTS Reading", "price": "FREE", "img": "https://raw.githubusercontent.com/linhchutvn/test/main/READING.png", "category": "Reading", "link": "https://www.google.com"},
    {"id": 3, "title": "Khoá học IELTS Listening", "price": "FREE", "img": "https://raw.githubusercontent.com/linhchutvn/test/main/LISTENING.png", "category": "Listening", "link": "https://www.google.com"},
    {"id": 4, "title": "Khoá học IELTS Writing Task 1", "price": "FREE", "img": "https://raw.githubusercontent.com/linhchutvn/test/main/TASK%201.png", "category": "Writing Task 1", "link": "https://www.youtube.com/playlist?list=PLI3S3xWA78UWtIxIEnZia2siEgxJPwpfQ"},
    {"id": 5, "title": "Khoá học IELTS Writing Task 2", "price": "FREE", "img": "https://raw.githubusercontent.com/linhchutvn/test/main/task%202.png", "category": "Writing Task 2", "link": "https://www.youtube.com/playlist?list=PLI3S3xWA78UWM9nT6jYY9vl3mHb52ZQ08"},
    {"id": 6, "title": "Chấm điểm IELTS Writing Task 1", "price": "FREE", "img": "https://raw.githubusercontent.com/linhchutvn/test/main/Assessment_TASK1.png", "category": "Writing Task 1", "link": "https://ielts-test.streamlit.app/"},
    {"id": 7, "title": "Chấm điểm IELTS Writing Task 2", "price": "FREE", "img": "https://raw.githubusercontent.com/linhchutvn/test/main/Assessment_TASK2.png", "category": "Writing Task 2", "link": "https://www.google.com"},
]

with search_col:
    search_term = st.text_input("Search", placeholder="Nhập tên khóa học...", label_visibility="collapsed")
with filter_col:
    categories = ["Tất cả"] + list(set([c['category'] for c in courses]))
    selected_category = st.selectbox("Category", categories, label_visibility="collapsed")

st.markdown("### 🔥 Các khóa học nổi bật")

# LOGIC & HIỂN THỊ
filtered_courses = courses
if selected_category != "Tất cả":
    filtered_courses = [c for c in courses if c['category'] == selected_category]
if search_term:
    filtered_courses = [c for c in filtered_courses if search_term.lower() in c['title'].lower()]

if not filtered_courses:
    st.warning("Không tìm thấy khóa học nào!")
else:
    cols = st.columns(3)
    for i, course in enumerate(filtered_courses):
        with cols[i % 3]:
            # Nút Xem chi tiết
            st.markdown(f"""
            <div class="product-card">
                <img src="{course['img']}" class="card-img" onerror="this.onerror=null; this.src='https://via.placeholder.com/400x200'">
                <div style="flex-grow: 1;">
                    <p class="course-title">{course['title']}</p>
                    <p class="course-price">{course['price']}</p>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <a href="{course.get('link', '#')}" target="_blank" style="background-color: #00b894; color: white; padding: 8px 20px; border-radius: 20px; text-decoration: none; font-size: 14px;">
                        Xem chi tiết
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

# FOOTER
logo_url = "https://raw.githubusercontent.com/linhchutvn/test/main/logo.png" 
st.markdown(f"""
<hr>
<div style="display: flex; justify-content: space-between; padding: 20px;">
    <div>
        <img src="{logo_url}" width="100" onerror="this.style.display='none'">
        <h4>Âu Việt Center</h4>
    </div>
    <div>
        <p>📍 Địa chỉ: 10 Thiên Phát, Quảng Ngãi</p>
        <p>📞 Hotline: 0866.771.333</p>
    </div>
</div>
<center style="color:#666; font-size:12px;">© 2025 Developed by Albert Nguyen</center>
""", unsafe_allow_html=True)
