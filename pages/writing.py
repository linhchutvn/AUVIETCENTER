import streamlit as st

st.set_page_config(page_title="Luyện tập 4 kỹ năng", layout="wide", page_icon="📝")

# CSS chung
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    
    .login-btn {
        display: inline-flex; align-items: center; justify-content: center;
        background-color: white; color: #3c4043; border: 1px solid #dadce0;
        border-radius: 20px; padding: 5px 15px; text-decoration: none; font-size: 14px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    .login-btn:hover {background-color: #f7fafe;}
    [data-testid="stHeaderAction"] { display: none !important; }
</style>
""", unsafe_allow_html=True)

# HEADER (NAVBAR)
col_brand, col_nav, col_login = st.columns([2, 5, 2], gap="small", vertical_alignment="center")

with col_brand:
    st.markdown("<h3 style='margin:0; color:#0984e3;'>🎓 AU VIET</h3>", unsafe_allow_html=True)

with col_nav:
    nav1, nav2 = st.columns(2)
    with nav1:
        st.page_link("app.py", label="Trang chủ", icon="🏠", use_container_width=True)
    with nav2:
        st.page_link("pages/writing.py", label="Luyện tập 4 kỹ năng", icon="📝", use_container_width=True, disabled=True)

with col_login:
    st.markdown("""
        <div style="text-align: right;">
            <a href="https://accounts.google.com" target="_blank" class="login-btn">
                <img src="https://www.svgrepo.com/show/475656/google-color.svg" width="18" height="18" style="margin-right:8px;">
                Đăng nhập
            </a>
        </div>
    """, unsafe_allow_html=True)

st.divider()

st.markdown("""
<style>
    .exam-card { background-color: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin-bottom: 20px; display: flex; gap: 15px; position: relative; }
    .exam-tag { background-color: #1e272e; color: white; padding: 3px 8px; font-size: 10px; border-radius: 4px; position: absolute; top: 10px; left: 10px; z-index: 10; }
    .exam-thumb { width: 120px; height: 80px; object-fit: cover; border-radius: 6px; }
    .exam-title { color: #0984e3; font-weight: bold; text-decoration: none; font-size: 16px; }
</style>
""", unsafe_allow_html=True)

col_menu, col_content = st.columns([1, 4])
with col_menu:
    st.info("💡 Review đề thi thật")
    mode = st.radio("Chọn kỹ năng", ["Reading", "Listening", "Writing", "Speaking"])

with col_content:
    st.markdown(f"#### 🕒 Danh sách bài tập: {mode}")
    exercises = [
        {"type": "Table", "title": "The table below illustrates weekly consumption...", "img": "https://via.placeholder.com/150x100?text=Table"},
        {"type": "Map", "title": "Coal mining site redevelopment...", "img": "https://via.placeholder.com/150x100?text=Map"},
    ]
    grid = st.columns(2)
    for i, ex in enumerate(exercises):
        with grid[i % 2]:
            st.markdown(f"""
            <div class="exam-card">
                <span class="exam-tag">{ex['type']}</span>
                <img src="{ex['img']}" class="exam-thumb">
                <div><a href="#" class="exam-title">{ex['title']}</a></div>
            </div>
            """, unsafe_allow_html=True)
