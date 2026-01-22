import streamlit as st
import requests
import pandas as pd
import random
import time

API = "https://script.google.com/a/macros/svce.ac.in/s/AKfycby6z48bgJxUfTLRoqv-4vbGUUa8WRb9TgAj0TniGN33ntvFNQ2SgmEoFgGn2zfKoNGWgg/exec"
EXAM_DURATION = 10*60  # 10 min

st.set_page_config(page_title="Entrance Exam", layout="wide")

if "page" not in st.session_state: st.session_state.page="login"
if "answers" not in st.session_state: st.session_state.answers={}
if "marks_for_review" not in st.session_state: st.session_state.marks_for_review={}
if "start_time" not in st.session_state: st.session_state.start_time=None
if "random_options" not in st.session_state: st.session_state.random_options=[]

# ---------------- LOGIN ----------------
if st.session_state.page=="login":
    st.title("🎓 Entrance Exam Portal")
    app_no = st.text_input("Application Number")
    password = st.text_input("Mobile (Password)", type="password")
    if st.button("Login"):
        try:
            res = requests.get(API, params={"action":"login","app_no":app_no,"password":password})
            data = res.json()
        except:
            st.error(f"Invalid server response: {res.text}")
            st.stop()
        if data.get("status")=="success":
            st.session_state.user = data
            st.session_state.page="instructions"
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

# ---------------- INSTRUCTIONS ----------------
elif st.session_state.page=="instructions":
    user = st.session_state.user
    st.sidebar.success(f"{user['name']} ({user['app_no']})")
    st.title("📌 Exam Instructions")
    st.info("3 Sections: Physics, Chemistry, Maths\nTimer enabled\nMark for Review available")
    if st.button("Start Exam"):
        qdata = requests.get(API, params={"action":"questions"}).json()
        df = pd.DataFrame(qdata).sample(frac=1, random_state=int(time.time())).reset_index(drop=True)
        shuffled_options=[]
        for _, row in df.iterrows():
            opts = ["option_a","option_b","option_c","option_d"]
            random.shuffle(opts)
            shuffled_options.append({
                "question": row["question"],
                "section": row["section"],
                "options": {o: row[o] for o in opts},
                "correct": row[row["correct"]]
            })
        st.session_state.random_options = shuffled_options
        st.session_state.start_time = time.time()
        st.session_state.page="exam"
        st.experimental_rerun()

# ---------------- EXAM PAGE ----------------
elif st.session_state.page=="exam":
    user = st.session_state.user
    elapsed = int(time.time()-st.session_state.start_time)
    remaining = EXAM_DURATION-elapsed
    if remaining<=0: st.session_state.auto_submit=True; remaining=0
    mins, secs = divmod(remaining,60)
    st.sidebar.metric("⏳ Time Left", f"{mins:02}:{secs:02}")
    st.sidebar.title("👤 Profile")
    st.sidebar.write("Name:", user["name"])
    st.sidebar.write("App No:", user["app_no"])
    sections=["All","Physics","Chemistry","Maths"]
    selected_section = st.sidebar.selectbox("Filter Section", sections)

    st.sidebar.subheader("Question Palette")
    total_questions=len(st.session_state.random_options)
    for i,q in enumerate(st.session_state.random_options):
        if selected_section!="All" and q["section"]!=selected_section: continue
        if i in st.session_state.marks_for_review: lbl=f"{i+1} 🔶"
        elif i not in st.session_state.answers: lbl=f"{i+1} ⚪"
        else: lbl=f"{i+1} ✅"
        if st.sidebar.button(lbl,key=f"qbtn_{i}"): st.session_state.current_q=i

    st.sidebar.write(f"Unanswered: {total_questions-len(st.session_state.answers)}")
    st.sidebar.write(f"Marked for Review: {len(st.session_state.marks_for_review)}")

    current_q=st.session_state.get("current_q",0)
    q=st.session_state.random_options[current_q]
    st.write(f"**Q{current_q+1} [{q['section']}]**: {q['question']}")
    opts=list(q["options"].values())
    sel = st.radio("Select Answer:", opts, index=opts.index(st.session_state.answers.get(current_q, opts[0])) if current_q in st.session_state.answers else 0)
    st.session_state.answers[current_q]=sel

    if current_q in st.session_state.marks_for_review:
        if st.button("Remove Mark for Review"): del st.session_state.marks_for_review[current_q]
    else:
        if st.button("Mark for Review"): st.session_state.marks_for_review[current_q]=True

    col1,col2,col3=st.columns([1,1,1])
    with col1: 
        if st.button("Previous") and current_q>0: st.session_state.current_q-=1; st.experimental_rerun()
    with col3:
        if st.button("Next") and current_q<total_questions-1: st.session_state.current_q+=1; st.experimental_rerun()

    def submit_exam():
        score={"Physics":0,"Chemistry":0,"Maths":0}
        for i,q in enumerate(st.session_state.random_options):
            ans=st.session_state.answers.get(i)
            if ans==q["correct"]: score[q["section"]]+=1
        payload={
            "app_no": user["app_no"],
            "name": user["name"],
            "physics": score["Physics"],
            "chemistry": score["Chemistry"],
            "maths": score["Maths"],
            "total": sum(score.values())
        }
        requests.post(API,json=payload)
        st.success("✅ Exam Submitted Successfully!")
        st.balloons()
        st.stop()

    if st.button("Submit Exam") or st.session_state.auto_submit: submit_exam()
