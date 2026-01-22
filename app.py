import streamlit as st
import requests
import random
import json

# ---------------- CONFIG ----------------
API = "PASTE_YOUR_WEBAPP_URL_HERE"  # <-- replace with your Apps Script Web App URL

st.set_page_config(page_title="Entrance Exam", layout="wide")

# ---------------- SESSION STATE ----------------
def init_state():
    defaults = {
        "user": None,
        "questions": None,
        "q_index": 0,
        "answers": {},
        "mark_review": set(),
        "submitted": False
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ---------------- HELPERS ----------------
def api_get(params):
    try:
        r = requests.get(API, params=params, timeout=10)
        return r.json()
    except Exception as e:
        st.error("Backend not returning JSON. Check deployment & URL.")
        st.code(str(e))
        st.stop()


def api_post(payload):
    try:
        r = requests.post(API, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        st.error("Submit failed. Backend issue.")
        st.code(str(e))
        st.stop()


def load_questions():
    data = api_get({"action": "questions"})

    random.shuffle(data)

    for q in data:
        options = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
        correct_text = q[q["correct"]]
        random.shuffle(options)

        q["shuffled"] = options
        q["correct_index"] = options.index(correct_text)

    return data


# ---------------- LOGIN PAGE ----------------
if not st.session_state.user:
    st.title("🎓 Entrance Exam Login")

    app_no = st.text_input("Application Number")
    password = st.text_input("Mobile Number (Password)", type="password")

    if st.button("Login"):
        res = api_get({
            "action": "login",
            "app_no": app_no,
            "password": password
        })

        if res.get("status") == "success":
            st.session_state.user = res
            st.session_state.questions = load_questions()
            st.success("Login successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.stop()

# ---------------- LOAD QUESTIONS ----------------
questions = st.session_state.questions

# ---------------- SIDEBAR PALETTE ----------------
st.sidebar.title("📌 Question Palette")

sections = ["All", "Physics", "Chemistry", "Maths"]
filter_sec = st.sidebar.selectbox("Filter by Section", sections)

for i, q in enumerate(questions):
    if filter_sec != "All" and q["section"] != filter_sec:
        continue

    qid = q["id"]

    if qid in st.session_state.answers:
        label = f"✅ {qid}"
    elif qid in st.session_state.mark_review:
        label = f"⚠️ {qid}"
    else:
        label = qid

    if st.sidebar.button(label):
        st.session_state.q_index = i
        st.rerun()

# ---------------- MAIN EXAM ----------------
q = questions[st.session_state.q_index]

st.title("Online Entrance Examination")
st.subheader(f"Candidate: {st.session_state.user['name']}")

with st.expander("📜 Exam Instructions"):
    st.markdown("""
    - Each question has one correct answer
    - Use palette to navigate questions
    - You can mark questions for review
    - No score will be shown after submission
    - Do not refresh after submission
    """)

st.markdown(f"### {q['section']} — Question {st.session_state.q_index + 1}")
st.write(q["question"])

# ---------------- OPTIONS ----------------
prev = st.session_state.answers.get(q["id"])

if prev is None:
    choice = st.radio("Choose answer", q["shuffled"])
else:
    choice = st.radio("Choose answer", q["shuffled"], index=prev)

# ---------------- BUTTONS ----------------
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("Save Answer"):
        st.session_state.answers[q["id"]] = q["shuffled"].index(choice)
        st.success("Answer saved")

with col2:
    if st.button("Mark for Review"):
        st.session_state.mark_review.add(q["id"])
        st.warning("Marked for review")

with col3:
    if st.button("Clear Response"):
        st.session_state.answers.pop(q["id"], None)
        st.rerun()

with col4:
    if st.button("Next Question"):
        st.session_state.q_index = min(len(questions)-1, st.session_state.q_index + 1)
        st.rerun()

# ---------------- SUBMIT ----------------
st.divider()

if st.button("🚨 Submit Exam"):
    payload = {
        "app_no": st.session_state.user["app_no"],
        "name": st.session_state.user["name"],
        "answers": st.session_state.answers
    }

    res = api_post(payload)

    if res.get("status") == "saved":
        st.success("Exam submitted successfully. You may close this page.")
        st.stop()
    else:
        st.error("Submission failed. Try again later.")
