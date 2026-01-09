import streamlit as st
import google.generativeai as genai
import json
import re
import time
from PIL import Image
import random
import textwrap

# ==========================================
# 1. CẤU HÌNH API & PROMPT
# ==========================================

ALL_KEYS = st.secrets["GEMINI_API_KEYS"]

def generate_content_with_failover(prompt, image=None):
    """Hàm thông minh tự động dò tìm Model tốt nhất có sẵn lượt dùng"""
    keys_to_try = list(ALL_KEYS)
    random.shuffle(keys_to_try) 
    
    # DANH SÁCH ƯU TIÊN (Giữ nguyên theo yêu cầu của bạn)
    model_priority = [
        #"gemini-2.0-flash-thinking-preview-01-21",
        #"gemini-3-pro-preview", 
        #"gemini-2.5-pro",
        "gemini-3-flash-preview",        
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-pro", 
        "gemini-1.5-flash"
    ]
    
    last_error = ""
    for index, current_key in enumerate(keys_to_try): # Thêm index để theo dõi số thứ tự Key
        try:
            genai.configure(api_key=current_key)
            
            # Lấy danh sách các model mà Key này THỰC SỰ có quyền truy cập
            available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
            
            # Tìm model tốt nhất
            sel_model = None
            for target in model_priority:
                if any(target in m_name for m_name in available_models):
                    sel_model = target
                    break
            
            if not sel_model:
                sel_model = "gemini-1.5-flash" 

            # --- [PHẦN THÊM MỚI] HIỂN THỊ THÔNG TIN MODEL ---
            # 1. Tạo mặt nạ cho Key (Chỉ hiện 4 số cuối để bảo mật)
            masked_key = f"****{current_key[-4:]}"
            
            # 2. Hiển thị thông báo nhỏ góc màn hình (Toast)
            st.toast(f"⚡ Đã kết nối: {sel_model}", icon="🤖")
            
            # 3. Hiển thị chi tiết trong giao diện (Tùy chọn: Dùng Expander để không rối mắt)
            with st.expander("🔌 Technical Connection Details (Debug)", expanded=False):
                st.write(f"**Active Model:** `{sel_model}`")
                st.write(f"**Active API Key:** `{masked_key}` (Key #{index + 1})")
                if "thinking" in sel_model.lower():
                    st.caption("🧠 Thinking Mode: ON")
            # ------------------------------------------------
            
            # Khởi tạo model
            temp_model = genai.GenerativeModel(
                model_name=sel_model, 
                # system_instruction=GRADING_PROMPT_TEMPLATE # Bỏ comment dòng này nếu bạn đã define biến này ở ngoài
            )
            
            content_parts = [prompt]
            if image:
                content_parts.append(image)
                
             # Cấu hình Generation Config
            gen_config = {
                "temperature": 0.3,       # Tăng nhẹ từ 0.1 lên 0.3 để AI giải thích phong phú hơn
                "top_p": 0.95,            # Cho phép AI chọn từ vựng đa dạng hơn
                "top_k": 64,              # Giúp câu văn mượt mà và sâu sắc hơn
                "max_output_tokens": 32000, # Đảm bảo AI có đủ "đất" để viết bản phân tích dài
            }

            # Nếu là model Thinking thì thêm cấu hình suy luận
            if "thinking" in sel_model.lower():
                gen_config["thinking_config"] = {
                    "include_thoughts": True,
                    "thinking_budget": 32000 # Đẩy max ngân sách suy nghĩ
                }

            # Thực hiện gọi API
            response = temp_model.generate_content(
                content_parts,
                generation_config=gen_config
            )
            
            # Trả về kết quả và tên model để hiển thị thêm nếu cần
            return response, sel_model 
            
        except Exception as e:
            last_error = str(e)
            if "429" in last_error or "quota" in last_error.lower() or "limit" in last_error.lower():
                continue 
            else:
                break
                
    st.error(f"❌ Toàn bộ {len(keys_to_try)} Keys đã hết hạn mức. Lỗi cuối: {last_error}")
    return None, None 

# Prompt "khủng" từ file gemini.ts của bạn
GRADING_PROMPT_TEMPLATE = """
Bạn hãy đóng vai trò là một Giám khảo IELTS với 30 năm kinh nghiệm làm việc tại Hội đồng Anh (British Council). Nhiệm vụ của bạn là đánh giá bài viết dựa trên **bộ tiêu chí chuẩn xác của IELTS Writing Task 1 (Band Descriptors)**. 
**Phân loại bài thi (Context Awareness):** Bắt buộc phải nhận diện đây là IELTS Academic: Biểu đồ/Đồ thị/Quy trình/Map. Đề bài nói về nội dung gì.
**Yêu cầu khắt khe:** Bạn phải sử dụng **tiêu chuẩn của Band 9.0 làm thước đo tham chiếu cao nhất** để soi xét bài làm. Hãy thực hiện một bản "Gap Analysis" chi tiết: chỉ ra mọi thiếu sót một cách nghiêm ngặt và chính xác tuyệt đối, từ những lỗi sai căn bản cho đến những điểm chưa đạt được độ tinh tế của một bài viết điểm tuyệt đối.
**YÊU CẦU ĐẶC BIỆT (CHẾ ĐỘ KIỂM TRA KỸ):** Bạn không cần phải trả lời nhanh. Hãy dành thời gian "suy nghĩ" để phân tích thật sâu và chi tiết (Step-by-step Analysis).
Nhiệm vụ của bạn là đọc bài viết dưới đây và đưa ra các bình luận (Comments) chi tiết cho từng đoạn văn, giống như cách bạn dùng tính năng "Add Comment" trong MS Word.

**YÊU CẦU BẮT BUỘC:**
1.  **Phân tích theo đoạn:** Nhận xét của bạn phải bám sát vào từng phần của bài viết (Introduction, Overview, Body 1, Body 2).
2.  **Phong cách "Comment":** Mỗi nhận xét phải bắt đầu bằng **"Commented [TG...]:"**. 
3.  **Chiến thuật "I'd do this":** Khi đưa ra gợi ý, hãy dùng văn phong cá nhân, ví dụ: *"I'd group these two together..."* hoặc *"You could add that..."*.
4.  **Tập trung vào Logic:** Ưu tiên bắt các lỗi về tư duy dữ liệu (Data Logic), cách nhóm thông tin (Grouping), và sự thiếu sót (Omission).

**QUY TRÌNH LÀM VIỆC:**
1.  Đọc toàn bộ bài viết.
2.  Với mỗi đoạn, viết ra 1-3 bình luận chi tiết.
3.  Tổng hợp các bình luận này thành một báo cáo Markdown duy nhất.
4.  Sau đó, mới tính điểm và xuất JSON như thường lệ.

### 1. TƯ DUY & GIAO THỨC LÀM VIỆC (CORE PROTOCOL)
* **>> GIAO THỨC PHÂN TÍCH CHẬM (SLOW REASONING PROTOCOL):**
    * Bạn không được phép tóm tắt nhận xét. Với mỗi tiêu chí, bạn phải viết ít nhất 200-300 từ.
    * Bạn phải thực hiện phân tích theo phương pháp "Socratic": Đặt câu hỏi về từng câu văn của thí sinh, tìm ra điểm chưa hoàn hảo và giải thích cặn kẽ tại sao nó chưa đạt Band 7.0 hoặc Band 9.0 từ dữ liệu bài viết này.
    * Cấm dùng các cụm từ chung chung như "Good grammar" hay "Appropriate vocabulary". Bạn phải trích dẫn ít nhất 3-5 ví dụ thực tế từ bài làm cho mỗi tiêu chí để chứng minh cho nhận định của mình.
*   **Persona:** Giám khảo lão làng, khó tính nhưng công tâm. Tông giọng phản hồi trực diện, không khen ngợi sáo rỗng. Nếu bài tệ, phải nói rõ là tệ.
*   **>> NGUYÊN TẮC "HOLISTIC SCORING" (Chấm điểm tổng hòa):** 
    *   Tuyệt đối phân biệt giữa **Lỗi hệ thống (Systematic error)** và **Lỗi trượt chân (Slip)**.
    *   *Lỗi trượt chân (Slip):* Là lỗi nhỏ, ngẫu nhiên (như viết thiếu 1 chữ cái, thừa 1 từ so sánh). Nếu bài viết thể hiện trình độ từ vựng/ngữ pháp xuất sắc, những lỗi này **KHÔNG ĐƯỢC** dùng làm lý do để hạ điểm từ 8 xuống 7 hoặc từ 9 xuống 8.
*   **Chế độ "Deep Scan":** Không trả lời nhanh. Hãy dành thời gian phân tích từng câu, từng từ theo quy trình "Step-by-step Analysis".
*   **Quy tắc "Truy quét kiệt quệ" (Exhaustive Listing):**
    *   Tuyệt đối KHÔNG gộp lỗi. Nếu thí sinh sai 10 lỗi mạo từ, liệt kê đủ 10 mục.
    *   Danh sách lỗi trong JSON là bằng chứng pháp lý. Mọi lỗi nhỏ nhất (dấu phẩy, viết hoa, mạo từ) đều phải được ghi nhận. Nếu JSON ít lỗi mà điểm GRA thấp, đó là một sự mâu thuẫn nghiêm trọng.
    *   **>> BỔ SUNG QUY TẮC TAXONOMY:** Khi phân loại lỗi trong JSON, chỉ được sử dụng các thuật ngữ chuẩn mực (ví dụ: Subject-Verb Agreement, Collocation, Article, Comma Splice). TUYỆT ĐỐI KHÔNG sáng tạo ra tên lỗi lạ (như "Bad word", "Wrong grammar").
*   **Nhận diện ngữ cảnh (Context Awareness):** Tự xác định là Academic (Biểu đồ/Process/Map) hay General Training (Thư) để áp dụng Band Descriptors tương ứng.
* **>> GIAO THỨC QUÉT 2 LỚP (TWO-PASS SCANNING):**
    * Lớp 1: Tìm các lỗi nặng (Cấu trúc, từ vựng sai ngữ cảnh, logic dữ liệu).
    * Lớp 2: Quét lại toàn bộ bài để tìm các lỗi nhỏ (Mạo từ, số ít/nhiều, dấu câu, viết hoa). 
    * Chỉ sau khi hoàn thành 2 lớp quét này mới được lập danh sách lỗi cuối cùng.
*   **>> NGUYÊN TẮC "APPROXIMATION TOLERANCE":** 
    *   Đối với các số liệu rất nhỏ (< 2-3%), chấp nhận các từ ngữ ước lượng mạnh như *"virtually no"*, *"almost zero"*, *"negligible"*. Đừng coi đây là lỗi sai dữ liệu (Logic Error) trừ khi số liệu thực tế > 5%.    

### 2. TIÊU CHÍ CHẤM ĐIỂM CHI TIẾT (4 CRITERIA)
#### A. Task Achievement (TA)
*   **Tư duy dữ liệu & Nhóm thông tin (Logical Grouping):**
    *   **Band 8.0+:** Thí sinh PHẢI biết nhóm các đối tượng tương đồng vào cùng đoạn văn một cách thông minh (Skilfully selected). Nếu chỉ liệt kê máy móc -> Tối đa Band 6-7.
    *   **>> BỔ SUNG QUY TẮC CHẶN BAND 6 (Comparison Rule):** Nếu bài viết chỉ mô tả đơn lẻ (description) số liệu của từng đối tượng mà KHÔNG CÓ sự so sánh (comparison) tương quan giữa các đối tượng -> **TỐI ĐA BAND 6.0** (Dù mô tả đúng 100%).
    *   **>> BỔ SUNG QUY TẮC "TOTAL/OTHER" (Safety Net):** Các hạng mục như 'Total', 'Miscellaneous', 'Other' KHÔNG ĐƯỢC tính là Key Features bắt buộc. Nếu thí sinh bỏ qua các số liệu này, HOÀN TOÀN KHÔNG ĐƯỢC TRỪ ĐIỂM. (Cảnh báo: Nếu trừ điểm lỗi này là sai quy chế).
*   **Độ dài & Sự súc tích (Word Count vs Conciseness):**
    *   **Không phạt oan:** Nếu bài > 200 từ nhưng thông tin đắt giá, số liệu chính xác 100% -> KHÔNG hạ điểm TA.
    *   `>> ƯU TIÊN "DATA SYNTHESIZING": Đánh giá cao nếu thí sinh biết biến số liệu % thành phân số (fractions) hoặc các cụm từ ước lượng (rounding) thay vì chỉ liệt kê số liệu thô từ bảng.`
    *   **Chỉ trừ điểm khi:** Bài viết dài dòng do lặp ý (Repetitive) hoặc lan man (Irrelevant). Nếu > 200 từ mà nội dung tốt, chỉ đưa vào phần "Lời khuyên" là nên cô đọng hơn.
    *   **Hình phạt:** < 150 từ (đánh giá khắt khe TA), < 20 từ (Band 1).
*   **Các bẫy "Chết người" (Negative Features - TA):**
    *   **Object vs Figure:** Phạt nặng lỗi sai chủ ngữ (VD: "The figure of apple rose" -> Sai; "The consumption of apple rose" -> Đúng).
    *   **Nhầm đơn vị:** Đề là % mà viết là Number -> Chặn đứng ở Band 5.0 TA.
    *   **No Data/Support:** Academic mà mô tả không có số liệu đi kèm -> Band 5.0.
    *   **Band 5 (Nguy hiểm):** Nếu mô tả xu hướng mà **không có số liệu (data)** đi kèm -> BẮT BUỘC hạ xuống Band 5 (Theo dòng in đậm: "There may be no data to support the description").
    *   **Overview:** Process phải đủ "Đầu-Giữa-Cuối"; Map phải có "Sự thay đổi tổng quan". Sai/Thiếu Overview -> Tối đa Band 5-6.
    *   **Band 7:** Phải xác định được xu hướng chính/sự khác biệt rõ ràng (Clear overview).
    *   **Band 6:** Có nỗ lực viết Overview nhưng thông tin chọn lọc sai hoặc không rõ ràng.
    *   **Band 5:** Không có Overview hoặc Overview sai lệch hoàn toàn.
    *   **Ý kiến cá nhân:** Tuyệt đối cấm. Có ý kiến cá nhân -> Trừ điểm nặng.
*   **>> BỔ SUNG QUY TẮC FORMAT & TONE:**
        *   **Lỗi định dạng (Format):** Nếu bài viết dùng gạch đầu dòng (bullet points) hoặc đánh số (1, 2, 3) thay vì viết đoạn văn -> **TỐI ĐA BAND 5.0 TA**.
        *   **Lỗi giọng điệu (Tone - GT):** Nếu đề yêu cầu "Formal letter" mà dùng ngôn ngữ suồng sã (slang, contractions like "gonna") -> Trừ điểm nặng xuống **Band 5.0-6.0**.
*   **Math Logic Check:** Soi kỹ các từ chỉ mức độ (slight, significant). Ví dụ: Từ 10% lên 15% là tăng gấp rưỡi -> Cấm dùng "slight".
*   **Endpoint Trap:** Cấm dùng "peak" cho năm cuối cùng của biểu đồ (vì không biết tương lai). Gợi ý: "ending at a high".
*   **>> CHIẾN THUẬT OVERVIEW BAND 8.0-9.0 (BẮT BUỘC ĐỐI CHIẾU):**
    1.  **Nguyên tắc "No Data":** Overview đạt Band cao TUYỆT ĐỐI không được chứa số liệu chi tiết. 
    2.  **Cấu trúc "Double Content":** Phải bao quát được cả (1) Xu hướng chính (Trends) VÀ (2) Sự so sánh nổi bật nhất (Major Comparisons/High-lows).
    3.  **Kỹ thuật Synthesis:** Đánh giá xem học sinh có biết gộp các đối tượng tương đồng để khái quát hóa không, hay chỉ đang liệt kê.
    4.  **Vị trí:** Khuyên học sinh đặt ngay sau Introduction để tạo luồng logic.
#### B. Coherence & Cohesion (CC)
*   **Liên kết "Vô hình" (Invisible Cohesion - Band 9):** Ưu tiên các cấu trúc "respectively", "in that order", mệnh đề quan hệ rút gọn.
*   **Mechanical Linkers (Lỗi máy móc):** Nếu câu nào cũng bắt đầu bằng "Firstly, Secondly, In addition, Furthermore" -> Tối đa Band 6.0.
*   **Paragraphing:** Bài viết phải chia đoạn logic. Chỉ có 1 đoạn văn -> CC tối đa 5.0.
*   **>> BỔ SUNG QUY TẮC "AMBIGUOUS REFERENCING" (The 'It' Trap):**
        *   Kiểm tra kỹ các đại từ thay thế (It, This, That, These, Those). Nếu dùng các từ này mà KHÔNG RÕ thay thế cho danh từ nào trước đó (gây khó hiểu) -> **TỐI ĐA BAND 6.0 CC**.
*   **>> QUY TẮC "INVISIBLE GLUE" (Keo dán vô hình):**
        *   Soi kỹ các từ dẫn đầu đoạn (Signposting words). Nếu thí sinh dùng lặp lại các từ như "Regarding...", "As for...", "Turning to..." quá 2 lần -> Đánh dấu là "Mechanical" (Máy móc).
        *   Khuyến khích cách chuyển đoạn bằng chủ ngữ ẩn hoặc Reference (Ví dụ: Thay vì "Regarding A, it increased...", hãy viết "A, conversely, witnessed a rise...").
*   **>> NGUYÊN TẮC LINH HOẠT CC:** Nếu bài viết có logic tốt và dễ hiểu, việc sử dụng từ nối hơi máy móc (như "Regarding") KHÔNG NÊN kéo điểm xuống 7.0 ngay lập tức. Hãy cân nhắc Band 8.0 nếu dòng chảy thông tin (flow) vẫn mượt mà. Chỉ hạ xuống 7.0 nếu việc dùng từ nối gây khó chịu hoặc làm gián đoạn việc đọc.
*   **>> YÊU CẦU OUTPUT CHO PHẦN NÀY:**
    *   **Trích dẫn chứng:** Phải trích dẫn câu văn cụ thể của thí sinh để phân tích.
    *   **Gợi ý "Vừa sức":** 
        *   Bài dưới Band 7 -> Gợi ý sửa cho ĐÚNG.
        *   Bài Band 7+ -> Gợi ý sửa cho HAY (Band 9).
#### C. Lexical Resource (LR)
*   **Naturalness over Academic:** Ưu tiên từ vựng tự nhiên (use, help, start) hơn là từ đao to búa lớn sai ngữ cảnh (utilise, facilitate, commence).
*   **Blacklist:** Cảnh báo các từ sáo rỗng/học thuộc lòng bị lạm dụng.
*   **Precision:** Soi kỹ Collocation (VD: "increased significantly" > "increased strongly").
*   **>> BỔ SUNG QUY TẮC "REPETITION" (Lặp từ):**
        *   Nếu một từ vựng quan trọng (ví dụ: "increase", "fluctuate") bị lặp lại > 3 lần mà không có nỗ lực thay thế (paraphrase) -> **TỐI ĐA BAND 5.0 LR** (Lỗi "Limited flexibility").
    *   **>> QUY TẮC CHÍNH TẢ (Spelling Threshold):**
        *   Sai 1-2 lỗi nhỏ -> Vẫn có thể Band 8.
        *   Sai vài lỗi (A few) nhưng vẫn hiểu được -> Band 7.
        *   Sai nhiều lỗi (Noticeable) nhưng vẫn hiểu được -> Band 6.
        *   Sai gây khó hiểu (Impede meaning) -> Band 5.
*   **>> NGUYÊN TẮC "NO DOUBLE PENALIZATION" (Không phạt kép):**
        *   Nếu lỗi thuộc về Redundancy (thừa từ: *most highest*) hoặc Spelling (*fluctation*), hãy tính nó vào điểm Lexical Resource (LR).
        *   KHÔNG trừ điểm Grammatical Range (GRA) cho những lỗi đã tính ở LR, trừ khi nó làm sai cấu trúc câu nghiêm trọng. Đây là lý do tại sao một bài có lỗi từ vựng vẫn có thể đạt 9.0 GRA nếu cấu trúc câu phức tạp và đa dạng.
*   **Word Choice:** Ưu tiên "Proportion" cho dữ liệu nhân lực/dân số. "Percentage" chỉ là con số thuần túy.
*   **Precision:** "Chosen one" -> Sai style. Sửa thành "Popular sector".
#### D. Grammatical Range & Accuracy (GRA)
*   **Độ chính xác tuyệt đối:** Soi kỹ từng lỗi mạo từ, giới từ, số ít/nhiều.
*   **Tỷ lệ câu không lỗi (Error-free sentences):**
    *   Band 6: Có lỗi nhưng không quá khó hiểu.
    *   Band 7: Câu không lỗi xuất hiện thường xuyên (Frequent).
    *   Band 8+: Đa số các câu hoàn toàn sạch lỗi (Majority error-free).
*   **Các lỗi kỹ thuật:**
    *   **Comma Splice:** Dùng dấu phẩy nối hai mệnh đề độc lập -> Kéo điểm xuống Band 5-6.
    *   **The Mad Max:** Lạm dụng hoặc thiếu mạo từ "the".
    *   **Past Perfect Trigger:** Thấy "By + [thời gian quá khứ]" mà không dùng Quá khứ hoàn thành -> Đánh dấu yếu kém về Range.
    *   **>> BỔ SUNG QUY TẮC DẤU CÂU (Punctuation Control):** Ngoài Comma Splice, nếu bài viết thường xuyên thiếu dấu phẩy ngăn cách mệnh đề phụ (Subordinate clause), hoặc viết hoa tùy tiện -> **KHÔNG ĐƯỢC CHẤM BAND 8.0 GRA**.
*   **>> CHIẾN THUẬT PARAPHRASING (Introduction Strategy):**
        *   Kiểm tra câu mở đầu (Introduction). Nếu thí sinh chỉ thay từ đồng nghĩa (synonyms) trong cụm danh từ (Noun Phrase), hãy đánh giá ở mức "Standard".
        *   Nếu thí sinh chuyển đổi được cấu trúc từ Noun Phrase (*the number of...*) sang Noun Clause (*how many...*), hãy ghi nhận đây là điểm cộng lớn cho Band 8+ GRA.
*   **Band 9 Threshold:** Nếu bài viết dùng câu phức hay và tự nhiên, cho phép 1-2 lỗi nhỏ (slips). Đừng kẹt ở Band 8.0 chỉ vì một lỗi mạo từ.
*   **>> NGUYÊN TẮC "SLIPS" TRONG GRA:** Band 9.0 GRA cho phép "rare minor errors" (các lỗi nhỏ hiếm gặp). Nếu bài viết sử dụng nhiều cấu trúc phức tạp một cách tự nhiên, đừng ngần ngại cho 9.0 dù vẫn còn 1-2 lỗi mạo từ hoặc số ít/nhiều. Đừng máy móc chặn ở 8.0.
*   **>> GIAO THỨC "PREPOSITION MICRO-SCANNING" (Soi Giới từ Chết người):**
    *   Sau khi quét toàn bộ bài viết, hãy thực hiện một lượt quét **thứ hai** chỉ để tìm lỗi giới từ đi kèm với số liệu và xu hướng.
    *   **To:** Dùng cho điểm đến cuối cùng (VD: "recovered **to** 15%").
    *   **At:** Dùng cho một điểm cố định (VD: "stood **at** 10%").
    *   **Of:** Dùng để chỉ giá trị của một danh từ (VD: "a level **of** 15%").
    *   **In:** Dùng cho năm (VD: "**in** 2015").
    *   **By:** Dùng để chỉ một lượng thay đổi (VD: "decreased **by** 5%").
    *   **BẮT BUỘC:** Nếu thí sinh dùng sai bất kỳ giới từ nào trong các trường hợp trên (ví dụ: dùng "at" hoặc "by" thay vì "to"), hãy bắt lỗi **"Preposition Error"** và giải thích rõ quy tắc sử dụng. Đây là lỗi cơ bản nhưng làm mất điểm rất nặng.
    
### 3. QUY TRÌNH CHẤM ĐIỂM & TỰ SỬA LỖI (SCORING & SELF-CORRECTION)

Mọi từ hoặc dấu câu nằm trong thẻ `<del>...</del>` ở bản sửa **BẮT BUỘC** phải có một mục nhập (entry) riêng biệt tương ứng trong danh sách `errors`. Tuyệt đối không được tóm tắt hay gộp lỗi.
**Bước 1: Deep Scan & Lập danh sách lỗi (JSON Errors Array)**
*   Dựa trên kết quả quét 3 lớp, liệt kê **TẤT CẢ** vấn đề vào mảng `errors`.
*   **>> QUY TẮC "BẰNG CHỨNG BẮT BUỘC" (MANDATORY EVIDENCE):**
    *   Nếu bạn định chấm điểm **Coherence & Cohesion dưới 9.0**, bạn **BẮT BUỘC** phải tạo ra ít nhất **2-3 mục lỗi** trong mảng `errors` thuộc nhóm `Coherence & Cohesion` để giải thích lý do trừ điểm.
    *   *Ví dụ:* Nếu chấm CC 6.0, bạn phải chỉ ra cụ thể: "Đoạn 2 thiếu câu chủ đề", "Từ nối 'Moreover' dùng sai", hoặc "Mạch văn bị đứt gãy".
    *   **CẤM:** Tuyệt đối không được để trống danh sách lỗi CC nếu điểm CC < 9.0.
*   **Thực hiện quét 2 lớp:** 
        *   *Lớp 1 (Grammar/Vocab):* Soi từng mạo từ, dấu phẩy, số ít/nhiều.
        *   *Lớp 2 (Data Logic):* Kiểm tra lỗi "Object vs Figure" (vd: nhầm giữa chủ thể ngành công nghiệp và lượng khí thải). 
*   **Liệt kê toàn bộ lỗi vào mảng `errors` trước.** Nếu có 14 vị trí sai, phải có 14 mục lỗi trong JSON. *Ví dụ:* Nếu sai 3 mạo từ 'the', phải có 3 mục lỗi riêng biệt.
*   **>> QUY TẮC "DOUBLE-TAGGING" (GẮN NHÃN KÉP - MỚI THÊM):**
    *   Nếu gặp lỗi ngữ pháp nghiêm trọng làm đứt gãy mạch văn (như `Sentence Fragment`, `Run-on Sentence`, `Comma Splice`), bạn phải tạo **2 mục lỗi** trong JSON:
        1.  Một mục `Grammar` (để sửa câu chữ).
        2.  Một mục `Coherence & Cohesion` với tên lỗi `Fragmented Flow` (để cảnh báo về mạch lạc).
    *   Điều này đảm bảo phần Coherence & Cohesion không bị trống và không hiển thị thông báo "Tuyệt vời" sai lệch.
*   Dựa trên danh sách lỗi này để tính toán Band điểm cho bài gốc (Markdown).
*   **Quy tắc làm tròn điểm bài viết theo chuẩn IELTS:**
    *   Làm tròn đến nửa band gần nhất (.0 hoặc .5).
    *   **NGOẠI LỆ BẮT BUỘC:**
        *   Điểm trung bình có đuôi **.25** -> BẮT BUỘC làm tròn **XUỐNG** số nguyên (Ví dụ: 8.25 -> 8.0).
        *   Điểm trung bình có đuôi **.75** -> BẮT BUỘC làm tròn **XUỐNG** .5 (Ví dụ: 8.75 -> 8.5).

**Bước 2: Tạo bản sửa lỗi (Annotated Essay)**
    *   **Nguyên tắc "Soi gương":** Bạn chỉ được phép sửa lỗi dựa trên danh sách lỗi đã lập ở Bước 1. 
    *   **Cấm sửa ngầm (No Hidden Edits):** Tuyệt đối không được "tiện tay" sửa các lỗi nhỏ (như thêm mạo từ 'the' hay viết hoa) trong bài sửa nếu bạn chưa khai báo lỗi đó trong danh sách `errors` ở Bước 1. 
    *   **Số lượng thẻ `<del>` phải bằng chính xác số lượng lỗi trong JSON.** Nếu sai lệch, hệ thống sẽ coi là vi phạm giao thức.
    
**Bước 3: Chấm lại bản sửa lỗi (JSON Output - Internal Re-grading)**
*   Hãy đóng vai một Giám khảo độc lập thứ 2 chấm lại bản `annotated_essay` vừa tạo (coi đây là một bài nộp mới đã sạch lỗi câu chữ).
*   **Luật Nội dung (Content Rule):** Vì bản sửa này chỉ khắc phục GRA/LR và giữ nguyên cấu trúc cũ, nên điểm TA và CC của bản sửa **THƯỜNG GIỮ NGUYÊN** như bài gốc. Nếu bài gốc thiếu Overview hoặc sai số liệu, bài sửa vẫn bị điểm thấp ở TA/CC.
*   **Điểm số `revised_score`:** Phải phản ánh đúng trình độ của bài sau khi đã sạch lỗi GRA/LR.
    *   **Kiểm tra độ dài:** Nếu bản sửa > 200 từ -> TA tối đa **8.0** (Phạt lỗi thiếu súc tích).
    *   **Kiểm tra tính tự nhiên:** Nếu dùng từ vựng "đao to búa lớn" gượng ép -> LR tối đa **8.0**.
*   **Lưu ý về TA & CC:** Vì bản sửa này chỉ sửa lỗi Ngữ pháp/Từ vựng và giữ nguyên cấu trúc cũ, nên điểm TA và CC của bản sửa **PHẢI GIỮ NGUYÊN** như bài gốc (trừ khi việc sửa từ vựng giúp ý nghĩa rõ ràng hơn thì có thể tăng nhẹ .5 điểm). 
*   **Consistency & Parity Check:** 
    *   Đếm số lượng thẻ `<del>` trong bài sửa. Nếu không khớp với số lượng mục lỗi trong mảng `errors` (Ví dụ: sửa 14 chỗ nhưng chỉ khai báo 7 lỗi), bạn đã vi phạm giao thức. Bạn phải bổ sung mảng `errors` cho đến khi đạt tỷ lệ **1:1**.
*   **>> CHỐT CHẶN BAND 9.0 (THE 9.0 BARRIER):**
    *   **Về Coherence & Cohesion (CC):** Tuyệt đối KHÔNG cho bản sửa đạt 9.0 nếu cấu trúc vẫn sử dụng các từ nối cơ bản ở đầu câu như *"Regarding...", "In addition...", "Overall..."*. Band 9 CC yêu cầu sự liên kết "vô hình" (invisible cohesion). Nếu cấu trúc bài gốc là Band 7-8, điểm CC của bản sửa **BẮT BUỘC** phải giữ nguyên ở mức 7-8.
    *   **Về Task Achievement & Lexical (TA/LR):** Kiểm tra lỗi logic "Object vs Figure". Nếu thí sinh viết *"Industry was the most polluted"* thay vì *"Industrial emissions were the highest"*, đây là lỗi tư duy dữ liệu nghiêm trọng. Bản sửa dù có sửa lại câu chữ thì điểm TA và LR vẫn phải bị khống chế (Ceiling) ở mức **7.0 - 8.0** vì lỗi sai bản chất chủ thể.
    *   **Về Đơn vị (Unit Accuracy):** Soi kỹ đơn vị (tonnes, %, number). Nếu bài gốc nhầm lẫn đơn vị, bản sửa dù có thay đổi từ vựng cũng không được phép tăng điểm TA quá 1.0 điểm so với bài gốc.
*   **>> GIAO THỨC "RE-SCAN" (QUÉT LẠI LẦN CUỐI):** Trước khi chốt điểm `revised_score`, hãy tự đặt câu hỏi: *"Tôi có đang quá hào phóng không? Nếu một Giám khảo khó tính nhất đọc bản sửa này, họ có thấy nó vẫn còn mang 'khung xương' của một bài Band 7 hay không?"*. Nếu có, hãy hạ điểm xuống ngay lập tức.
Thông tin bài làm:
a/ Đề bài (Task 1 question): {{TOPIC}}
b/ Mô tả hình ảnh (Picture/Graph/Chart): {{IMAGE_NOTE}}
c/ Bài làm của thí sinh (Written report): {{ESSAY}}

---
### NỘI DUNG ĐÁNH GIÁ CHI TIẾT:
**LƯU Ý QUAN TRỌNG VỀ SƯ PHẠM (PEDAGOGY RULE):**
Khi đưa ra ví dụ sửa lỗi (Example/Rewrite), bạn phải căn cứ vào **Band điểm hiện tại** của bài làm:
*   **Nếu bài < 6.0:** Hãy đưa ra ví dụ sửa ở mức **Band 7.0** (Tập trung vào sự Chính xác, Rõ ràng, Dễ hiểu). Đừng dùng từ quá khó.
*   **Nếu bài >= 6.5:** Hãy đưa ra ví dụ sửa ở mức **Band 9.0** (Tập trung vào sự Tinh tế, Học thuật, Cấu trúc phức tạp).
**QUY TẮC "CHỐNG SƠ SÀI" (ANTI-BREVITY RULE):**
1.  **Cấm nhận xét chung chung:** Tuyệt đối không viết "Cần cải thiện ngữ pháp" mà không chỉ rõ là cải thiện cái gì (thì, mạo từ, hay cấu trúc?).
2.  **Trích dẫn bằng chứng:** Mọi nhận xét đều phải trích dẫn câu văn cụ thể của thí sinh để chứng minh.
3.  **Luôn viết mẫu:** Dù bài làm ở Band 1 hay Band 9, bạn **BẮT BUỘC** phải cung cấp các ví dụ viết lại (Rewrite) ở cuối mỗi tiêu chí. Không được bỏ qua.

### **1. Task Achievement (Hoàn thành yêu cầu bài thi):**

*   **Đánh giá Overview (Cái nhìn tổng quan):** 
    *   [Phân tích: Đã có Overview chưa? Có nêu được xu hướng chính và sự so sánh nổi bật không?]
    *   **⚠️ Cảnh báo cho trình độ Band 5-6:** [Nếu Overview vẫn bị dính số liệu chi tiết, hãy giải thích tại sao lỗi này khiến họ bị kẹt ở Band 5 và hướng dẫn cách xóa bỏ để lên Band 7.]
*   **Độ chính xác và Chọn lọc dữ liệu:** 
    *   [Kiểm tra độ chính xác của số liệu. Có bị lỗi "Data Saturation" - nhồi nhét quá nhiều số liệu vụn vặt không?]
    *   [**Lưu ý:** Bỏ qua dữ liệu 'Total'/'Other' nếu không quan trọng.]
*   **Giải quyết yêu cầu (Response Strategy):** [Đánh giá cách nhóm thông tin. Thí sinh đang mô tả đơn lẻ (Band 5) hay đã biết tổng hợp dữ liệu để so sánh (Band 7+)?]

*   **⚠️ Các lỗi nghiêm trọng & Phân tích chuyên sâu:** 
    *   [Với mỗi lỗi tìm được, bạn **BẮT BUỘC** giải thích theo 3 bước:
        1. **Trích dẫn lỗi:** (Ví dụ: "the figure of pizza ate")
        2. **Lý do yếu kém:** (Ví dụ: Vi phạm lỗi tư duy Object vs Figure).
        3. **Tác động:** (Ví dụ: Làm mất tính chuyên nghiệp, khiến giám khảo đánh giá thấp tư duy logic).]

*   **💡 CHIẾN THUẬT NÂNG BAND (STEP-BY-STEP):**
    *   **Bước 1 (Lọc):** Tuyệt đối xóa số liệu khỏi Overview. Overview chỉ nói về "ý nghĩa" con số.
    *   **Bước 2 (Gộp):** Nhóm các đối tượng cùng tăng/cùng giảm để tạo sự súc tích (Economy).
    *   **Bước 3 (So sánh):** Luôn phải chỉ ra điểm cao nhất/thấp nhất hoặc sự thay đổi thứ hạng đáng kể.
    *   **Bước 4 (Kết nối):** Sử dụng liên kết "tàng hình" (While/Whereas/V-ing) thay vì từ nối máy móc.
    
*   **✍️ HÌNH MẪU ĐỐI CHIẾU (CHỌN MỨC PHÙ HỢP ĐỂ HỌC):**
    *   **Mẫu thực tế (Mục tiêu Band 7.0):** 
        *   *"Đây là phiên bản rõ ràng, chính xác, không lỗi logic mà bạn có thể đạt được ngay sau khi chỉnh sửa bài làm hiện tại:"*
        *   **[AI HÃY VIẾT OVERVIEW & BODY ĐẠT CHUẨN 7.0 DỰA TRÊN Ý TƯỞNG CỦA HỌC VIÊN]**
    *   **Mẫu chuyên sâu (Tham khảo Band 9.0):** 
        *   *"Đây là phiên bản để bạn tham khảo cách dùng từ vựng tinh tế và cấu trúc tổng hợp dữ liệu đỉnh cao của Giám khảo:"*
        *   **[AI HÃY VIẾT OVERVIEW & BODY ĐẠT CHUẨN 9.0 TẠI ĐÂY]**

> **📍 Điểm Task Achievement:** [Điểm số/9.0]

#### **2. Coherence and Cohesion (Độ mạch lạc và liên kết):**

*   **Tổ chức đoạn văn (Paragraphing):** [Phân tích logic chia đoạn: Bạn chia đoạn theo Tiêu chí gì (Thời gian/Đối tượng/Xu hướng)? Cách chia này có giúp người đọc dễ so sánh không? Mỗi đoạn có một trọng tâm rõ ràng không?]
*   **Sử dụng từ nối (Linking Devices):** [Đánh giá độ tự nhiên:
    *   **Cảnh báo:** Có bị lạm dụng từ nối đầu câu ("Mechanical Linking") như *Regarding, Turning to, Looking at, Firstly* không?
    *   **Khuyến khích:** Có sử dụng "Invisible Cohesion" (trạng từ đứng giữa câu như *meanwhile, however* hoặc dùng mệnh đề quan hệ để nối ý) không?]
*   **Phép tham chiếu (Referencing):** [Kiểm tra kỹ thuật Referencing: Bạn có sử dụng *it, this, that, the former, the latter, respectively* để tránh lặp từ không? Hay bạn lặp lại danh từ liên tục?]
*   **⚠️ Lỗi cần khắc phục:** [Chỉ ra cụ thể (càng nhiều càng tốt):
    1.  **Mạch văn đứt gãy:** Các câu rời rạc, không ăn nhập.
    2.  **Tham chiếu sai:** Dùng "it" nhưng không rõ thay thế cho từ nào (Ambiguous Reference).
    3.  **Lỗi cấu trúc:** Lặp lại cấu trúc câu (VD: Câu nào cũng bắt đầu bằng "The figure...").
    4.  **Câu thiếu động từ (Fragment):** Gây khó hiểu.]
*   **💡 Cải thiện & Nâng cấp (Correction & Upgrade):**
    *   *Câu gốc (Vấn đề):* "[Trích dẫn chính xác câu văn bị máy móc/lủng củng của thí sinh]"
    *   *Gợi ý viết lại (Natural Flow):* "[Nếu Band thấp: Sửa cho ĐÚNG ngữ pháp và RÕ nghĩa nối. Nếu Band 7+: Viết lại câu đó sử dụng cấu trúc liên kết ẩn hoặc chủ ngữ liên kết để đạt Band 8-9]"
    *   *Giải thích:* "[Tại sao cách viết mới giúp bài văn mượt mà và chuyên nghiệp hơn?]"
* **Yêu cầu bắt buộc về độ sâu:** Với mỗi lỗi tìm được, bạn phải giải thích theo 3 bước:
    1. Trích dẫn lỗi.
    2. Giải thích tại sao quy tắc Band Descriptors coi đây là điểm yếu.
    3. Phân tích tác động của lỗi này đến người đọc (gây hiểu lầm, làm mất tính chuyên nghiệp...).
    
> **📍 Điểm Coherence & Cohesion:** [Điểm số/9.0]

#### **3. Lexical Resource (Vốn từ vựng):**

*   **Đánh giá độ đa dạng (Range & Flexibility):** [Nhận xét tổng quan: Vốn từ của thí sinh đang ở mức nào? (Cơ bản/Đủ dùng/Phong phú). Có bị lỗi lặp từ ("Repetition") nghiêm trọng với các từ khóa chính (increase, decrease, figure...) không?]
*   **Độ chính xác và Văn phong (Precision & Style):** [Đánh giá: Thí sinh có dùng được các cụm từ kết hợp (Collocations) tự nhiên không hay là dịch từ tiếng mẹ đẻ (Word-for-word translation)? Có từ nào bị dùng sai ngữ cảnh (ví dụ: dùng văn nói "get up" thay vì "increase") không?]
*   **⚠️ Điểm yếu cốt lõi:** [Đừng liệt kê từng lỗi chính tả. Hãy chỉ ra **thói quen sai** của thí sinh. Ví dụ: *"Bạn thường xuyên chọn sai từ để mô tả đối tượng (Object)"* hoặc *"Bạn lạm dụng từ vựng quá trang trọng (Pretentious) không cần thiết"*.]
*   **💡 Gợi ý nâng cấp (Vocabulary Upgrade):**
    *   *Thay thế từ vựng thường:* "[Tìm 1 từ lặp lại nhiều nhất trong bài, ví dụ 'increase']"
    *   *Gợi ý thay thế:* 
        *   *[Nếu Band < 7]:* Gợi ý các từ cơ bản nhưng đúng (rise, growth, go up).
        *   *[Nếu Band 7+]:* Gợi ý các từ học thuật (escalate, upsurge, register a growth).
* **Yêu cầu bắt buộc về độ sâu:** Với mỗi lỗi tìm được, bạn phải giải thích theo 3 bước:
    1. Trích dẫn lỗi.
    2. Giải thích tại sao quy tắc Band Descriptors coi đây là điểm yếu.
    3. Phân tích tác động của lỗi này đến người đọc (gây hiểu lầm, làm mất tính chuyên nghiệp...).
    
> **📍 Điểm Lexical Resource:** [Điểm số/9.0]

#### **4. Grammatical Range and Accuracy (Ngữ pháp):**

*   **Độ đa dạng cấu trúc (Range Check):** [Phân tích chiến lược: Bài viết có "nghèo nàn" cấu trúc không? (Chỉ dùng câu đơn/câu ghép cơ bản). Thí sinh có sử dụng được các cấu trúc Band 8+ không: *Passive Voice (Bị động)*, *Reduced Relative Clause (Rút gọn mệnh đề)*, *Nominalization (Danh từ hóa)*?]
*   **Độ chính xác (Accuracy Check):** [Ước lượng tỷ lệ câu không lỗi (Error-free sentences): Dưới 50% (Band 5), 50-70% (Band 6-7), hay trên 80% (Band 8+)? Lỗi sai chủ yếu là lỗi hệ thống (Systematic - sai quy tắc) hay lỗi sơ suất (Slips)?].Nếu bài viết có trên 80% số câu hoàn toàn sạch lỗi (Error-free) và lỗi duy nhất là một lỗi nhỏ (như "most highest") -> **Vẫn giữ mức Band 8.5 - 9.0**. Đừng ép thí sinh dùng cấu trúc lạ nếu cấu trúc hiện tại đã quá đủ để truyền đạt thông tin một cách tinh tế. Band 9 không bắt buộc phải có "Đảo ngữ" hay "Câu điều kiện". Range được thể hiện qua việc sử dụng linh hoạt: Mệnh đề quan hệ, câu phân từ (Reduced clauses), danh từ hóa (Nominalization), và các cấu trúc so sánh phức tạp. 
*   **Dấu câu (Punctuation):** [Nhận xét việc dùng dấu phẩy, dấu chấm. Có mắc lỗi *Comma Splice* (Dấu phẩy nối câu) kinh điển không?]
*   **⚠️ Lỗi hệ thống cần sửa:** [Chỉ ra lỗ hổng kiến thức ngữ pháp lớn nhất của thí sinh. Ví dụ: *"Bạn rất yếu về Mệnh đề quan hệ"* hoặc *"Bạn chưa nắm vững cách dùng Mạo từ"*.]
*   **💡 Thử thách viết lại (Sentence Transformation):**
    *   *Câu gốc (Simple/Error):* "[Trích 1 câu đơn giản hoặc có lỗi trong bài]"
    *   *Nâng cấp câu:* 
        *   *[Nếu Band thấp]:* Ghép thành câu ghép/câu phức cơ bản (dùng because, although) để đảm bảo đúng.
        *   *[Nếu Band cao]:* Dùng cấu trúc nâng cao (Mệnh đề phân từ, Đảo ngữ, Nominalization).
* **Yêu cầu bắt buộc về độ sâu:** Với mỗi lỗi tìm được, bạn phải giải thích theo 3 bước:
    1. Trích dẫn lỗi.
    2. Giải thích tại sao quy tắc Band Descriptors coi đây là điểm yếu.
    3. Phân tích tác động của lỗi này đến người đọc (gây hiểu lầm, làm mất tính chuyên nghiệp...).
    
> **📍 Điểm Grammatical Range & Accuracy:** [Điểm số/9.0]

---
### **TỔNG ĐIỂM (OVERALL BAND SCORE):** Quy tắc làm tròn điểm bài viết theo chuẩn IELTS:
    *   Làm tròn đến nửa band gần nhất (.0 hoặc .5).
    *   **NGOẠI LỆ BẮT BUỘC:**
        *   Điểm trung bình có đuôi **.25** -> BẮT BUỘC làm tròn **XUỐNG** số nguyên (Ví dụ: 8.25 -> 8.0).
        *   Điểm trung bình có đuôi **.75** -> BẮT BUỘC làm tròn **XUỐNG** .5 (Ví dụ: 8.75 -> 8.5).

---
### **LỜI KHUYÊN CHIẾN THUẬT TỪ GIÁM KHẢO (EXAMINER'S TIPS):**
1.  **Đưa ra các lời khuyên:** Hãy đưa ra các lời khuyên chiến thuật dựa trên những lỗi sai thực tế trong bài.
2.  **Economy:** Cách cắt giảm số từ thừa (nếu bài > 200 từ).
3.  **Introduction Power:** Cách đổi Noun Phrase -> Noun Clause trong mở bài.
4.  **Grouping:** Cách nhóm thông tin thông minh hơn (nhóm theo xu hướng Lớn vs Nhỏ).
5.  **Overview:** Cách viết Overview tốt hơn.

#### **5. DỮ LIỆU PHÂN TÍCH (ANALYSIS DATA):**

Sau khi đánh giá xong, bạn **BẮT BUỘC** phải trích xuất dữ liệu dưới dạng một **JSON Object duy nhất**.

**QUAN TRỌNG:** Trong trường "type" (Tên lỗi), bạn CHỈ ĐƯỢC PHÉP được dùng các thuật ngữ tiếng Anh chuẩn học thuật dưới đây:

**A. [COHERENCE & COHESION] - Macro Errors:**
# Organization & Progression (Tổ chức & Phát triển)
`Illogical Grouping` (Sắp xếp phi logic), `Missing Overview` (Thiếu tổng quan), `Fragmented Flow` (Mạch văn đứt gãy), `Lack of Progression` (Không phát triển ý), `Incoherent Paragraphing` (Chia đoạn không mạch lạc).
# Linking & Reference (Liên kết & Tham chiếu)
`Mechanical Linking` (Từ nối máy móc), `Overuse of Connectors` (Lạm dụng từ nối), `Ambiguous Referencing` (Tham chiếu mơ hồ), `Repetitive Structure` (Lặp cấu trúc), `Data Inaccuracy` (Sai số liệu/Logic).

**B. [GRAMMAR] - Micro Errors:**
# Sentence Structure (Cấu trúc câu)
`Comma Splice` (Lỗi dấu phẩy), `Run-on Sentence` (Câu dính liền), `Sentence Fragment` (Câu thiếu thành phần), `Faulty Parallelism` (Lỗi song song), `Misplaced Modifier` (Bổ ngữ sai chỗ), `Word Order` (Trật tự từ).
# Morphology & Syntax (Hình thái & Cú pháp)
`Subject-Verb Agreement` (Hòa hợp chủ vị), `Tense Inconsistency` (Sai thì), `Passive Voice Error` (Lỗi bị động), `Relative Clause Error` (Lỗi mệnh đề quan hệ).
# Mechanics (Cơ học)
`Article Error` (Mạo từ), `Preposition Error` (Giới từ), `Singular/Plural` (Số ít/nhiều), `Countable/Uncountable` (Danh từ đếm được/không), `Punctuation` (Dấu câu).

**C. [VOCABULARY] - Lexical Errors:**
# Meaning & Use (Nghĩa & Cách dùng)
`Imprecise Word Choice` (Dùng từ thiếu chính xác), `Incompatible Collocation` (Kết hợp từ sai), `Word Form Error` (Sai loại từ), `Selectional Restriction Violation` (Vi phạm quy tắc chọn lọc từ).
# Style & Register (Văn phong)
`Informal Register` (Văn phong suồng sã), `Pretentious Language` (Dùng từ sáo rỗng/làm màu), `Redundancy` (Thừa từ/Lặp ý), `Forced Paraphrasing` (Paraphrase gượng ép).

**CATEGORY MAPPING RULE:**
*   Group A -> `category`: "Coherence & Cohesion"
*   Group B -> `category`: "Grammar"
*   Group C -> `category`: "Vocabulary"

**TỰ CHẤM LẠI BẢN SỬA (INTERNAL RE-GRADING - BƯỚC QUAN TRỌNG NHẤT):**
   - Hãy quên rằng bạn vừa sửa bài này. Hãy đóng vai một Giám khảo độc lập thứ 2 chấm lại bản 'annotated_essay' vừa tạo.
   - **Luật Nội dung (Content Rule):** Bản sửa chỉ sửa ngữ pháp/từ vựng, KHÔNG THỂ sửa lỗi thiếu số liệu/thiếu so sánh của bài gốc. Nếu bài gốc TA 6.0, bản sửa TA vẫn là 6.0 (hoặc tối đa 7.0 nếu diễn đạt rõ hơn).
   - **Kết luận:** Điểm 'revised_score' PHẢI là điểm thực tế của bản sửa, KHÔNG ĐƯỢC mặc định là 9.0.
Cấu trúc JSON:
```json
{
  "original_score": {
      "task_achievement": "Điểm TA của bài làm gốc (User's essay)",
      "cohesion_coherence": "Điểm CC của bài làm gốc",
      "lexical_resource": "Điểm LR của bài làm gốc",
      "grammatical_range": "Điểm GRA của bài làm gốc",
      "overall": "Điểm Overall của bài làm gốc (Average)"
  },
  "errors": [
    {
      "category": "Grammar" hoặc "Vocabulary",
      "type": "Tên Lỗi",
      "impact_level": "High" | "Medium" | "Low",
      "explanation": "Giải thích ngắn gọn lỗi.",
      "original": "đoạn văn bản sai",
      "correction": "đoạn văn bản đúng (VIẾT IN HOA)"
    }
  ],
  "annotated_essay": "Phiên bản bài làm đã được sửa lỗi (giữ nguyên cấu trúc các đoạn văn). Bọc từ sai trong thẻ <del>...</del> và từ sửa đúng trong thẻ <ins class='grammar'>...</ins> hoặc <ins class='vocab'>...</ins>. Nội dung sửa đúng phải viết IN HOA.",
   "revised_score": {
      "word_count_check": "BẮT BUỘC GHI SỐ TỪ CỦA BẢN SỬA (Ví dụ: '220 words - Too long')",
      "logic_re_evaluation": "Giải thích tại sao bị trừ điểm (Ví dụ: 'Dù sạch lỗi ngữ pháp nhưng bài viết dài 220 từ, vi phạm nguyên tắc súc tích, nên TA chỉ đạt 8.0').",
      "task_achievement": "Điểm TA thực tế (phạt nặng nếu dài dòng)",
      "cohesion_coherence": "Điểm CC",
      "lexical_resource": "Điểm LR",
      "grammatical_range": "Điểm GRA",
      "overall": "Điểm trung bình (Làm tròn theo Quy tắc làm tròn điểm bài viết theo chuẩn IELTS)"
          *   Làm tròn đến nửa band gần nhất (.0 hoặc .5).
          *   **NGOẠI LỆ BẮT BUỘC:**
              *   Điểm trung bình có đuôi **.25** -> BẮT BUỘC làm tròn **XUỐNG** số nguyên (Ví dụ: 8.25 -> 8.0).
              *   Điểm trung bình có đuôi **.75** -> BẮT BUỘC làm tròn **XUỐNG** .5 (Ví dụ: 8.75 -> 8.5).
  }
}
```
"""

# ==========================================
# 2. CẤU HÌNH GIAO DIỆN (Từ index.html & styles)
# ==========================================
st.set_page_config(page_title="IELTS Examiner Pro", page_icon="🛡️", layout="wide")

# CSS để tái tạo giao diện React (Màu sắc, Font Merriweather/Inter, Error Cards)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Merriweather:wght@300;400;700&display=swap');
    
    /* Font và màu sắc Global */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Style cho Header */
    h1 {
        font-family: 'Merriweather', serif !important;
        color: #0F172A !important;
        font-weight: 700 !important;
    }
    .pro-badge {
        color: #D40E14; 
        font-weight: bold;
    }
    .verified-badge {
        background-color: #F1F5F9;
        border: 1px solid #E2E8F0;
        padding: 4px 12px;
        border-radius: 99px;
        font-size: 14px;
        font-weight: bold;
        color: #475569;
        display: inline-flex;
        align-items: center;
        margin-left: 10px;
    }
    
    /* Style cho Error Cards (Giống MessageBubble.tsx) */
    .error-card {
        background-color: white;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        transition: all 0.2s;
    }
    .error-card:hover {
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-color: #D1D5DB;
    }
    .error-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        border-bottom: 1px solid #F3F4F6;
        padding-bottom: 8px;
    }
    .error-badge-grammar {
        background-color: #DCFCE7;
        border: 1px solid #22C55E;
        color: #022C22;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 800;
        text-transform: uppercase;
    }
    .error-badge-vocab {
        background-color: #FEF9C3;
        border: 1px solid #FCD34D;
        color: #713F12;
        padding: 2px 8px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 800;
        text-transform: uppercase;
    }
    .impact-high { background-color: #FEE2E2; color: #991B1B; padding: 2px 8px; border-radius: 99px; font-size: 14px; font-weight: bold; border: 1px solid #FECACA;}
    .impact-medium { background-color: #FFEDD5; color: #9A3412; padding: 2px 8px; border-radius: 99px; font-size: 14px; font-weight: bold; border: 1px solid #FED7AA;}
    .impact-low { background-color: #DBEAFE; color: #1E40AF; padding: 2px 8px; border-radius: 99px; font-size: 14px; font-weight: bold; border: 1px solid #BFDBFE;}
    
    .correction-box {
        background-color: #F9FAFB;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 12px;
        font-size: 16px;
        border: 1px solid #F3F4F6;
    }
    
    /* Style cho Annotated Essay */
    .annotated-text {
        font-family: 'Merriweather', serif;
        line-height: 1.8;
        color: #374151;
        background-color: white;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    del {
        color: #9CA3AF;
        text-decoration: line-through;
        margin-right: 4px;
        text-decoration-thickness: 2px;
    }
    ins.grammar {
        background-color: #4ADE80;
        color: #022C22;
        text-decoration: none;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 700;
        border: 1px solid #22C55E;
    }
    ins.vocab {
        background-color: #FDE047;
        color: #000;
        text-decoration: none;
        padding: 2px 6px;
        border-radius: 4px;
        font-weight: 700;
        border: 1px solid #FCD34D;
    }
    
    /* Button Style */
    div.stButton > button {
        background-color: #D40E14;
        color: white;
        font-weight: bold;
        border: none;
        padding: 10px 24px;
        border-radius: 8px;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #B91C1C;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LOGIC KẾT NỐI AI & XỬ LÝ DỮ LIỆU
# ==========================================

import html
import os
import requests
import re
import time
from io import BytesIO

# Thư viện Word
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Thư viện PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping

# --- HÀM TỰ ĐỘNG TẢI & ĐĂNG KÝ FONT ROBOTO (HỖ TRỢ TIẾNG VIỆT) ---
def clean_json(text):
    """Trích xuất JSON từ phản hồi của AI"""
    match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if match:
        content = match.group(1)
        content = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', content)
        return content.strip()
    return None

def calculate_overall(scores):
    """Hàm phụ: Tự tính điểm Overall chuẩn IELTS từ 4 điểm thành phần"""
    try:
        # Lọc bỏ các giá trị không phải số
        valid_scores = []
        for s in scores:
            try:
                valid_scores.append(float(s))
            except:
                continue
                
        if not valid_scores or len(valid_scores) < 4: return '-'
        
        avg = sum(valid_scores) / len(valid_scores)
        decimal = avg - int(avg)
        
        # Quy tắc làm tròn IELTS (.25 lên .5, .75 lên 1.0)
        if decimal < 0.25: final = int(avg)
        elif decimal < 0.75: final = int(avg) + 0.5
        else: final = int(avg) + 1.0
        
        return str(final)
    except:
        return '-'

def process_response(full_text):
    """
    1. Tách JSON để lấy danh sách lỗi và bài sửa.
    2. Dùng Regex quét văn bản Markdown để lấy điểm Gốc (Original Score).
    """
    json_str = clean_json(full_text)
    markdown_part = full_text
    
    # Khởi tạo cấu trúc dữ liệu mặc định
    data = {
        "errors": [], 
        "annotatedEssay": None, 
        "revisedScore": None, 
        "originalScore": {
            "task_achievement": "-",
            "cohesion_coherence": "-",
            "lexical_resource": "-",
            "grammatical_range": "-",
            "overall": "-"
        }
    }
    
    # A. Xử lý JSON (Chủ yếu để lấy Lỗi và Bài sửa)
    if json_str:
        markdown_part = full_text.split("```json")[0].strip()
        try:
            parsed = json.loads(json_str)
            data["errors"] = parsed.get("errors", [])
            data["annotatedEssay"] = parsed.get("annotated_essay")
            data["revisedScore"] = parsed.get("revised_score")
        except json.JSONDecodeError:
            pass

    # B. QUAN TRỌNG: COPY ĐIỂM TỪ VĂN BẢN (Regex Scanning)
    patterns = {
        "task_achievement": r"Điểm\s+Task\s+Achievement.*?(\d+\.?\d*)",
        "cohesion_coherence": r"Điểm\s+Coherence.*?(\d+\.?\d*)",
        "lexical_resource": r"Điểm\s+Lexical.*?(\d+\.?\d*)",
        "grammatical_range": r"Điểm\s+Grammatical.*?(\d+\.?\d*)",
    }
    
    found_scores = []
    
    # Quét từng tiêu chí trong văn bản markdown
    for key, regex in patterns.items():
        match = re.search(regex, markdown_part, re.IGNORECASE | re.DOTALL)
        if match:
            score = match.group(1) # Lấy con số tìm được
            data["originalScore"][key] = score
            found_scores.append(score)
        else:
            # Nếu không tìm thấy, thử tìm trong JSON dự phòng
            try:
                if json_str:
                    parsed = json.loads(json_str)
                    val = parsed.get("original_score", {}).get(key, "-")
                    data["originalScore"][key] = str(val)
                    if str(val) != "-": found_scores.append(val)
            except:
                pass

    # C. Tự tính Overall từ các điểm vừa tìm được
    if found_scores:
        data["originalScore"]["overall"] = calculate_overall(found_scores)

    return markdown_part, data

# --- 2. CÁC HÀM XUẤT FILE (FILE EXPORT) ---

def register_vietnamese_font():
    """Tải và đăng ký font Roboto từ Google Fonts (Github Source)"""
    font_reg = "Roboto-Regular.ttf"
    font_bold = "Roboto-Bold.ttf"
    
    # URL mới chính xác (Dùng kho 'src/hinted' của googlefonts)
    urls = {
        font_reg: "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
        font_bold: "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    }
    
    # Headers giả lập trình duyệt để tránh lỗi 403/404
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        # 1. Tải font về nếu chưa có hoặc file bị lỗi (0kb)
        for filename, url in urls.items():
            if os.path.exists(filename) and os.path.getsize(filename) < 1000:
                os.remove(filename) # Xóa file lỗi
                
            if not os.path.exists(filename):
                response = requests.get(url, headers=headers, timeout=20)
                if response.status_code == 200:
                    with open(filename, "wb") as f:
                        f.write(response.content)
                else:
                    print(f"❌ Không tải được {filename}. Mã lỗi: {response.status_code}")

        # 2. Đăng ký với ReportLab
        if os.path.exists(font_reg) and os.path.exists(font_bold):
            pdfmetrics.registerFont(TTFont('Roboto', font_reg))
            pdfmetrics.registerFont(TTFont('Roboto-Bold', font_bold))
            addMapping('Roboto', 0, 0, 'Roboto') # Normal
            addMapping('Roboto', 1, 0, 'Roboto-Bold') # Bold
            return True
        else:
            print("⚠️ Không tìm thấy file font sau khi tải.")
            return False
            
    except Exception as e:
        print(f"❌ Lỗi xử lý font: {e}")
        return False

# HÀM TẠO FILE WORD
def create_docx(data, topic, original_essay, analysis_text):
    doc = Document()
    
    # Header
    heading = doc.add_heading('IELTS WRITING TASK 1 - ASSESSMENT REPORT', 0)
    heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.add_paragraph(f"Date: {time.strftime('%d/%m/%Y')}")
    
    # 1. BAND SCORE
    doc.add_heading('1. BAND SCORE', level=1)
    scores = data.get("originalScore")
    
    if scores and isinstance(scores, dict) and scores.get('overall', '-') != '-':
        table = doc.add_table(rows=2, cols=5)
        table.style = 'Table Grid'
        
        headers = ['Task Achievement', 'Coherence', 'Lexical Resource', 'Grammar', 'OVERALL']
        for i, h in enumerate(headers):
            cell = table.cell(0, i)
            cell.text = h
            cell.paragraphs[0].runs[0].bold = True
        
        vals = [
            str(scores.get('task_achievement', '-')),
            str(scores.get('cohesion_coherence', '-')),
            str(scores.get('lexical_resource', '-')),
            str(scores.get('grammatical_range', '-')),
            str(scores.get('overall', '-'))
        ]
        for i, v in enumerate(vals):
            table.cell(1, i).text = v
    else:
        doc.add_paragraph("Score details could not be extracted automatically.")

    # 2. ANALYSIS
    doc.add_heading('2. EXAMINER\'S DETAILED ANALYSIS', level=1)
    if analysis_text:
        clean_analysis = analysis_text.replace('**', '').replace('### ', '').replace('#### ', '')
        doc.add_paragraph(clean_analysis)

    # 3. ERRORS
    doc.add_heading('3. DETAILED ERROR LOG', level=1)
    if data.get("errors"):
        for err in data['errors']:
            p = doc.add_paragraph(style='List Bullet')
            runner = p.add_run(f"[{err['category']} - {err['type']}]: ")
            runner.bold = True
            runner.font.color.rgb = RGBColor(200, 0, 0)
            p.add_run(f" '{err['original']}' → '{err['correction']}'")
            p.add_run(f"\n   Reason: {err['explanation']}")
    else:
        doc.add_paragraph("No specific errors detected.")

    # APPENDIX
    doc.add_page_break()
    doc.add_heading('APPENDIX', level=1)
    doc.add_heading('A. Task Prompt:', level=2)
    doc.add_paragraph(topic)
    doc.add_heading('B. Original Essay:', level=2)
    doc.add_paragraph(original_essay)
    doc.add_heading('C. Annotated Version:', level=2)
    clean_annotated = re.sub(r'<[^>]+>', '', data.get("annotatedEssay", "") or "")
    doc.add_paragraph(clean_annotated)

    # D. PROJECTED SCORE
    doc.add_heading('D. PROJECTED BAND SCORE (AFTER REVISION)', level=2)
    rev_scores = data.get("revisedScore")
    if rev_scores:
        table = doc.add_table(rows=2, cols=5)
        table.style = 'Table Grid'
        vals = [
            str(rev_scores.get('task_achievement', '-')),
            str(rev_scores.get('cohesion_coherence', '-')),
            str(rev_scores.get('lexical_resource', '-')),
            str(rev_scores.get('grammatical_range', '-')),
            str(rev_scores.get('overall', '-'))
        ]
        # Header
        for i, h in enumerate(['Task Achievement', 'Coherence', 'Lexical Resource', 'Grammar', 'OVERALL']):
            cell = table.cell(0, i)
            cell.text = h
            cell.paragraphs[0].runs[0].bold = True
            cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0, 100, 0)
        # Value
        for i, v in enumerate(vals):
            table.cell(1, i).text = v
            
        if rev_scores.get('logic_re_evaluation'):
            p = doc.add_paragraph()
            run = p.add_run(f"\nExaminer's Note: {rev_scores['logic_re_evaluation']}")
            run.font.italic = True
            run.font.color.rgb = RGBColor(0, 128, 0)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# HÀM TẠO FILE PDF
def create_pdf(data, topic, original_essay, analysis_text):
    # 1. Đăng ký Font
    has_font = register_vietnamese_font()
    font_name = 'Roboto' if has_font else 'Helvetica'
    font_bold = 'Roboto-Bold' if has_font else 'Helvetica-Bold'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    # 2. Lấy Styles
    styles = getSampleStyleSheet()
    
    # 3. Cập nhật Font
    styles['Title'].fontName = font_name
    styles['Title'].fontSize = 18
    styles['Heading1'].fontName = font_bold
    styles['Heading2'].fontName = font_bold
    styles['Normal'].fontName = font_name
    styles['Normal'].fontSize = 13
    
    h1_style = styles['Heading1']
    h2_style = styles['Heading2']
    normal_style = styles['Normal']
    
    elements = []

    # Title
    elements.append(Paragraph("IELTS WRITING ASSESSMENT REPORT", styles['Title']))
    elements.append(Spacer(1, 12))

    # 1. BAND SCORE
    elements.append(Paragraph("1. BAND SCORE", h1_style))
    scores = data.get("originalScore")
    
    if scores and isinstance(scores, dict) and scores.get('overall', '-') != '-':
        data_table = [
            ['TA', 'CC', 'LR', 'GRA', 'OVERALL'],
            [
                str(scores.get('task_achievement', '-')),
                str(scores.get('cohesion_coherence', '-')),
                str(scores.get('lexical_resource', '-')),
                str(scores.get('grammatical_range', '-')),
                str(scores.get('overall', '-'))
            ]
        ]
        t = Table(data_table, colWidths=[60, 60, 60, 60, 80])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkred),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), font_name) 
        ]))
        elements.append(t)
    else:
        elements.append(Paragraph("Original score data not found.", normal_style))
    
    elements.append(Spacer(1, 12))

    # 2. ANALYSIS
    elements.append(Paragraph("2. DETAILED ANALYSIS", h1_style))
    if analysis_text:
        safe_text = html.escape(analysis_text).replace('\n', '<br/>').replace('**', '').replace('###', '')
        elements.append(Paragraph(safe_text, normal_style))
    else:
        elements.append(Paragraph("No detailed analysis available.", normal_style))
    elements.append(Spacer(1, 12))

    # 3. ERRORS
    elements.append(Paragraph("3. ERROR LOG", h1_style))
    if data.get("errors"):
        for err in data['errors']:
            cat = html.escape(str(err.get('category', '')))
            typ = html.escape(str(err.get('type', '')))
            orig = html.escape(str(err.get('original', '')))
            fix = html.escape(str(err.get('correction', '')))
            text = f"<b>[{cat}] {typ}</b><br/>Original: <strike>{orig}</strike> -> Fix: <b>{fix}</b>"
            elements.append(Paragraph(text, normal_style))
            elements.append(Spacer(1, 6))

    # APPENDIX
    elements.append(PageBreak())
    elements.append(Paragraph("APPENDIX", h1_style))
    
    elements.append(Paragraph("<b>A. Task Prompt:</b>", h2_style))
    elements.append(Paragraph(html.escape(topic).replace('\n', '<br/>'), normal_style))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph("<b>B. Original Essay:</b>", h2_style))
    elements.append(Paragraph(html.escape(original_essay).replace('\n', '<br/>'), normal_style))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>C. Annotated Version:</b>", h2_style))
    clean_annotated = re.sub(r'<[^>]+>', '', data.get("annotatedEssay", "") or "")
    elements.append(Paragraph(html.escape(clean_annotated).replace('\n', '<br/>'), normal_style))
    elements.append(Spacer(1, 10))

    # D. PROJECTED
    elements.append(Paragraph("<b>D. PROJECTED BAND SCORE (AFTER REVISION):</b>", h2_style))
    rev_scores = data.get("revisedScore")
    if rev_scores:
        rev_table_data = [
            ['TA', 'CC', 'LR', 'GRA', 'OVERALL'],
            [
                str(rev_scores.get('task_achievement', '-')),
                str(rev_scores.get('cohesion_coherence', '-')),
                str(rev_scores.get('lexical_resource', '-')),
                str(rev_scores.get('grammatical_range', '-')),
                str(rev_scores.get('overall', '-'))
            ]
        ]
        t2 = Table(rev_table_data, colWidths=[60, 60, 60, 60, 80])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, -1), font_name)
        ]))
        elements.append(t2)
        
        if rev_scores.get('logic_re_evaluation'):
            safe_note = html.escape(rev_scores['logic_re_evaluation'])
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<i>Examiner's Note: {safe_note}</i>", normal_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
    
# ==========================================
# 4. GIAO DIỆN CHÍNH (UI)
# ==========================================
import textwrap

# HEADER (Thanh tiêu đề và nút xóa)
c1, c2 = st.columns([3, 1])
with c1:
    st.markdown("""
        <div style="display: flex; flex-direction: column; justify-content: center;">
            <h1 style="margin-bottom: 5px; line-height: 0.2rem;">
                IELTS Examiner <span class='pro-badge'>Pro</span>
            </h1>
            <div>
                <span class='verified-badge' style="margin-left: 2px;">
                    🛡️ BC CERTIFIED EXPERT
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)
with c2:
    if st.button("🗑️ Clear Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.submitted = False 
        st.rerun()

if "submitted" not in st.session_state:
    st.session_state.submitted = False

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "ai",
            "content": """
<div style="font-family: 'Inter', sans-serif; color: #1F2937; line-height: 1.4; font-size: 16px; max-width: 850px;">
    <h3 style="color: #D40E14; font-family: 'Merriweather', serif; margin-top: 0; margin-bottom: 15px; font-size: 22px; border-bottom: 3px solid #D40E14; display: inline-block; padding-bottom: 5px;">
        Welcome to the Official Task 1 Assessment Room.
    </h3>
    <p style="margin-bottom: 13px;">
        This system provides expert-level evaluation of <b>IELTS Academic Task 1 reports</b>, based on the official IELTS band descriptors.
    </p>
    <p style="margin-bottom: 13px;">
        The assessment focuses on objective, criteria-based feedback to help you understand your current writing level and areas for improvement.
    </p>
    <div style="background-color: #F8FAFC; border-radius: 8px; padding: 15px 20px; border-left: 5px solid #D40E14; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
        <p style="margin-bottom: 10px; font-weight: 800; font-size: 13px; color: #111827; text-transform: uppercase; letter-spacing: 1px;">
            Guidelines for a valid submission:
        </p>
        <div style="color: #374151;">
            <div style="margin-bottom: 6px;">• <b>Task Prompt:</b> Provide the original question or instruction.</div>
            <div style="margin-bottom: 6px;">• <b>Visual Data:</b> Upload a clear image of the chart, graph, table, or diagram.</div>
            <div>• <b>Written Report:</b> Paste your complete response (at least <b>150 words</b> to avoid penalties).</div>
        </div>
    </div>
</div>
""",
            "data": None
        }
    ]

# HIỂN THỊ LỊCH SỬ CHAT VÀ KẾT QUẢ CHẤM ĐIỂM
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="👨‍🏫" if msg["role"] == "ai" else "👤"):
        if msg["role"] == "user":
            if msg.get("topic"):
                st.markdown(f"**📝 Task Prompt:**\n> {msg['topic']}")
            if msg.get("image"):
                st.image(msg["image"], caption="Visual Resource Attached", width=400)
            st.write(msg["content"])
        else:
            # 1. PHẦN MARKDOWN CHÍNH (Báo cáo tổng quan)
            st.markdown(msg["content"], unsafe_allow_html=True)  
            
            # 2. HIỂN THỊ LỖI CHI TIẾT (Chia làm 2 phần)
            if msg.get("data") and msg["data"]["errors"]:
                all_errors = msg["data"]["errors"]
                
                # --- LỌC LỖI ---
                micro_errors = [e for e in all_errors if e.get('category') in ['Grammar', 'Vocabulary']]
                macro_errors = [e for e in all_errors if e.get('category') not in ['Grammar', 'Vocabulary']]

                # --- PHẦN 1: GRAMMAR & VOCABULARY ---
                if micro_errors:
                    with st.expander(f"🚩 Grammar & Vocabulary Corrections ({len(micro_errors)} Issues)", expanded=True):
                        for idx, err in enumerate(micro_errors):
                            cat = err.get('category', 'Grammar')
                            badge_style = "background:#DCFCE7; color:#166534; border:1px solid #86EFAC" if cat == 'Grammar' else "background:#FEF9C3; color:#854D0E; border:1px solid #FCD34D"
                            impact = err.get('impact_level', 'Low').upper()
                            
                            html_micro = textwrap.dedent(f"""
                            <div class="error-card" style="margin-bottom:12px;">
                                <div class="error-header" style="display:flex; justify-content:space-between; border-bottom:1px solid #eee; padding-bottom:4px; margin-bottom:4px;">
                                    <div style="display:flex; align-items:center;">
                                        <span style="background:#F3F4F6; width:24px; height:24px; display:inline-flex; align-items:center; justify-content:center; border-radius:50%; font-size:14px; font-weight:bold; margin-right:8px;">{idx + 1}</span>
                                        <span style="{badge_style}; padding: 2px 8px; border-radius: 6px; font-size: 12px; font-weight: 800; text-transform: uppercase;">{cat}</span>
                                        <span style="font-weight:700; font-size:16px; margin-left:10px; color:#1F2937;">{err['type']}</span>
                                    </div>
                                    <span style="background:#F3F4F6; color:#666; padding:2px 8px; border-radius:6px; font-size:11px; font-weight:bold;">{impact}</span>
                                </div>
                                <div style="background:#F9FAFB; padding:10px; border-radius:6px; font-size:15px; line-height: 1.5;">
                                    <div style="margin-bottom:4px;">
                                        <span style="color:#6B7280; font-size:11px; font-weight:800; letter-spacing: 0.5px;">ORIGINAL:</span> 
                                        <span style="text-decoration:line-through; color:#9CA3AF; margin-left: 6px;">{err['original']}</span>
                                    </div>
                                    <div>
                                        <span style="color:#6B7280; font-size:11px; font-weight:800; letter-spacing: 0.5px;">FIX:</span> 
                                        <span style="{badge_style}; padding:1px 6px; border-radius:4px; font-weight:bold; margin-left: 6px; color:#111;">{err['correction']}</span>
                                    </div>
                                </div>
                                <div style="font-size:14px; color:#4B5563; margin-top:6px; font-style: italic;">
                                    Note: {err['explanation']}
                                </div>
                            </div>
                            """).strip()
                            st.markdown(html_micro, unsafe_allow_html=True)
                            
                # --- PHẦN 2: COHERENCE & COHESION ---
                if macro_errors:
                    st.markdown("---") 
                    st.markdown(f"#### 💡 Coherence & Cohesion Improvements ({len(macro_errors)} Issues)")
                    with st.expander("Xem chi tiết các lỗi Tư duy & Mạch lạc", expanded=True):
                        for idx, err in enumerate(macro_errors):
                            badge_style = "background:#DBEAFE; color:#1E40AF; border:1px solid #BFDBFE"
                            impact = err.get('impact_level', 'Low').upper()
                            html_macro = textwrap.dedent(f"""...""") # Dùng textwrap.dedent
                            st.markdown(html_macro, unsafe_allow_html=True)
                else:
                    structure_breakers = ['Fragment', 'Run-on Sentence', 'Comma Splice', 'Sentence Structure']
                    has_structure_error = any(e.get('type') in structure_breakers for e in all_errors)

                    st.markdown("---")
                    st.markdown("#### 💡 Coherence & Cohesion Review")
                    
                    if has_structure_error:
                        st.warning("⚠️ **Lưu ý:** Mặc dù không có lỗi logic lớn, nhưng các lỗi cấu trúc câu (Fragment/Run-on) ở phần Ngữ pháp phía trên đang gây ảnh hưởng xấu đến sự mạch lạc của bài viết.")
                    else:
                        st.success("✅ **Tuyệt vời!** Bài viết có cấu trúc mạch lạc, các ý được liên kết tốt và không phát hiện lỗi logic nghiêm trọng.")

            # --- [ĐOẠN ĐÃ ĐƯỢC SỬA] - Thụt vào trong khối "else" ---
            # 3. Phần Annotated Essay (Bài viết đã sửa)
            if msg.get("data") and msg["data"].get("annotatedEssay"):
                st.markdown("### 📝 Examiner's Annotated Report")
                st.caption("The essay has been corrected (strikethrough = incorrect, highlighted = corrected)")
                st.markdown(f'<div class="annotated-text">{msg["data"]["annotatedEssay"]}</div>', unsafe_allow_html=True)
            
            # 4. Bảng điểm chấm lại (Revised Score)
            if msg.get("data") and msg["data"].get("revisedScore"):
                scores = msg["data"]["revisedScore"]
                
                st.markdown("### 📊 Projected Band (Revised Version)")
                
                if float(str(scores.get('overall', 0)).replace('-', '0')) >= 8.5:
                    st.success("✨ Bản sửa lỗi này đã đạt mức tiệm cận hoàn hảo.")
                else:
                    st.warning(f"⚠️ **Lưu ý của Giám khảo:** Bản sửa lỗi này vẫn chỉ đạt {scores.get('overall')} vì: {scores.get('logic_re_evaluation', 'vẫn chưa đạt độ súc tích tuyệt đối của Band 9.0')}")

                cols = st.columns(5)
                cols[0].metric("TA", scores.get("task_achievement", "-"))
                cols[1].metric("CC", scores.get("cohesion_coherence", "-"))
                cols[2].metric("LR", scores.get("lexical_resource", "-"))
                cols[3].metric("GRA", scores.get("grammatical_range", "-"))
                cols[4].metric("OVERALL", scores.get("overall", "-"))
                
                # --- KHU VỰC NÚT TẢI VỀ ---
                st.markdown("---")
                st.markdown("### 📥 Download Report")
                
                topic_text = msg.get("topic", "")
                essay_text = msg.get("original_essay", "")
                analysis_text = msg.get("content", "")
                
                if not topic_text:
                    try:
                        prev_msg_index = st.session_state.messages.index(msg) - 1
                        if prev_msg_index >= 0:
                            prev_msg = st.session_state.messages[prev_msg_index]
                            topic_text = prev_msg.get("topic", "Topic not found")
                            essay_text = prev_msg.get("content", "Essay not found")
                    except:
                        pass

                d1, d2 = st.columns(2)
                
                docx_file = create_docx(msg["data"], topic_text, essay_text, analysis_text)
                d1.download_button(...)
                
                pdf_file = create_pdf(msg["data"], topic_text, essay_text, analysis_text)
                d2.download_button(...)
# ==========================================
# 5. KHU VỰC NHẬP LIỆU & XỬ LÝ AI (ẨN KHI XONG)
# ==========================================

# Chỉ hiển thị nếu chưa nộp bài
if not st.session_state.submitted:
    st.markdown("---")
    with st.container():
        # Bố cục bất đối xứng: Cột trái 1.3 - Cột phải 2.7
        col_left, col_right = st.columns([1.3, 2.7], gap="large")
        
        with col_left:
            st.markdown("<p style='font-weight: 700; font-size: 15px; color: #1F2937;'>📝 TASK 1 QUESTION / PROMPT</p>", unsafe_allow_html=True)
            topic_input = st.text_area("topic_label", label_visibility="collapsed", height=280, placeholder="Paste the official question text here...")
            
            st.markdown("<div style='margin-top: 25px;'></div>", unsafe_allow_html=True)
            st.markdown("<p style='font-weight: 700; font-size: 15px; color: #1F2937;'>📊 VISUAL DATA</p>", unsafe_allow_html=True)
            uploaded_file = st.file_uploader("file_label", label_visibility="collapsed", type=['png', 'jpg', 'jpeg'])
            
        with col_right:
            st.markdown("<p style='font-weight: 700; font-size: 15px; color: #1F2937;'>✍️ YOUR WRITTEN REPORT</p>", unsafe_allow_html=True)
            essay_input = st.text_area("essay_label", label_visibility="collapsed", height=515, placeholder="Type or paste your response here (aim for 150+ words)...")

        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        submit_btn = st.button("🚀 SUBMIT FOR ASSESSMENT", type="primary", use_container_width=True)

        if submit_btn:
            # KIỂM TRA BẮT BUỘC NHẬP ĐỦ 3 THÔNG TIN
            if not topic_input.strip():
                st.warning("⚠️ Bắt buộc: Vui lòng nhập đề bài (Task Prompt) trước khi chấm điểm!")
            elif uploaded_file is None:
                st.warning("⚠️ Bắt buộc: Vui lòng tải lên hình ảnh biểu đồ (Visual Data) để Giám khảo đối chiếu số liệu!")
            elif not essay_input.strip() or len(essay_input.strip()) < 10:
                st.warning("⚠️ Bắt buộc: Vui lòng nhập nội dung bài làm (ít nhất 10 ký tự)!")
            else:
                # NẾU ĐÃ NHẬP ĐỦ, BẮT ĐẦU QUY TRÌNH CHẤM ĐIỂM
                loading_steps = [
                    "🕵️ INITIAL VALIDATION: IDENTIFYING EXAM CONTEXT AND ENFORCING WORD COUNT CONSTRAINTS...",
                    "🔍 EXHAUSTIVE ERROR SCANNING: CONDUCTING SENTENCE-BY-SENTENCE REVIEW FOR ALL ERRORS...",
                    "📊 DEEP CRITERIA ANALYSIS: EVALUATING TA, CC, LR, AND GRA STANDARDS WITH CEILING SCORES...",
                    "🧮 SCORE CALCULATION: DETERMINING COMPONENT BANDS AND APPLYING IELTS ROUNDING RULES...",
                    "⚖️ CONSISTENCY CHECK: CROSS-REFERENCING ASSIGNED SCORES WITH ERROR LOG FOR LOGICAL ACCURACY...",
                    "📝 OUTPUT GENERATION: COMPILING DETAILED ANALYSIS AND PRODUCING ANNOTATED ESSAY DATA..."
                ]
                
                status_container = st.status("👨‍🏫 Senior Examiner is starting assessment...", expanded=True)
                progress_bar = status_container.progress(0)
                
                try:
                    # 1. Xử lý hình ảnh
                    image_part = Image.open(uploaded_file)
                    
                    # 2. Ghép Prompt
                    full_prompt = GRADING_PROMPT_TEMPLATE.replace('{{TOPIC}}', topic_input).replace('{{ESSAY}}', essay_input)
                    
                    # 3. Gọi AI
                    response, used_model = generate_content_with_failover(full_prompt, image_part)
                    
                    # 4. Chạy hiệu ứng Loading
                    for i, text in enumerate(loading_steps):
                        status_container.write(text)
                        progress_bar.progress(int((i + 1) * (100 / len(loading_steps))))
                        time.sleep(2.8) 
                    
                    if response:
                        markdown_text, parsed_data = process_response(response.text)
                        st.session_state.messages.append({"role": "user", "content": essay_input, "topic": topic_input, "image": uploaded_file})
                        st.session_state.messages.append({"role": "ai", "content": markdown_text, "data": parsed_data, "model_version": used_model})
                        st.session_state.submitted = True
                        status_container.update(label="✅ ASSESSMENT COMPLETE!", state="complete", expanded=False)
                        st.rerun()
                        
                except Exception as e:
                    status_container.update(label="❌ Error occurred!", state="error")
                    st.error(f"Lỗi hệ thống: {e}")
# Footer
st.markdown("---")
st.caption("Developed by Albert Nguyen - v20251228.")


















