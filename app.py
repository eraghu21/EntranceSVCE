import streamlit as st
import requests
import random

API = "https://script.google.com/macros/s/AKfycbx7zUH73IqzqfyxBSdHjM4yIzJttGXiKZIenZyuGqwDIAG1scI9U5SF9Z4S3PYwOE1WhA/exec"

st.set_page_config(page_title="Entrance Exam", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

if "answers" not in st.session_state:
    st.session_state.answers = {}

if "mark_review" not in st.session_state:
    st.session_state.mark_review = set()

# ---------------- LOGIN ----------------
if not st.session_state.user:
    st.title("🎓 Entrance Exam Login")

    app_no = st.text_input("Application Number")
    password = st.text_input("Mobile Number", type="password")

    if st.button("Login"):
        res = requests.get(API, params={
            "action": "login",
            "app_no": app_no,
            "password": password
        }).json()

        if res.get("status") == "success":
            st.session_state.user = res
            st.rerun()
        else:
            st.error("Invalid login")

    st.stop()

# ---------------- FETCH QUESTIONS ----------------
@st.cache_data
def load_questions():
    data = requests.get(API, params={"action":"questions"}).json()
    random.shuffle(data)

    for q in data:
        opts = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
        correct = q[q["correct"]]
        random.shuffle(opts)
        q["shuffled"] = opts
        q["new_correct"] = opts.index(correct)
    return data

questions = load_questions()

# ---------------- SIDEBAR PALETTE ----------------
st.sidebar.title("Question Palette")

sections = ["All","Physics","Chemistry","Maths"]
filter_sec = st.sidebar.selectbox("Section Filter", sections)

filtered = [i for i,q in enumerate(questions) if filter_sec=="All" or q["section"]==filter_sec]

for i in filtered:
    qid = questions[i]["id"]
    if qid in st.session_state.answers:
        label = f"✅ {qid}"
    elif qid in st.session_state.mark_review:
        label = f"⚠️ {qid}"
    else:
        label = f"{qid}"
    if st.sidebar.button(label):
        st.session_state.q_index = i

# ---------------- MAIN EXAM ----------------
if "q_index" not in st.session_state:
    st.session_state.q_index = 0

q = questions[st.session_state.q_index]

st.title("Online Entrance Exam")
st.subheader(f"Welcome: {st.session_state.user['name']}")

with st.expander("📜 Instructions"):
    st.write("""
    - Each question has one correct answer  
    - Use palette to navigate  
    - You may mark questions for review  
    - No score will be shown after submission  
    """)

st.markdown(f"### {q['section']} - Question {st.session_state.q_index+1}")
st.write(q["question"])

choice = st.radio(
    "Choose answer",
    q["shuffled"],
    index = st.session_state.answers.get(q["id"], -1)
)

if st.button("Save Answer"):
    st.session_state.answers[q["id"]] = q["shuffled"].index(choice)
    st.success("Saved")

if st.button("Mark for Review"):
    st.session_state.mark_review.add(q["id"])
    st.warning("Marked for review")

col1,col2 = st.columns(2)
with col1:
    if st.button("Previous"):
        st.session_state.q_index = max(0, st.session_state.q_index-1)
        st.rerun()

with col2:
    if st.button("Next"):
        st.session_state.q_index = min(len(questions)-1, st.session_state.q_index+1)
        st.rerun()

# ---------------- SUBMIT ----------------
if st.button("Submit Exam"):
    payload = {
        "app_no": st.session_state.user["app_no"],
        "name": st.session_state.user["name"],
        "answers": st.session_state.answers
    }

    r = requests.post(API, json=payload)

    if r.status_code == 200:
        st.success("Exam submitted successfully.")
        st.stop()
    else:
        st.error("Submission failed")
