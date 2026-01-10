import streamlit as st

# 1. Cấu hình trang
st.set_page_config(page_title="AuViet Center", layout="wide", page_icon="🎓")

# CSS tùy chỉnh
st.markdown("""
<style>
    /* 1. Tạo khung thẻ sản phẩm (Card) */
    .product-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 20px; /* Khoảng cách giữa các hàng */
        transition: 0.3s;
        height: 100%; /* Quan trọng: Giữ chiều cao thẻ đồng đều */
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    
    .product-card:hover {
        box-shadow: 0 8px 15px rgba(0,0,0,0.2);
        transform: translateY(-5px);
    }

    /* 2. Style cho ảnh */
    .card-img {
        width: 100%;
        border-radius: 5px;
        object-fit: cover;
        height: 180px; /* Cố định chiều cao ảnh để các thẻ bằng nhau */
        margin-bottom: 10px;
    }

    /* 3. Các dòng chữ */
    .course-title {
        font-size: 18px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 5px !important;
        line-height: 1.3;
        min-height: 50px; /* Cố định chiều cao tiêu đề */
    }
    
    .course-cat {
        font-size: 13px;
        color: #7f8c8d;
        margin-bottom: 5px !important;
    }
    
    .course-price {
        color: #d63031;
        font-weight: bold;
        font-size: 16px;
        margin-bottom: 15px !important;
    }
    
    /* 4. Nút bấm */
    .custom-btn {
        display: inline-block;
        background-color: #00b894; 
        color: white !important;
        padding: 8px 20px;
        border-radius: 20px;
        text-decoration: none !important;
        font-weight: 500;
        font-size: 14px;
        text-align: center;
        border: none;
        width: auto;
    }
    .custom-btn:hover {
        background-color: #019376;
    }
</style>
""", unsafe_allow_html=True)

# 2. Dữ liệu giả lập
# LƯU Ý: Link ảnh unsplash.com đôi khi bị lỗi, mình thay tạm bằng placeholder để đảm bảo hiển thị
courses = [
    {"id": 1, "title": "Khoá học IELTS Speaking", "price": "499.000đ", "img": "https://github.com/linhchutvn/test/blob/main/SPEAKING.png?raw=true", "category": "Speaking", "link": "https://www.google.com"},
    {"id": 2, "title": "Khoá học IELTS Reading", "price": "299.000đ", "img": "https://via.placeholder.com/400x200?text=IELTS+Reading", "category": "Reading", "link": "https://www.google.com"},
    {"id": 3, "title": "Khoá học IELTS Listening", "price": "199.000đ", "img": "https://via.placeholder.com/400x200?text=IELTS+Listening", "category": "Listening", "link": "https://www.google.com"},
    {"id": 4, "title": "Khoá học IELTS Writing Task 1", "price": "599.000đ", "img": "https://via.placeholder.com/400x200?text=Writing+Task+1", "category": "Writing Task 1", "link": "https://www.google.com"},
    {"id": 5, "title": "Khoá học IELTS Writing Task 2", "price": "899.000đ", "img": "https://via.placeholder.com/400x200?text=Writing+Task+2", "category": "Writing Task 2", "link": "https://www.google.com"},
    {"id": 6, "title": "Chấm điểm IELTS Writing Task 1", "price": "699.000đ", "img": "https://via.placeholder.com/400x200?text=Cham+Diem+Task+1", "category": "Writing Task 1", "link": "https://ielts-test.streamlit.app/"},
    {"id": 7, "title": "Chấm điểm IELTS Writing Task 2", "price": "699.000đ", "img": "https://via.placeholder.com/400x200?text=Cham+Diem+Task+2", "category": "Writing Task 2", "link": "https://www.google.com"},
]

# 3. Sidebar
with st.sidebar:
    # Nếu file logo.png chưa có trên github thì dòng này sẽ lỗi, hãy upload file lên github nhé
    try:
        st.image("logo.png", width=150)
    except:
        st.header("AuViet Center") # Hiện chữ nếu không tìm thấy ảnh
        
    st.header("🔍 Tìm kiếm & Lọc")
    search_term = st.text_input("Tìm khóa học...")
    categories = ["Tất cả"] + list(set([c['category'] for c in courses]))
    selected_category = st.selectbox("Danh mục", categories)
    st.markdown("---")
    st.write("📞 Hotline: 0866.771.333")
    if st.button("Đăng nhập"):
        st.write("Chức năng đang phát triển")

# 4. Main Content
# Tương tự, nếu chưa có banner.JPG trên github thì sẽ lỗi
try:
    st.image("banner.JPG", use_column_width=True)
except:
    pass # Bỏ qua nếu không có banner

st.title("🔥 Các khóa học tại Âu Việt")

# Logic lọc
filtered_courses = courses
if selected_category != "Tất cả":
    filtered_courses = [c for c in courses if c['category'] == selected_category]
if search_term:
    filtered_courses = [c for c in filtered_courses if search_term.lower() in c['title'].lower()]

# Hiển thị
if not filtered_courses:
    st.warning("Không tìm thấy khóa học nào!")
else:
    cols = st.columns(3)
    
    # Đã sửa lỗi thụt đầu dòng ở đây
    for i, course in enumerate(filtered_courses):
        with cols[i % 3]:
            st.markdown(f"""
            <div class="product-card">
                <img src="{course['img']}" class="card-img" onerror="this.onerror=null; this.src='https://via.placeholder.com/400x200'">
                <div style="flex-grow: 1;">
                    <p class="course-title">{course['title']}</p>
                    <p class="course-cat">{course['category']}</p>
                    <p class="course-price">{course['price']}</p>
                </div>
                <div style="text-align: center; margin-top: 10px;">
                    <a href="{course.get('link', '#')}" target="_blank" class="custom-btn">
                        Xem chi tiết
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            # Đã xóa dòng st.markdown("---") để giao diện sạch đẹp hơn

st.markdown("---")
st.markdown("<center>© 2025 Âu Việt Center Developed by Albert Nguyen</center>", unsafe_allow_html=True)



