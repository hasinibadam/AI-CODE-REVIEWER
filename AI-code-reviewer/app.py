# -*- coding: utf-8 -*-

import streamlit as st
import sqlite3
import subprocess
from datetime import datetime
import ast
import autopep8
import pickle
import matplotlib.pyplot as plt
import time
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AI Code Reviewer", layout="wide")
st.title("🚀 AI Code Reviewer")

# ---------------- ML ----------------
model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

def predict_quality(code):
    return model.predict(vectorizer.transform([code]))[0]

# ---------------- DATABASE ----------------
conn = sqlite3.connect("app.db", check_same_thread=False)
c = conn.cursor()
c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT, password TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS history (username TEXT, code TEXT, result TEXT, score INTEGER, time TEXT)")
conn.commit()

# ---------------- AUTH ----------------
def login(u, p):
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p))
    return c.fetchone()

def signup(u, p):
    c.execute("INSERT INTO users VALUES (?,?)", (u, p))
    conn.commit()

# ---------------- ANALYSIS ----------------
def run_pylint(f):
    return subprocess.run(
        ["pylint", f],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    ).stdout

def run_code(file):
    try:
        result = subprocess.run(
            ["python", file],
            input="5\n5\n5\n",
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.stdout if result.stdout else result.stderr
    except Exception as e:
        return f"Error: {e}"

def check_syntax(code):
    try:
        ast.parse(code)
        return "✅ No syntax errors"
    except Exception as e:
        return f"❌ {e}"

# ---------------- ⭐ IMPROVED SCORING ----------------
def get_score(code):

    score = 100

    # Syntax error
    try:
        ast.parse(code)
    except:
        score -= 30

    # Type mismatch
    if '"' in code and "+" in code:
        score -= 20

    # Input issue
    if "input(" in code and "int(input(" not in code:
        score -= 15

    # Indentation issue
    if "for " in code and "    " not in code:
        score -= 15

    # No comments
    if "#" not in code:
        score -= 5

    return max(score, 0)

def suggestions(code):
    s = []
    if "print(" in code: s.append("Use return instead of print")
    if "#" not in code: s.append("Add comments")
    if "input(" in code: s.append("Convert input to int/float")
    return s

# ---------------- ERROR EXPLANATION ----------------
def explain_errors(code):
    explanations = []

    if "for " in code and ":" not in code:
        explanations.append("Missing ':' in loop")

    if "def " in code and ":" not in code:
        explanations.append("Missing ':' in function")

    if "input(" in code:
        explanations.append("input() returns string")

    if "+" in code and '"' in code:
        explanations.append("String and number cannot be added")

    if "    " not in code and "for " in code:
        explanations.append("Indentation missing in loop")

    return explanations

# ---------------- 🔥 AUTO FIX ----------------
def auto_fix_code(code):

    try:
        ast.parse(code)
        return autopep8.fix_code(code)
    except:
        pass

    # Fix colons
    lines = code.split("\n")
    fixed_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("def ", "if ", "for ", "while ", "elif ", "else")):
            if not stripped.endswith(":"):
                line = stripped + ":"
        fixed_lines.append(line)

    code = "\n".join(fixed_lines)

    # Fix indentation
    try:
        ast.parse(code)
    except:
        new_lines = []
        indent = 0

        for line in code.split("\n"):
            stripped = line.strip()

            if stripped.startswith(("def ", "for ", "if ", "while ", "elif ", "else")):
                new_lines.append(stripped)
                indent += 1

            elif stripped:
                new_lines.append("    " * indent + stripped)

            else:
                new_lines.append(line)

        code = "\n".join(new_lines)

    # Fix input
    code = re.sub(
        r'(\w+)\s*=\s*input\((.*?)\)',
        r'\1 = int(input(\2))',
        code
    )

    # Fix string numbers
    code = re.sub(r'["\'](\d+)["\']', r'int(\1)', code)

    # Fix print concat
    code = re.sub(
        r'print\("([^"]+)"\s*\+\s*(\w+)\)',
        r'print("\1", \2)',
        code
    )

    code = autopep8.fix_code(code)

    return code

# ---------------- SESSION ----------------
if "login" not in st.session_state:
    st.session_state.login = False

# ---------------- LOGIN ----------------
if not st.session_state.login:

    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        u = st.text_input("Username")
        p = st.text_input("Password", type="password")
        if st.button("Login"):
            if login(u, p):
                st.session_state.login = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        u = st.text_input("New Username")
        p = st.text_input("New Password", type="password")
        if st.button("Signup"):
            signup(u, p)
            st.success("Account created!")

# ---------------- MAIN ----------------
else:

    st.sidebar.title(f"👤 {st.session_state.user}")

    if st.sidebar.button("Logout"):
        st.session_state.login = False
        st.rerun()

    file = st.file_uploader("Upload Code", type=["py"])
    code = ""

    if file:
        code = file.read().decode("utf-8", errors="ignore")

    code = st.text_area("Code", value=code, height=250)

    if st.button("Analyze"):

        with st.spinner("⚡ Fixing your code..."):
            time.sleep(1)

        with open("temp.py", "w", encoding="utf-8") as f:
            f.write(code)

        fixed = auto_fix_code(code)

        with open("temp_fixed.py", "w", encoding="utf-8") as f:
            f.write(fixed)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📌 Original Code")
            st.code(code)

        with col2:
            st.subheader("🛠 Fixed Code")
            st.code(fixed)

        # Explanation
        st.subheader("🧠 Error Explanation")
        for e in explain_errors(code):
            st.write("❌", e)

        # Syntax
        syntax_result = check_syntax(fixed)
        st.subheader("🧠 Syntax Check")
        st.write(syntax_result)

        if syntax_result.startswith("✅"):
            st.success("Code fixed successfully!")
        else:
            st.error("Some issues still exist")

        # Pylint
        st.subheader("🔍 Pylint Analysis")
        result = run_pylint("temp_fixed.py")
        st.text_area("", result, height=200)

        # Output
        st.subheader("🖥 Output")
        output = run_code("temp_fixed.py")
        st.code(output)

        # Suggestions
        st.subheader("💡 Suggestions")
        for i in suggestions(code):
            st.write("💡", i)

        # Score comparison
        score = get_score(code)
        fixed_score = get_score(fixed)

        st.subheader("📊 Score Comparison")
        col1, col2 = st.columns(2)
        col1.metric("Before Fix", score)
        col2.metric("After Fix", fixed_score)

        # Download
        st.download_button("⬇ Download Fixed Code", fixed, "fixed_code.py")

        # Graphs
        st.subheader("📊 Dashboard")

        c.execute("SELECT * FROM history WHERE username=?", (st.session_state.user,))
        rows = c.fetchall()

        col1, col2 = st.columns(2)

        with col1:
            fig, ax = plt.subplots(figsize=(4, 3))
            ax.bar(["Score"], [score])
            st.pyplot(fig)

        with col2:
            scores = [r[3] for r in rows[::-1]]
            if scores:
                fig2, ax2 = plt.subplots(figsize=(4, 3))
                ax2.plot(scores, marker='o')
                st.pyplot(fig2)

        # ML
        st.subheader("🧠 ML Prediction")
        ml = predict_quality(code)

        if ml == "good":
            st.success("Good Code")
        elif ml == "average":
            st.warning("Average Code")
        else:
            st.error("Poor Code")

        # Save
        c.execute(
            "INSERT INTO history VALUES (?,?,?,?,?)",
            (st.session_state.user, code, result, score, str(datetime.now()))
        )
        conn.commit()

    st.sidebar.subheader("📜 History")
    c.execute("SELECT * FROM history WHERE username=?", (st.session_state.user,))
    for r in c.fetchall()[::-1]:
        st.sidebar.text(f"{r[4]} | {r[3]}") 