import streamlit as st

st.set_page_config(page_title="Luyện tập YouPass", layout="wide", page_icon="📝")

# ----------------------------------------------------------------
# THANH MENU ĐIỀU HƯỚNG (NAVBAR)
# ----------------------------------------------------------------
nav_col1, nav_col2, nav_col3 = st.columns([1, 1, 4])

with nav_col1:
    st.page_link("app.py", label="🏠 Trang chủ", icon=None, use_container_width=True)

with nav_col2:
    st.page_link("pages/writing.py", label="📝 Luyện tập YouPass", icon=None, use_container_width=True, disabled=True)

st.divider()

# ----------------------------------------------------------------
# CSS & NỘI DUNG TRANG YOUPASS
# ----------------------------------------------------------------
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;} /* Ẩn sidebar */
    
    .exam-card {
        background-color: white; border: 1px solid #e0e0e0; border-radius: 8px;
        padding: 15px; margin-bottom: 20px; display: flex; gap: 15px; position: relative;
    }
    .exam-tag {
        background-color: #1e272e; color: white; padding: 3px 8px;
        font-size: 10px; border-radius: 4px; position: absolute; top: 10px; left: 10px; z-index: 10;
    }
    .exam-thumb { width: 120px; height: 80px; object-fit: cover; border-radius: 6px; }
    .exam-title { color: #0984e3; font-weight: bold; text-decoration: none; font-size: 16px; }
    .exam-desc { font-size: 13px; color: #636e72; }
</style>
""", unsafe_allow_html=True)

# Giao diện chính YouPass (2 cột)
col_menu, col_content = st.columns([1, 4])

with col_menu:
    st.markdown("### YouPass Collect")
    st.info("💡 Review đề thi thật")
    mode = st.radio("Chọn kỹ năng", ["Reading", "Listening", "Writing"])

with col_content:
    st.markdown(f"#### 🕒 Danh sách bài tập: {mode}")
    
    # Dữ liệu giả lập
    exercises = [
        {"type": "Table", "title": "The table below illustrates weekly consumption...", "img": "https://via.placeholder.com/150x100?text=Table", "desc": "Table description here..."},
        {"type": "Map", "title": "Coal mining site redevelopment...", "img": "https://via.placeholder.com/150x100?text=Map", "desc": "Map description here..."},
        {"type": "Line", "title": "Going to the cinema statistics...", "img": "https://via.placeholder.com/150x100?text=Line", "desc": "Line graph description..."},
    ]
    
    grid = st.columns(2)
    for i, ex in enumerate(exercises):
        with grid[i % 2]:
            st.markdown(f"""
            <div class="exam-card">
                <span class="exam-tag">{ex['type']}</span>
                <img src="{ex['img']}" class="exam-thumb">
                <div>
                    <a href="#" class="exam-title">{ex['title']}</a>
                    <div class="exam-desc">{ex['desc']}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
