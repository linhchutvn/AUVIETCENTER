import streamlit as st

# 1. Cấu hình trang
st.set_page_config(page_title="AuViet Center", layout="wide", page_icon="🎓")

# CSS tùy chỉnh để làm đẹp giao diện (Hack CSS trong Streamlit)
st.markdown("""
<style>
    /* CSS cho phần hiển thị thông tin */
    .course-info {
        margin-top: 5px;
        margin-bottom: 10px;
    }
    
    /* Chỉnh tiêu đề nhỏ gọn, khoảng cách thấp */
    .course-title {
        font-size: 18px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 2px !important; /* Thu hẹp khoảng cách dưới tiêu đề */
        line-height: 1.2;
    }
    
    /* Chỉnh dòng danh mục */
    .course-cat {
        font-size: 13px;
        color: #666;
        margin-bottom: 5px !important;
        margin-top: 0px !important;
    }
    
    /* Chỉnh giá tiền */
    .course-price {
        color: #d63031;
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 10px !important;
    }
    
    /* Nút bấm màu Xanh Ngọc Bích (Jade) */
    .custom-btn {
        display: inline-block; /* Giúp nút co giãn theo nội dung */
        background-color: #00b894; 
        color: white !important;
        padding: 8px 20px; /* Tăng khoảng cách đệm để nút nhìn đẹp hơn */
        border-radius: 5px; /* Bo tròn góc */
        
        text-decoration: none !important; /* QUAN TRỌNG: Bỏ gạch chân dưới chữ */
        
        font-weight: 500;
        font-size: 14px;
        text-align: center;
        transition: 0.3s;
        border: none;
        
        width: auto; /* QUAN TRỌNG: Dòng này giúp nút thu nhỏ lại vừa bằng chữ */
    }
    
    .custom-btn:hover {
        background-color: #019376;
        color: white !important;
        text-decoration: none !important;
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
        with cols[i % 3]:
            with st.container():
                # 1. Hiển thị ảnh (Vẫn dùng Streamlit để tự co giãn đẹp)
                try:
                    st.image(course['img'], use_column_width=True)
                except:
                    st.image("https://via.placeholder.com/400x200", use_column_width=True)
                
                # 2. Dùng HTML để hiển thị thông tin và nút bấm (Giúp sát dòng nhau)
                # Lưu ý: Chỗ href='{course['link']}' chính là link bạn đã thêm ở bước trước
                st.markdown(f"""
                <div class="course-info">
                    <p class="course-title">{course['title']}</p>
                    <p class="course-cat">Danh mục: {course['category']}</p>
                    <p class="course-price">{course['price']}</p>
                    <a href="{course.get('link', '#')}" target="_blank" class="custom-btn">
                        Xem chi tiết
                    </a>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
st.markdown("<center>© 2025 Âu Việt Center Developed by Albert Nguyen</center>", unsafe_allow_html=True)








