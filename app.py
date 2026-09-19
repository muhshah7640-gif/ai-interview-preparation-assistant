import sqlite3
import json
import streamlit as st
import pandas as pd

from ai_engine import generate_question, evaluate_answer
from database import (
    save_interview,
    get_interviews,
    get_profile,
    save_profile,
    login_user,
    create_user,
    delete_saved_session,
)
from resume_parser import extract_text_from_pdf


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="AI Interview Pro",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)


def load_css():
    try:
        with open("style.css", "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass


load_css()


# =========================================================
# SESSION STATE
# =========================================================

defaults = {
    "logged_in": False,
    "user_id": None,
    "user_name": "",
    "user_email": "",
    "interview_started": False,
    "job_role": "",
    "field": "",
    "experience": "",
    "interview_type": "",
    "difficulty": "",
    "number_questions": 5,
    "resume_text": "",
    "current_question": 0,
    "question": "",
    "answer": "",
    "answer_submitted": False,
    "feedback": None,
    "scores": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================================================
# LOGIN / REGISTER
# =========================================================

if not st.session_state.logged_in:

    st.title("🤖 AI Interview Pro")
    st.caption("Your personal AI-powered interview preparation assistant.")

    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Create Account"])

    with tab_login:
        st.subheader("Welcome Back")

        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input(
            "Password", type="password", key="login_password"
        )

        if st.button("🔐 Login", type="primary", use_container_width=True):
            if not login_email or not login_password:
                st.warning("Please enter your email and password.")
            else:
                try:
                    user = login_user(login_email, login_password)

                    if user:
                        st.session_state.user_id = user["id"]
                        st.session_state.user_name = user.get("name", "")
                        st.session_state.user_email = user["email"]
                        st.session_state.logged_in = True
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password.")
                except Exception as e:
                    st.error(f"Login error: {e}")

    with tab_register:
        st.subheader("Create Your Account")

        register_name = st.text_input("Full Name", key="register_name")
        register_email = st.text_input("Email", key="register_email")
        register_password = st.text_input(
            "Password", type="password", key="register_password"
        )
        register_confirm = st.text_input(
            "Confirm Password", type="password", key="register_confirm"
        )

        if st.button(
            "📝 Create Account",
            type="primary",
            use_container_width=True,
        ):
            if not register_name:
                st.warning("Please enter your name.")
            elif not register_email:
                st.warning("Please enter your email.")
            elif not register_password:
                st.warning("Please enter a password.")
            elif register_password != register_confirm:
                st.error("❌ Passwords do not match.")
            else:
                try:
                    success, message = create_user(
                        register_name,
                        register_email,
                        register_password,
                    )
                    if success:
                        st.success(
                            "✅ Account created successfully. You can now login."
                        )
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"Registration error: {e}")

    st.stop()


# =========================================================
# HELPERS
# =========================================================

def clear_current_interview_state():
    st.session_state.interview_started = False
    st.session_state.job_role = ""
    st.session_state.field = ""
    st.session_state.experience = ""
    st.session_state.interview_type = ""
    st.session_state.difficulty = ""
    st.session_state.number_questions = 5
    st.session_state.resume_text = ""
    st.session_state.current_question = 0
    st.session_state.question = ""
    st.session_state.answer = ""
    st.session_state.answer_submitted = False
    st.session_state.feedback = None
    st.session_state.scores = []


def delete_all_user_interview_data(user_id):
    # Current/saved session
    try:
        delete_saved_session(user_id)
    except Exception:
        pass

    # Completed questions used by History and Progress
    conn = sqlite3.connect("interview.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM interviews WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_feedback_dict(value):
    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return {"better_answer": value}

    return {}


def generate_next_question():
    question = generate_question(
        st.session_state.job_role,
        st.session_state.field,
        st.session_state.experience,
        st.session_state.interview_type,
        st.session_state.difficulty,
        st.session_state.resume_text,
    )

    st.session_state.question = question
    st.session_state.answer = ""
    st.session_state.answer_submitted = False
    st.session_state.feedback = None


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("## 🤖 AI Interview Pro")
    st.caption("AI-powered interview preparation")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "👤 Profile",
            "🎯 Start Interview",
            "📊 Progress",
            "📝 History",
        ],
    )

    st.divider()
    st.write(f"👤 {st.session_state.user_name}")

    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.user_name = ""
        st.session_state.user_email = ""
        clear_current_interview_state()
        st.rerun()

    st.divider()
    st.caption(
        "Practice interviews for any career, get AI feedback, "
        "and track your progress."
    )
    st.caption("Powered by Gemini")


# =========================================================
# USER DATA
# =========================================================

try:
    interviews = get_interviews(st.session_state.user_id)
except Exception:
    interviews = []


# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":

    st.markdown("<h1>🤖 AI Interview Pro</h1>", unsafe_allow_html=True)
    st.markdown(
        "### Prepare for any interview with your personal AI interviewer."
    )
    st.write(
        "Practice realistic interview questions, receive AI-powered "
        "feedback, and improve your answers step by step."
    )
    st.divider()

    scores = []
    for item in interviews:
        try:
            scores.append(float(item[8]))
        except Exception:
            pass

    average_score = sum(scores) / len(scores) if scores else 0
    best_score = max(scores) if scores else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Questions Practiced", len(interviews))
    with col2:
        st.metric("Average Score", f"{average_score:.1f}/10")
    with col3:
        st.metric("Best Score", f"{best_score:.1f}/10")

    st.divider()

    st.markdown("## Why use AI Interview Pro?")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🎯 Any Career")
        st.write(
            "Prepare for interviews across different jobs and professional fields."
        )
    with col2:
        st.markdown("### 🤖 AI Feedback")
        st.write(
            "Receive scores, strengths, missing points, improvements and better answers."
        )
    with col3:
        st.markdown("### 📊 Track Progress")
        st.write(
            "Monitor your performance and improve your interview skills over time."
        )

    st.divider()
    st.markdown("## How It Works")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("### 1️⃣ Choose")
        st.write("Select job role, field, experience and interview type.")
    with c2:
        st.markdown("### 2️⃣ Practice")
        st.write("Answer AI-generated interview questions.")
    with c3:
        st.markdown("### 3️⃣ Improve")
        st.write("Get an AI score and detailed feedback.")
    with c4:
        st.markdown("### 4️⃣ Track")
        st.write("Review interview history and performance.")

    st.divider()
    st.info(
        "💡 Tip: Upload your resume before starting an interview "
        "to receive more personalized questions."
    )


# =========================================================
# PROFILE
# =========================================================

elif page == "👤 Profile":

    st.markdown("## 👤 My Profile")

    try:
        profile = get_profile(st.session_state.user_id)
    except Exception:
        profile = None

    if profile:
        current_name = profile[0] or st.session_state.user_name
        current_email = profile[1] or st.session_state.user_email
        current_target_role = profile[2] or ""
        current_education = profile[3] or ""
        current_bio = profile[4] or ""
    else:
        current_name = st.session_state.user_name
        current_email = st.session_state.user_email
        current_target_role = ""
        current_education = ""
        current_bio = ""

    name = st.text_input("Full Name", value=current_name)
    st.text_input("Email", value=current_email, disabled=True)
    target_role = st.text_input(
        "Target Job Role",
        value=current_target_role,
        placeholder="e.g. Data Scientist",
    )
    education = st.text_input(
        "Education",
        value=current_education,
        placeholder="e.g. BS Data Science",
    )
    bio = st.text_area(
        "About You",
        value=current_bio,
        placeholder="Write a short professional introduction.",
    )

    if st.button("💾 Save Profile", type="primary", use_container_width=True):
        try:
            save_profile(
                st.session_state.user_id,
                name.strip(),
                current_email,
                target_role.strip(),
                education.strip(),
                bio.strip(),
            )
            st.session_state.user_name = name.strip()
            st.success("✅ Profile updated successfully.")
        except Exception as e:
            st.error(f"Could not save profile: {e}")


# =========================================================
# START INTERVIEW
# =========================================================

elif page == "🎯 Start Interview":

    st.markdown("## 🎯 Start AI Interview")
    st.write(
        "Enter your career information and let AI create a personalized interview."
    )
    st.divider()

    job_role = st.text_input(
        "Job Role",
        value=st.session_state.job_role,
        placeholder="e.g. Data Scientist, Teacher, Accountant",
    )

    field = st.text_input(
        "Field / Industry",
        value=st.session_state.field,
        placeholder="e.g. Data Science, Education, Finance",
    )

    col1, col2 = st.columns(2)

    with col1:
        experience_options = [
            "Student / Fresh Graduate",
            "Entry Level",
            "1–2 Years",
            "3–5 Years",
            "5+ Years",
        ]
        experience = st.selectbox(
            "Experience Level",
            experience_options,
            index=(
                experience_options.index(st.session_state.experience)
                if st.session_state.experience in experience_options
                else 0
            ),
        )

        interview_type_options = [
            "General Interview",
            "Technical Interview",
            "HR Interview",
            "Behavioral Interview",
            "Mixed Interview",
        ]
        interview_type = st.selectbox(
            "Interview Type",
            interview_type_options,
            index=(
                interview_type_options.index(st.session_state.interview_type)
                if st.session_state.interview_type in interview_type_options
                else 0
            ),
        )

    with col2:
        difficulty_options = ["Beginner", "Intermediate", "Advance"]
        difficulty = st.selectbox(
            "Difficulty",
            difficulty_options,
            index=(
                difficulty_options.index(st.session_state.difficulty)
                if st.session_state.difficulty in difficulty_options
                else 0
            ),
        )

        number_questions = st.slider(
            "Number of Questions",
            min_value=1,
            max_value=10,
            value=st.session_state.number_questions,
        )

    st.divider()

    st.markdown("### 📄 Resume")

    resume_file = st.file_uploader(
        "Upload Resume (PDF) — Optional",
        type=["pdf"],
        help="Upload your resume to personalize your interview.",
    )

    if resume_file is not None:
        st.success(f"✅ Resume uploaded: {resume_file.name}")
    else:
        st.caption(
            "Resume upload is optional. You can continue without a resume."
        )

    st.divider()

    # Only this page has the delete button.
    if st.button(
        "🗑️ Delete Old Interview Data",
        use_container_width=True,
    ):
        try:
            delete_all_user_interview_data(st.session_state.user_id)
            clear_current_interview_state()
            st.success(
                "✅ Old interview data, History and Progress deleted."
            )
            st.rerun()
        except Exception as e:
            st.error(f"Could not delete old interview data: {e}")

    st.divider()

    # Only ONE Start Interview button.
    if st.button(
        "🚀 Start AI Interview",
        use_container_width=True,
        type="primary",
    ):

        if not job_role.strip():
            st.error("Please enter a job role.")

        elif not field.strip():
            st.error("Please enter your field / industry.")

        else:

            if resume_file is not None:
                try:
                    extracted_resume = extract_text_from_pdf(resume_file)
                    st.session_state.resume_text = extracted_resume[:3000]
                except Exception as e:
                    st.error(f"Could not read the resume: {e}")
                    st.session_state.resume_text = ""
            else:
                st.session_state.resume_text = ""

            st.session_state.job_role = job_role.strip()
            st.session_state.field = field.strip()
            st.session_state.experience = experience
            st.session_state.interview_type = interview_type
            st.session_state.difficulty = difficulty
            st.session_state.number_questions = number_questions
            st.session_state.current_question = 1
            st.session_state.answer = ""
            st.session_state.answer_submitted = False
            st.session_state.feedback = None
            st.session_state.scores = []
            st.session_state.interview_started = False

            with st.spinner("🤖 AI is preparing your interview..."):
                try:
                    question = generate_question(
                        st.session_state.job_role,
                        st.session_state.field,
                        st.session_state.experience,
                        st.session_state.interview_type,
                        st.session_state.difficulty,
                        st.session_state.resume_text,
                    )

                    st.session_state.question = question
                    st.session_state.interview_started = True
                    st.rerun()

                except Exception as e:
                    st.error(f"Could not generate question: {e}")


# =========================================================
# ACTIVE INTERVIEW
# =========================================================

if page == "🎯 Start Interview" and st.session_state.interview_started:

    st.divider()
    st.markdown("## 🎤 Interview in Progress")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Job Role:** {st.session_state.job_role}")
    with col2:
        st.markdown(f"**Field:** {st.session_state.field}")
    with col3:
        st.markdown(f"**Difficulty:** {st.session_state.difficulty}")

    if st.session_state.resume_text:
        st.success("📄 Resume personalization is active.")
    else:
        st.info(
            "📄 No resume uploaded. Questions are based on your interview settings."
        )

    st.divider()

    current = st.session_state.current_question
    total = st.session_state.number_questions

    st.progress(min(current / total, 1.0))
    st.caption(f"Question {current} of {total}")

    st.markdown("### ❓ Interview Question")
    st.info(st.session_state.question)

    if not st.session_state.answer_submitted:

        answer = st.text_area(
            "Your Answer",
            value=st.session_state.answer,
            height=180,
            placeholder="Type your interview answer here...",
        )

        if st.button(
            "✅ Submit Answer",
            use_container_width=True,
            type="primary",
        ):

            if not answer.strip():
                st.warning("Please write an answer before submitting.")

            else:

                with st.spinner("🤖 AI is evaluating your answer..."):

                    try:
                        feedback = evaluate_answer(
                            st.session_state.job_role,
                            st.session_state.question,
                            answer,
                        )

                        numeric_score = float(
                            feedback.get("score", 0)
                        )

                        st.session_state.answer = answer
                        st.session_state.feedback = feedback
                        st.session_state.scores.append(numeric_score)
                        st.session_state.answer_submitted = True

                        # Store feedback as JSON text for SQLite.
                        feedback_for_db = json.dumps(
                            feedback,
                            ensure_ascii=False,
                        )

                        save_interview(
                            st.session_state.user_id,
                            st.session_state.job_role,
                            st.session_state.field,
                            st.session_state.experience,
                            st.session_state.interview_type,
                            st.session_state.difficulty,
                            st.session_state.question,
                            answer,
                            numeric_score,
                            feedback_for_db,
                        )

                        st.rerun()

                    except Exception as e:
                        st.error(
                            f"Could not evaluate answer: {e}"
                        )

    if (
        st.session_state.answer_submitted
        and st.session_state.feedback
    ):

        feedback = st.session_state.feedback

        st.divider()
        st.markdown("## 🤖 AI Feedback")

        score = feedback.get("score", 0)

        score_col, info_col = st.columns([1, 3])
        with score_col:
            st.metric("Score", f"{score}/10")
        with info_col:
            st.write(
                "The AI evaluates your answer and provides constructive feedback."
            )

        st.markdown("### ✅ Good Points")
        good_points = feedback.get("good_points", [])
        if good_points:
            for item in good_points:
                st.write(f"• {item}")
        else:
            st.write("No specific good points returned.")

        st.markdown("### ⚠️ Missing Points")
        missing_points = feedback.get("missing_points", [])
        if missing_points:
            for item in missing_points:
                st.write(f"• {item}")
        else:
            st.write("No specific missing points returned.")

        st.markdown("### 💡 Improvements")
        improvements = feedback.get("improvements", [])
        if improvements:
            for item in improvements:
                st.write(f"• {item}")
        else:
            st.write("No specific improvements returned.")

        st.markdown("### ✨ Better Answer")
        st.info(feedback.get("better_answer", ""))

        st.divider()

        if current < total:

            if st.button(
                "➡️ Next Question",
                use_container_width=True,
                type="primary",
            ):

                st.session_state.current_question += 1

                with st.spinner(
                    "🤖 AI is preparing your next question..."
                ):
                    try:
                        generate_next_question()
                        st.rerun()
                    except Exception as e:
                        st.error(
                            f"Could not generate next question: {e}"
                        )

        else:

            st.success("🎉 Interview completed!")

            if st.session_state.scores:
                final_average = (
                    sum(st.session_state.scores)
                    / len(st.session_state.scores)
                )
                st.metric(
                    "Interview Average Score",
                    f"{final_average:.1f}/10",
                )

            if st.button(
                "🔄 Start New Interview",
                use_container_width=True,
            ):
                clear_current_interview_state()
                st.rerun()


# =========================================================
# PROGRESS
# =========================================================

elif page == "📊 Progress":

    st.markdown("## 📊 My Progress")

    if not interviews:
        st.info(
            "No interview data available yet. "
            "Complete an interview to see your progress."
        )

    else:

        progress_scores = []

        for item in interviews:
            try:
                progress_scores.append(float(item[8]))
            except Exception:
                pass

        if progress_scores:

            average = sum(progress_scores) / len(progress_scores)
            best = max(progress_scores)

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Questions Completed",
                    len(progress_scores),
                )

            with col2:
                st.metric(
                    "Average Score",
                    f"{average:.1f}/10",
                )

            with col3:
                st.metric(
                    "Best Score",
                    f"{best:.1f}/10",
                )

            st.divider()
            st.markdown("### 📈 Score History")

            chart_data = pd.DataFrame(
                {
                    "Question": range(
                        1,
                        len(progress_scores) + 1,
                    ),
                    "Score": progress_scores,
                }
            ).set_index("Question")

            st.line_chart(chart_data)

        else:
            st.info("No valid scores are available yet.")


# =========================================================
# HISTORY
# =========================================================

elif page == "📝 History":

    st.markdown("## 📝 Interview History")

    st.write(
        "Review your previous interview questions, answers and scores."
    )

    if not interviews:
        st.info("No interview history yet.")

    else:

        for item in interviews:

            (
                interview_id,
                job_role,
                field,
                experience,
                interview_type,
                difficulty,
                question,
                answer,
                score,
                feedback,
                created_at,
            ) = item

            with st.expander(
                f"🎯 {job_role} — Score: {score}/10"
            ):

                st.write(f"**Field:** {field}")
                st.write(f"**Experience:** {experience}")
                st.write(f"**Interview Type:** {interview_type}")
                st.write(f"**Difficulty:** {difficulty}")
                st.write(f"**Date:** {created_at}")

                st.markdown("### ❓ Question")
                st.info(question)

                st.markdown("### ✍️ Your Answer")
                st.write(answer)

                st.markdown("### 🤖 AI Feedback")

                feedback_data = get_feedback_dict(feedback)

                if feedback_data:

                    st.write(
                        f"**Score:** {feedback_data.get('score', score)}/10"
                    )

                    st.markdown("**Good Points**")
                    for point in feedback_data.get("good_points", []):
                        st.write(f"• {point}")

                    st.markdown("**Missing Points**")
                    for point in feedback_data.get("missing_points", []):
                        st.write(f"• {point}")

                    st.markdown("**Improvements**")
                    for point in feedback_data.get("improvements", []):
                        st.write(f"• {point}")

                    st.markdown("**Better Answer**")
                    st.info(
                        feedback_data.get("better_answer", "")
                    )

                else:
                    st.write(feedback)
