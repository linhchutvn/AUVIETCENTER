import streamlit as st

# 1. Cấu hình trang
st.set_page_config(page_title="YouPass Clone Demo", layout="wide", page_icon="🎓")

# CSS tùy chỉnh để làm đẹp giao diện (Hack CSS trong Streamlit)
st.markdown("""
<style>
    .course-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
    }
    .price {
        color: #d63031;
        font-weight: bold;
        font-size: 18px;
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
    {"id": 1, "title": "Lập trình Python cơ bản", "price": "499.000đ", "img": "https://source.unsplash.com/random/400x200?coding", "category": "IT"},
    {"id": 2, "title": "Tiếng Anh giao tiếp", "price": "299.000đ", "img": "https://source.unsplash.com/random/400x200?english", "category": "Ngoại ngữ"},
    {"id": 3, "title": "Excel cho người đi làm", "price": "199.000đ", "img": "https://source.unsplash.com/random/400x200?excel", "category": "Tin học VP"},
    {"id": 4, "title": "Marketing căn bản", "price": "599.000đ", "img": "https://source.unsplash.com/random/400x200?marketing", "category": "Marketing"},
    {"id": 5, "title": "Data Science nhập môn", "price": "899.000đ", "img": "https://source.unsplash.com/random/400x200?data", "category": "IT"},
    {"id": 6, "title": "Thiết kế UI/UX", "price": "699.000đ", "img": "https://source.unsplash.com/random/400x200?design", "category": "Design"},
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

# Banner (Giả lập Banner Slider)
st.image("https://via.placeholder.com/1200x300.png?text=BANNER+QUANG+CAO+KHOA+HOC", use_column_width=True)

st.title("🔥 Các khóa học nổi bật")

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
                
                if st.button(f"Xem chi tiết", key=f"btn_{course['id']}"):
                    st.success(f"Bạn đã chọn xem khóa: {course['title']}")
                    # Ở đây có thể chuyển trang hoặc mở modal
            
            st.markdown("---") # Đường kẻ ngang phân cách hàng (nếu màn hình nhỏ)

# Footer
st.markdown("---")
st.markdown("<center>© 2025 Âu Việt Center Developed by Albert Nguyen</center>", unsafe_allow_html=True)





