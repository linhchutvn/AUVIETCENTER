import streamlit as st

# 1. Cấu hình trang
st.set_page_config(page_title="AuViet Center", layout="wide", page_icon="🎓")

# CSS tùy chỉnh để làm đẹp giao diện (Hack CSS trong Streamlit)
st.markdown("""
<style>
    .course-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 50px;
        margin-bottom: 10px;
        text-align: center;
    }
    .price {
        color: #d63031;
        font-weight: bold;
        font-size: 15px;
    }
    .stButton>button {
        width: 100%;
        background-color: #0984e3;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# 2. Dữ liệu giả lập (Mock Data) các khóa học
courses = [
    {"id": 1, "title": "Khoá học IELTS Speaking", "price": "499.000đ", "img": "https://source.unsplash.com/random/400x200?coding", "category": "Speaking", "link": "https://www.google.com"},
    {"id": 2, "title": "Khoá học IELTS Reading", "price": "299.000đ", "img": "https://source.unsplash.com/random/400x200?english", "category": "Reading", "link": "https://www.google.com"},
    {"id": 3, "title": "Khoá học IELTS Listening", "price": "199.000đ", "img": "https://source.unsplash.com/random/400x200?excel", "category": "Listening", "link": "https://www.google.com"},
    {"id": 4, "title": "Khoá học IELTS Writing Task 1", "price": "599.000đ", "img": "https://source.unsplash.com/random/400x200?marketing", "category": "Writing Task 1", "link": "https://www.google.com"},
    {"id": 5, "title": "Khoá học IELTS Writing Task 2", "price": "899.000đ", "img": "https://source.unsplash.com/random/400x200?data", "category": "Writing Task 2", "link": "https://www.google.com"},
    {"id": 6, "title": "Chấm điểm IELTS Writing Task 1", "price": "699.000đ", "img": "https://source.unsplash.com/random/400x200?design", "category": "Writing Task 1", "link": "https://ielts-albertnguyen.streamlit.app/"},
    {"id": 7, "title": "Chấm điểm IELTS Writing Task 2", "price": "699.000đ", "img": "https://source.unsplash.com/random/400x200?design", "category": "Writing Task 2", "link": "https://www.google.com"},
]

# 3. Sidebar - Bộ lọc & Menu
with st.sidebar:
    st.image("logo.png", width=150) # Thay bằng link logo thật nếu có
    st.header("🔍 Tìm kiếm & Lọc")
    
    search_term = st.text_input("Tìm khóa học...")
    
    categories = ["Tất cả"] + list(set([c['category'] for c in courses]))
    selected_category = st.selectbox("Danh mục", categories)
    
    st.markdown("---")
    st.write("📞 Hotline: 0866777333")
    if st.button("Đăng nhập"):
        st.write("Chức năng đang phát triển")

# 4. Main Content - Trang chủ

# Banner
st.image("banner.JPG", use_column_width=True)

st.title("🔥 Các khóa học tại Âu Việt")

# Xử lý Logic lọc dữ liệu
filtered_courses = courses
if selected_category != "Tất cả":
    filtered_courses = [c for c in courses if c['category'] == selected_category]
if search_term:
    filtered_courses = [c for c in filtered_courses if search_term.lower() in c['title'].lower()]

# Hiển thị dạng Grid (Lưới)
if not filtered_courses:
    st.warning("Không tìm thấy khóa học nào!")
else:
    # Chia lưới: 3 cột mỗi hàng
    cols = st.columns(3)
    
    for i, course in enumerate(filtered_courses):
        with cols[i % 3]: # Logic chia cột thông minh
            with st.container():
                # Hiển thị ảnh (dùng placeholder nếu ảnh lỗi)
                try:
                    st.image(course['img'], use_column_width=True)
                except:
                    st.image("https://via.placeholder.com/400x200", use_column_width=True)
                
                st.subheader(course['title'])
                st.markdown(f"**Danh mục:** {course['category']}")
                st.markdown(f"<p class='price'>{course['price']}</p>", unsafe_allow_html=True)
                # use_container_width=True giúp nút dài ra full bề ngang cho đẹp
                st.link_button("Xem chi tiết", course['link'], use_container_width=True)
                    # Ở đây có thể chuyển trang hoặc mở modal
            
            
# Footer
st.markdown("---")
st.markdown("<center>© 2025 Âu Việt Center Developed by Albert Nguyen</center>", unsafe_allow_html=True)





