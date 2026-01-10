import streamlit as st

# 1. Cấu hình trang
st.set_page_config(page_title="AUVIET CENTER", layout="wide", page_icon="🎓")

# ----------------------------------------------------------------
# CSS: GIAO DIỆN CHUYÊN NGHIỆP & CĂN CHỈNH
# ----------------------------------------------------------------
st.markdown("""
<style>
    /* 1. Ẩn Sidebar & Ghim & Footer mặc định */
    [data-testid="stSidebar"] {display: none;}
    [data-testid="stHeaderAction"] {display: none !important;}
    footer {display: none !important;}

    /* 2. Căn chỉnh lề trang để không bị che bởi thanh công cụ phía trên */
    .block-container {
        padding-top: 3rem; /* Tăng lên 3rem để né thanh công cụ Streamlit */
        padding-bottom: 2rem;
    }

    /* 3. Style cho Nút Đăng nhập Google */
    .login-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        background-color: white;
        color: #3c4043;
        border: 1px solid #dadce0;
        border-radius: 20px;
        padding: 6px 16px; /* Tăng độ dày nút */
        text-decoration: none;
        font-weight: 500;
        font-size: 14px;
        transition: 0.3s;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .login-btn:hover {
        background-color: #f7fafe;
        border-color: #d2e3fc;
        color: #1a73e8;
    }
    
    /* 4. Style cho Logo chữ */
    .brand-text {
        font-size: 24px;
        font-weight: 800;
        color: #0984e3;
        margin: 0;
        line-height: 1.2; /* Giúp chữ không bị cắt dòng */
        white-space: nowrap; /* Không xuống dòng */
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------
# HEADER (NAVBAR) - CĂN GIỮA HOÀN HẢO
# ----------------------------------------------------------------
# vertical_alignment="center" giúp Logo, Menu và Nút Login tự động thẳng hàng
col_brand, col_nav, col_login = st.columns([2.5, 5, 1.5], gap="medium", vertical_alignment="center")

with col_brand:
    # Logo + Tên thương hiệu
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 10px;">
        <span style="font-size: 30px;">🎓</span>
        <span class="brand-text">AU VIET</span>
    </div>
    """, unsafe_allow_html=True)

with col_nav:
    # Menu điều hướng
    nav1, nav2 = st.columns(2)
    with nav1:
        # Nếu đang ở app.py thì disable nút Trang chủ, ngược lại ở luyentap.py thì disable nút kia
        # Bạn nhớ sửa True/False tùy theo file bạn đang dán code vào
        st.page_link("app.py", label="Trang chủ", icon="🏠", use_container_width=True) 
    with nav2:
        st.page_link("pages/luyentap.py", label="Luyện tập YouPass", icon="📝", use_container_width=True)

with col_login:
    # Nút đăng nhập (Căn phải)
    st.markdown("""
        <div style="display: flex; justify-content: flex-end;">
            <a href="https://accounts.google.com" target="_blank" class="login-btn">
                <img src="https://www.svgrepo.com/show/475656/google-color.svg" width="18" height="18" style="margin-right:8px;">
                Đăng nhập
            </a>
        </div>
    """, unsafe_allow_html=True)

st.divider() # Đường kẻ ngang phân cách

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

