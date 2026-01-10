import streamlit as st

# 1. Cấu hình trang
st.set_page_config(page_title="AuViet Center", layout="wide", page_icon="🎓")

# CSS tùy chỉnh để làm đẹp giao diện (Hack CSS trong Streamlit)
st.markdown("""
<style>
    /* 1. Tạo khung thẻ sản phẩm (Card) */
    .product-card {
        background-color: white; /* Màu nền của hộp */
        border: 1px solid #e0e0e0; /* Viền mỏng màu xám */
        border-radius: 10px; /* Bo tròn góc */
        padding: 15px; /* Khoảng cách từ viền vào nội dung */
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); /* Bóng đổ nhẹ giúp hộp nổi lên */
        margin-bottom: 20px; /* Khoảng cách với hộp dưới */
        transition: 0.3s; /* Hiệu ứng mượt khi di chuột */
        height: 100%; /* Giúp các hộp cao bằng nhau */
    }
    
    .product-card:hover {
        box-shadow: 0 8px 15px rgba(0,0,0,0.2); /* Bóng đổ đậm hơn khi di chuột vào */
        transform: translateY(-5px); /* Hộp nảy lên 1 chút */
    }

    /* 2. Style cho ảnh trong hộp */
    .card-img {
        width: 100%;
        border-radius: 5px;
        object-fit: cover;
        margin-bottom: 10px;
    }

    /* 3. Các dòng chữ */
    .course-title {
        font-size: 16px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 5px !important;
        line-height: 1.4;
        min-height: 45px; /* Giữ chiều cao tiêu đề đồng đều */
    }
    
    .course-cat {
        font-size: 12px;
        color: #7f8c8d;
        margin-bottom: 8px !important;
    }
    
    .course-price {
        color: #d63031;
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 15px !important;
    }
    
    /* 4. Nút bấm nhỏ gọn màu xanh ngọc */
    .custom-btn {
        display: inline-block;
        background-color: #00b894; 
        color: white !important;
        padding: 6px 15px;
        border-radius: 20px; /* Bo tròn nút nhiều hơn */
        text-decoration: none !important;
        font-weight: 500;
        font-size: 13px;
        text-align: center;
        border: none;
        width: auto;
    }
    .custom-btn:hover {
        background-color: #019376;
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
    st.image("logo.png", width=150)
    st.header("🔍 Tìm kiếm & Lọc")
    
    search_term = st.text_input("Tìm khóa học...")
    
    categories = ["Tất cả"] + list(set([c['category'] for c in courses]))
    selected_category = st.selectbox("Danh mục", categories)
    
    st.markdown("---")
    st.write("📞 Hotline: 0866.771.333")
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
            # Chỉ dùng 1 lệnh st.markdown duy nhất để vẽ toàn bộ cái hộp
            st.markdown(f"""
            <div class="product-card">
                <!-- Phần Ảnh -->
                <img src="{course['img']}" class="card-img" onerror="this.onerror=null; this.src='https://via.placeholder.com/400x200'">
                
                <!-- Phần Nội dung -->
                <p class="course-title">{course['title']}</p>
                <p class="course-cat">{course['category']}</p>
                <p class="course-price">{course['price']}</p>
                
                <!-- Phần Nút bấm -->
                <div style="text-align: center;">
                    <a href="{course.get('link', '#')}" target="_blank" class="custom-btn">
                        Xem chi tiết
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("---")
st.markdown("<center>© 2025 Âu Việt Center Developed by Albert Nguyen</center>", unsafe_allow_html=True)










