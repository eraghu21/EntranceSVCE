import streamlit as st
import requests
import pandas as pd
import time
import random

API = "YOUR_EXEC_URL_HERE"
EXAM_DURATION = 10*60  # 10 minutes

st.set_page_config(page_title="Entrance Exam", layout="wide")

# ---------------- SESSION ----------------
if "page" not in st.session_state:
    st.session_state.page = "login"
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "marks_for_review" not in st.session_state:
    st.session_state.marks_for_review = {}
if "start_time" not in st.session_state:
    st.session_state.start_time = None
if "auto_submit" not in st.session_state:
    st.session_state.auto_submit = False
if "random_options" not in st.session_state:
    st.session_state.random_options = []

# ---------------- LOGIN ----------------
if st.session_state.page == "login":
    st.title("🎓 Entrance Exam Portal")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.subheader("Login")
        app_no = st.text_input("Application Number")
        password = st.text_input("Mobile (Password)", type="password")
        if st.button("Login"):
            res = requests.get(API, params={
                "action": "login",
                "app_no": app_no,
                "password": password
            }).json()
            if res.get("status") == "success":
                st.session_state.user = res
                st.session_state.page = "instructions" if not res.get("is_admin") else "admin"
                st.rerun()
            else:
                st.error("Invalid credentials")

# ---------------- STUDENT INSTRUCTIONS ----------------
elif st.session_state.page == "instructions":
    user = st.session_state.user
    st.sidebar.success(f"{user['name']} ({user['app_no']})")
    st.title("📌 Exam Instructions")
    st.info("""
    • 3 Sections: Physics, Chemistry, Maths  
    • Each question carries 1 mark  
    • No negative marking  
    • Timer enabled  
    • Do not refresh  
    • One attempt only  
    • You can mark questions for review
    """)
    if st.button("Start Exam"):
        # Fetch questions and shuffle order
        qdata = requests.get(API, params={"action": "questions"}).json()
        df = pd.DataFrame(qdata)
        df = df.sample(frac=1, random_state=int(time.time())).reset_index(drop=True)
        
        # Shuffle options
        shuffled_options = []
        for _, row in df.iterrows():
            options = ["option_a","option_b","option_c","option_d"]
            random.shuffle(options)
            shuffled_options.append({
                "question": row["question"],
                "section": row["section"],
                "options": {o: row[o] for o in options},
                "correct": row[row["correct"]]
            })
        st.session_state.random_options = shuffled_options
        st.session_state.start_time = time.time()
        st.session_state.page = "exam"
        st.rerun()

# ---------------- EXAM PAGE ----------------
elif st.session_state.page == "exam":
    user = st.session_state.user

    # Timer
    elapsed = int(time.time() - st.session_state.start_time)
    remaining = EXAM_DURATION - elapsed
    if remaining <= 0:
        st.warning("⏰ Time Over. Auto submitting...")
        st.session_state.auto_submit = True
        remaining = 0
    mins, secs = divmod(remaining, 60)
    st.sidebar.metric("⏳ Time Left", f"{mins:02}:{secs:02}")

    # Sidebar profile
    st.sidebar.title("👤 Profile")
    st.sidebar.write("Name:", user["name"])
    st.sidebar.write("App No:", user["app_no"])

    # Sidebar Section Filter
    sections = ["All", "Physics", "Chemistry", "Maths"]
    selected_section = st.sidebar.selectbox("Filter Section", sections)

    # Question Palette
    st.sidebar.subheader("Question Palette")

    total_questions = len(st.session_state.random_options)
    for i, q in enumerate(st.session_state.random_options):
        if selected_section != "All" and q["section"] != selected_section:
            continue

        # Determine button color and icon
        if i in st.session_state.marks_for_review:
            btn_label = f"{i+1} 🔶"
        elif i not in st.session_state.answers:
            btn_label = f"{i+1} ⚪"
        else:
            btn_label = f"{i+1} ✅"

        if st.sidebar.button(btn_label, key=f"qbtn_{i}"):
            st.session_state.current_q = i

    # Unanswered / Review count
    unanswered_count = total_questions - len(st.session_state.answers)
    review_count = len(st.session_state.marks_for_review)
    st.sidebar.write(f"Unanswered: {unanswered_count}")
    st.sidebar.write(f"Marked for Review: {review_count}")

    # Current Question
    current_q = st.session_state.get("current_q", 0)
    q = st.session_state.random_options[current_q]

    st.write(f"**Q{current_q+1} [{q['section']}]**: {q['question']}")
    options_list = list(q["options"].values())
    selected = st.radio(
        "Select Answer:",
        options_list,
        index=options_list.index(st.session_state.answers.get(current_q, options_list[0])) if current_q in st.session_state.answers else 0
    )
    st.session_state.answers[current_q] = selected

    # Mark for Review
    if current_q in st.session_state.marks_for_review:
        if st.button("Remove Mark for Review"):
            del st.session_state.marks_for_review[current_q]
    else:
        if st.button("Mark for Review"):
            st.session_state.marks_for_review[current_q] = True

    # Navigation
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("Previous") and current_q > 0:
            st.session_state.current_q -= 1
            st.rerun()
    with col3:
        if st.button("Next") and current_q < total_questions - 1:
            st.session_state.current_q += 1
            st.rerun()

    # Submit Exam
    def submit_exam():
        # Send answers to backend, no scoring shown
        score = {"Physics":0,"Chemistry":0,"Maths":0}
        for i, q in enumerate(st.session_state.random_options):
            ans = st.session_state.answers.get(i)
            if ans == q["correct"]:
                score[q["section"]] += 1
        payload = {
            "app_no": user["app_no"],
            "name": user["name"],
            "physics": score["Physics"],
            "chemistry": score["Chemistry"],
            "maths": score["Maths"],
            "total": sum(score.values())
        }
        res = requests.post(API, json=payload).json()
        if res["status"] == "already_submitted":
            st.error("❌ Already Submitted")
        else:
            st.success("✅ Exam Submitted Successfully!")
            st.balloons()
        st.stop()

    if st.button("Submit Exam") or st.session_state.auto_submit:
        submit_exam()
