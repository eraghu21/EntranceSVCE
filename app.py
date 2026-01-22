import streamlit as st
import requests
import random

API = "PASTE_YOUR_WEB_APP_URL"

st.set_page_config(page_title="Entrance Exam", layout="wide")

# ---------------- SESSION INIT ----------------
def init():
    keys = {
        "user": None,
        "questions": None,
        "q_index": 0,
        "answers": {},
        "mark_review": set()
    }
    for k,v in keys.items():
        if k not in st.session_state:
            st.session_state[k] = v

init()

# ---------------- API HELPERS ----------------
def api_get(params):
    try:
        r = requests.get(API, params=params, timeout=10)
        return r.json()
    except:
        st.error("Backend not returning JSON. Check URL/deployment.")
        st.stop()

def api_post(payload):
    try:
        r = requests.post(API, json=payload, timeout=10)
        return r.json()
    except:
        st.error("Submit failed.")
        st.stop()

# ---------------- LOAD QUESTIONS ----------------
def load_questions():
    data = api_get({"action":"questions"})
    random.shuffle(data)

    for q in data:
        opts = [q["option_a"], q["option_b"], q["option_c"], q["option_d"]]
        correct_text = q[q["correct"]]
        random.shuffle(opts)

        q["shuffled"] = opts
        q["correct_index"] = opts.index(correct_text)

    return data

# ---------------- LOGIN ----------------
if not st.session_state.user:
    st.title("🎓 Entrance Exam Login")

    app_no = st.text_input("Application Number")
    password = st.text_input("Mobile Number", type="password")

    if st.button("Login"):
        res = api_get({
            "action":"login",
            "app_no":app_no,
            "password":password
        })

        if res.get("status") == "success":
            st.session_state.user = res
            st.session_state.questions = load_questions()
            st.rerun()
        else:
            st.error("Invalid credentials")

    st.stop()

# ---------------- PALETTE ----------------
questions = st.session_state.questions

st.sidebar.title("Question Palette")

section = st.sidebar.selectbox("Filter Section", ["All","Physics","Chemistry","Maths"])

for i,q in enumerate(questions):
    if section!="All" and q["section"]!=section:
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

st.title("Online Entrance Exam")
st.subheader(f"Candidate: {st.session_state.user['name']}")

with st.expander("📜 Instructions"):
    st.markdown("""
    - Each question has one correct answer  
    - You may mark questions for review  
    - You can navigate using palette  
    - No marks will be shown  
    """)

st.markdown(f"### {q['section']} - Question {st.session_state.q_index+1}")
st.write(q["question"])

prev = st.session_state.answers.get(q["id"])
if prev is None:
    choice = st.radio("Choose answer", q["shuffled"])
else:
    choice = st.radio("Choose answer", q["shuffled"], index=prev)

col1,col2,col3,col4 = st.columns(4)

with col1:
    if st.button("Save"):
        st.session_state.answers[q["id"]] = q["shuffled"].index(choice)

with col2:
    if st.button("Mark for Review"):
        st.session_state.mark_review.add(q["id"])

with col3:
    if st.button("Clear"):
        st.session_state.answers.pop(q["id"],None)
        st.rerun()

with col4:
    if st.button("Next"):
        st.session_state.q_index = min(len(questions)-1, st.session_state.q_index+1)
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

    if res.get("status")=="saved":
        st.success("Exam submitted successfully.")
        st.stop()
    else:
        st.error("Submission failed.")
