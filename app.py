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
    "answer_editor": "",
    "last_audio_key": None,
    "answer_editor_audio_key": None,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

if not st.session_state.logged_in:
    st.title("🤖 AI Interview Pro")
    st.caption("Your personal AI-powered interview preparation assistant.")
    tab_login, tab_register = st.tabs(["🔐 Login", "📝 Create Account"])

    with tab_login:
        st.subheader("Welcome Back")
        login_email = st.text_input("Email", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
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
        register_password = st.text_input("Password", type="password", key="register_password")
        register_confirm = st.text_input("Confirm Password", type="password", key="register_confirm")
        if st.button("📝 Create Account", type="primary", use_container_width=True):
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
                        register_name, register_email, register_password
                    )
                    if success:
                        st.success("✅ Account created successfully. You can now login.")
                    else:
                        st.error(message)
                except Exception as e:
                    st.error(f"Registration error: {e}")
    st.stop()

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
    st.session_state.answer_editor = ""
    st.session_state.answer_editor_audio_key = None
    st.session_state.last_audio_key = None
    st.session_state.answer_submitted = False
    st.session_state.feedback = None
    st.session_state.scores = []

def delete_all_user_interview_data(user_id):
    try:
        delete_saved_session(user_id)
    except Exception:
        pass
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

def clear_answer_editor():
    """Reset the current answer before the next Streamlit rerun."""
    st.session_state.answer = ""
    st.session_state.answer_editor = ""
    st.session_state.last_audio_key = None
    st.session_state.answer_editor_audio_key = None


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
    st.session_state.answer_editor = ""
    st.session_state.answer_editor_audio_key = None
    st.session_state.last_audio_key = None
    st.session_state.answer_submitted = False
    st.session_state.feedback = None

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
    st.caption("Practice interviews for any career, get AI feedback, and track your progress.")
    st.caption("Powered by Gemini")

try:
    interviews = get_interviews(st.session_state.user_id)
except Exception:
    interviews = []

# =========================================================
# DASHBOARD
# =========================================================

if page == "🏠 Dashboard":
    st.markdown('<div class="hero-title">🤖 AI Interview Pro</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Your personal AI interviewer for smarter interview preparation.</div>',
        unsafe_allow_html=True,
    )

    scores = []
    for item in interviews:
        try:
            scores.append(float(item[8]))
        except Exception:
            pass

    total_questions = len(scores)
    average_score = sum(scores) / len(scores) if scores else 0
    best_score = max(scores) if scores else 0

    st.divider()
    st.markdown("### 📊 Your Interview Overview")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Questions Practiced", total_questions)
    with col2:
        st.metric("Average Score", f"{average_score:.1f}/10")
    with col3:
        st.metric("Best Score", f"{best_score:.1f}/10")
    with col4:
        if total_questions >= 10:
            level = "Advanced"
        elif total_questions >= 5:
            level = "Intermediate"
        elif total_questions > 0:
            level = "Getting Started"
        else:
            level = "Not Started"
        st.metric("Practice Level", level)

    st.divider()
    st.markdown("### 🚀 Start Your Next Interview")
    quick_col1, quick_col2 = st.columns([2, 1])
    with quick_col1:
        st.markdown(
            """
            <div class="card">
                <h3>🎯 Practice with an AI Interviewer</h3>
                <p>Choose any career, field, experience level and interview type.
                Gemini will generate realistic interview questions and evaluate your answers.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with quick_col2:
        st.info("Go to **🎯 Start Interview** in the sidebar to begin.")

    st.divider()
    st.markdown("### 📈 Performance Summary")
    performance_col1, performance_col2 = st.columns(2)
    with performance_col1:
        if scores:
            chart_data = pd.DataFrame(
                {"Question": range(1, len(scores) + 1), "Score": scores}
            ).set_index("Question")
            st.line_chart(chart_data)
        else:
            st.info("Complete your first interview to see your performance chart.")
    with performance_col2:
        st.markdown(
            """
            <div class="card">
                <h3>🧠 AI Coaching</h3>
                <p>Your answers are evaluated across multiple interview skills.</p>
                <ul>
                    <li>Technical Knowledge</li>
                    <li>Communication</li>
                    <li>Clarity</li>
                    <li>Structure</li>
                    <li>Confidence</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### ✨ What You Can Do")
    feature1, feature2, feature3 = st.columns(3)
    with feature1:
        st.markdown(
            '<div class="feature-card"><div class="feature-icon">🎯</div><div class="feature-title">Any Career</div><div class="feature-text">Practice interviews for different jobs, industries and professional fields.</div></div>',
            unsafe_allow_html=True,
        )
    with feature2:
        st.markdown(
            '<div class="feature-card"><div class="feature-icon">🤖</div><div class="feature-title">AI Feedback</div><div class="feature-text">Get scores, strengths, missing points, improvements and better answers.</div></div>',
            unsafe_allow_html=True,
        )
    with feature3:
        st.markdown(
            '<div class="feature-card"><div class="feature-icon">📊</div><div class="feature-title">Track Progress</div><div class="feature-text">Review your interview history and monitor your performance over time.</div></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### ⚡ How It Works")
    step1, step2, step3, step4 = st.columns(4)
    with step1:
        st.markdown("### 1️⃣ Choose")
        st.caption("Select your job role, field and interview settings.")
    with step2:
        st.markdown("### 2️⃣ Practice")
        st.caption("Answer realistic AI-generated interview questions.")
    with step3:
        st.markdown("### 3️⃣ Improve")
        st.caption("Receive detailed AI scoring and coaching.")
    with step4:
        st.markdown("### 4️⃣ Track")
        st.caption("Review your scores, history and progress.")

    st.divider()
    st.markdown("### 📝 Recent Interview Activity")
    if not interviews:
        st.info("No interview activity yet. Start your first AI interview.")
    else:
        for item in interviews[:5]:
            try:
                _, job_role, field, experience, interview_type, difficulty, question, answer, score, feedback, created_at = item
                activity_col1, activity_col2 = st.columns([4, 1])
                with activity_col1:
                    st.markdown(f"**🎯 {job_role}**  \n{interview_type} • {difficulty} • {created_at}")
                with activity_col2:
                    st.metric("Score", f"{score}/10")
                st.divider()
            except Exception:
                continue

# =========================================================
# PROFILE
# =========================================================

elif page == "👤 Profile":
    st.markdown('<div class="hero-title">👤 My Profile</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Keep your professional profile ready for personalized interview practice.</div>',
        unsafe_allow_html=True,
    )

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

    profile_col1, profile_col2 = st.columns(2)
    with profile_col1:
        name = st.text_input("Full Name", value=current_name)
        st.text_input("Email", value=current_email, disabled=True)
        target_role = st.text_input(
            "Target Job Role",
            value=current_target_role,
            placeholder="e.g. Data Scientist",
        )
    with profile_col2:
        education = st.text_input(
            "Education",
            value=current_education,
            placeholder="e.g. BS Data Science",
        )
        bio = st.text_area(
            "About You",
            value=current_bio,
            placeholder="Write a short professional introduction.",
            height=150,
        )

    st.divider()
    st.markdown("### 🎯 Career Profile")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Target Role", target_role if target_role else "Not set")
    with c2:
        st.metric("Education", education if education else "Not set")
    with c3:
        st.metric("Profile Status", "Ready" if (target_role and education) else "Incomplete")

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
            st.rerun()
        except Exception as e:
            st.error(f"Could not save profile: {e}")

# =========================================================
# START INTERVIEW
# =========================================================

elif page == "🎯 Start Interview":
    st.markdown('<div class="hero-title">🎯 Start AI Interview</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Configure your interview and practice with your personal AI interviewer.</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("### 👤 Interview Profile")

    setup_col1, setup_col2 = st.columns(2)
    with setup_col1:
        job_role = st.text_input(
            "💼 Job Role",
            value=st.session_state.job_role,
            placeholder="e.g. Data Scientist, Software Engineer, Teacher",
        )
        field = st.text_input(
            "🏢 Field / Industry",
            value=st.session_state.field,
            placeholder="e.g. Data Science, Education, Finance",
        )
    with setup_col2:
        experience_options = ["Student / Fresh Graduate", "Entry Level", "1–2 Years", "3–5 Years", "5+ Years"]
        experience = st.selectbox(
            "📚 Experience Level",
            experience_options,
            index=(experience_options.index(st.session_state.experience) if st.session_state.experience in experience_options else 0),
        )
        interview_type_options = ["General Interview", "Technical Interview", "HR Interview", "Behavioral Interview", "Mixed Interview"]
        interview_type = st.selectbox(
            "🎤 Interview Type",
            interview_type_options,
            index=(interview_type_options.index(st.session_state.interview_type) if st.session_state.interview_type in interview_type_options else 0),
        )

    st.divider()
    st.markdown("### ⚙️ Interview Preferences")
    preference_col1, preference_col2 = st.columns(2)
    with preference_col1:
        difficulty_options = ["Beginner", "Intermediate", "Advanced"]
        difficulty = st.selectbox(
            "📈 Difficulty",
            difficulty_options,
            index=(difficulty_options.index(st.session_state.difficulty) if st.session_state.difficulty in difficulty_options else 0),
        )
    with preference_col2:
        number_questions = st.slider(
            "❓ Number of Questions",
            min_value=1,
            max_value=10,
            value=st.session_state.number_questions,
        )

    st.divider()
    st.markdown("### 📄 Personalize Your Interview")
    resume_file = st.file_uploader(
        "Upload Resume (PDF) — Optional",
        type=["pdf"],
        help="Upload your resume to personalize your interview.",
    )
    if resume_file is not None:
        st.success(f"✅ Resume selected: {resume_file.name}")
    else:
        st.info("📄 No resume uploaded. You can still start an interview.")

    st.divider()
    st.markdown("### 🔎 Interview Summary")
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    with summary_col1:
        st.markdown("**💼 Job Role**")
        st.write(job_role.strip() if job_role.strip() else "Not selected")
    with summary_col2:
        st.markdown("**🎤 Interview Type**")
        st.write(interview_type)
    with summary_col3:
        st.markdown("**❓ Questions**")
        st.write(number_questions)

    st.divider()
    if st.button("🚀 Start AI Interview", use_container_width=True, type="primary"):
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

            with st.spinner("🤖 AI is preparing your personalized interview..."):
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

    st.divider()
    info1, info2, info3 = st.columns(3)
    with info1:
        st.markdown('<div class="feature-card"><div class="feature-icon">❓</div><div class="feature-title">Generate Questions</div><div class="feature-text">AI creates questions based on your career and interview type.</div></div>', unsafe_allow_html=True)
    with info2:
        st.markdown('<div class="feature-card"><div class="feature-icon">🧠</div><div class="feature-title">Analyze Answers</div><div class="feature-text">Your answers are evaluated across multiple interview skills.</div></div>', unsafe_allow_html=True)
    with info3:
        st.markdown('<div class="feature-card"><div class="feature-icon">📈</div><div class="feature-title">Improve Performance</div><div class="feature-text">Receive practical feedback and a stronger example answer.</div></div>', unsafe_allow_html=True)

    st.divider()
    with st.expander("🗑️ Manage Previous Interview Data"):
        st.warning("This will permanently delete your saved interview history and progress.")
        if st.button("🗑️ Delete Old Interview Data", use_container_width=True):
            try:
                delete_all_user_interview_data(st.session_state.user_id)
                clear_current_interview_state()
                st.success("✅ Old interview data, History and Progress deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"Could not delete old interview data: {e}")

# =========================================================
# ACTIVE INTERVIEW
# =========================================================

def transcribe_voice_answer(audio_file):
    """Transcribe a recorded interview answer with Gemini 3.5 Transcribe."""
    import os
    import tempfile
    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured in your environment or Streamlit secrets.")

    audio_bytes = audio_file.getvalue()
    if not audio_bytes:
        raise RuntimeError("The recording is empty. Please record your answer again.")

    mime_type = getattr(audio_file, "type", None) or "audio/webm"
    extension_by_mime = {
        "audio/webm": ".webm",
        "audio/wav": ".wav",
        "audio/x-wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
        "audio/ogg": ".ogg",
    }
    suffix = extension_by_mime.get(mime_type.lower(), ".webm")
    temp_path = None
    client = None
    uploaded_audio = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(audio_bytes)
            temp_path = temp.name

        client = genai.Client(api_key=api_key)
        uploaded_audio = client.files.upload(file=temp_path)

        # Gemini 3.5 Transcribe uses the Interactions API. The previous
        # Generate Content call could return no transcript for this model.
        audio_uri = getattr(uploaded_audio, "uri", None)
        uploaded_mime = getattr(uploaded_audio, "mime_type", None) or mime_type
        if not audio_uri:
            raise RuntimeError("Gemini uploaded the recording but did not return an audio URI.")

        interaction = client.interactions.create(
            model="gemini-3.5-transcribe",
            input=[{
                "type": "audio",
                "uri": audio_uri,
                "mime_type": uploaded_mime,
            }],
            generation_config={
                "transcription_config": {
                    "mode": {"type": "verbatim"}
                }
            },
        )

        transcript = (getattr(interaction, "output_text", None) or "").strip()
        if not transcript:
            # Compatibility fallback for SDK responses that expose output items.
            output_items = getattr(interaction, "outputs", None) or getattr(interaction, "output", None) or []
            collected = []
            for item in output_items:
                item_text = getattr(item, "text", None)
                if item_text:
                    collected.append(item_text.strip())
                content = getattr(item, "content", None) or []
                for part in content:
                    part_text = getattr(part, "text", None)
                    if part_text:
                        collected.append(part_text.strip())
            transcript = " ".join(part for part in collected if part).strip()

        if not transcript:
            raise RuntimeError(
                "Gemini received the recording but returned an empty transcript. "
                "Try recording a clear 5–10 second answer, or type your answer manually."
            )

        # Guard against accidental binary data being inserted into the answer box.
        if "\x00" in transcript or "\xff" in transcript or any(ord(ch) < 9 for ch in transcript):
            raise RuntimeError("The transcription response was not valid speech text. Please record again.")

        return transcript

    except AttributeError as exc:
        if "interactions" in str(exc).lower() or "create" in str(exc).lower():
            raise RuntimeError(
                "Your google-genai package may be outdated. In the project terminal run: "
                "python -m pip install --upgrade google-genai, then restart Streamlit."
            ) from exc
        raise
    finally:
        if temp_path:
            try:
                os.remove(temp_path)
            except OSError:
                pass


if page == "🎯 Start Interview" and st.session_state.interview_started:
    st.divider()

    current = st.session_state.current_question
    total = st.session_state.number_questions

    st.markdown('<div class="hero-title">🎤 Interview in Progress</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Answer naturally. You can type or record your answer, then review it before AI evaluation.</div>',
        unsafe_allow_html=True,
    )

    meta1, meta2, meta3 = st.columns(3)
    with meta1:
        st.markdown(f"**💼 Job Role**  \n{st.session_state.job_role}")
    with meta2:
        st.markdown(f"**🏢 Field**  \n{st.session_state.field}")
    with meta3:
        st.markdown(f"**📈 Difficulty**  \n{st.session_state.difficulty}")

    st.progress(min(current / total, 1.0))
    st.caption(f"Question {current} of {total}")

    st.markdown(
        f"""
        <div class="question-card">
            <div class="question-label">QUESTION {current}</div>
            <div class="question-text">{st.session_state.question}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.resume_text:
        st.success("📄 Resume personalization is active.")
    else:
        st.caption("📄 This interview is based on your selected interview settings.")

    if not st.session_state.answer_submitted:
        st.markdown("### ✍️ Your Answer")
        st.caption("Type your answer, or record it with the microphone. If you record, the transcript will appear in the box below for review.")

        st.markdown("### 🎤 Voice Answer")
        audio_file = st.audio_input("Record your interview answer")

        # Process the audio BEFORE creating the answer_editor widget.
        # This avoids Streamlit's WidgetAlreadyInstantiatedError and ensures
        # the newest transcript becomes the editor value on the next render.
        if audio_file is not None:
            audio_bytes = audio_file.getvalue()
            audio_key = f"voice_{current}_{len(audio_bytes)}_{hash(audio_bytes)}"

            if st.session_state.get("last_audio_key") != audio_key:
                st.session_state.last_audio_key = audio_key
                with st.spinner("🎧 Transcribing exactly what was recorded..."):
                    try:
                        transcript = transcribe_voice_answer(audio_file)
                        if transcript and transcript != "[NO_SPEECH]":
                            st.session_state.answer = transcript
                            st.session_state.answer_editor = transcript
                            st.session_state.answer_editor_audio_key = audio_key
                            st.success("✅ Transcript ready. Please review it before submitting.")
                        else:
                            st.session_state.answer = ""
                            st.session_state.answer_editor = ""
                            st.warning("No clear speech was detected. Please record the answer again or type it manually.")
                    except Exception as e:
                        st.error(f"Could not transcribe the voice answer: {e}")

        final_answer = st.text_area(
            "Review your answer",
            height=190,
            key="answer_editor",
            placeholder="Type your answer here, or your voice transcript will appear here.",
        )
        st.session_state.answer = final_answer

        submit_col, clear_col = st.columns([3, 1])
        with submit_col:
            if st.button("✅ Submit Answer for AI Evaluation", use_container_width=True, type="primary"):
                if not final_answer.strip():
                    st.warning("Please write or record an answer before submitting.")
                else:
                    with st.spinner("🤖 AI is analyzing your answer..."):
                        try:
                            feedback = evaluate_answer(
                                st.session_state.job_role,
                                st.session_state.question,
                                final_answer,
                            )
                            numeric_score = float(feedback.get("score", 0))
                            st.session_state.answer = final_answer
                            st.session_state.feedback = feedback
                            st.session_state.scores.append(numeric_score)
                            st.session_state.answer_submitted = True

                            feedback_for_db = json.dumps(feedback, ensure_ascii=False)
                            save_interview(
                                st.session_state.user_id,
                                st.session_state.job_role,
                                st.session_state.field,
                                st.session_state.experience,
                                st.session_state.interview_type,
                                st.session_state.difficulty,
                                st.session_state.question,
                                final_answer,
                                numeric_score,
                                feedback_for_db,
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Could not evaluate answer: {e}")
        with clear_col:
            st.button(
                "🧹 Clear",
                use_container_width=True,
                on_click=clear_answer_editor,
            )

    if st.session_state.answer_submitted and st.session_state.feedback:
        feedback = st.session_state.feedback
        st.divider()
        st.markdown("### 🤖 AI Evaluation")

        score = feedback.get("score", 0)
        technical_score = feedback.get("technical_score", 0)
        communication_score = feedback.get("communication_score", 0)
        clarity_score = feedback.get("clarity_score", 0)
        structure_score = feedback.get("structure_score", 0)
        confidence_score = feedback.get("confidence_score", 0)

        score_col, summary_col = st.columns([1, 3])
        with score_col:
            st.metric("Overall Score", f"{score}/10")
        with summary_col:
            if score >= 8:
                st.success("🌟 Strong answer. Keep this level of preparation.")
            elif score >= 6:
                st.info("👍 Good attempt. A few improvements can make it stronger.")
            else:
                st.warning("💡 Keep practicing and focus on the improvement areas.")

        st.divider()
        st.markdown("### 📊 Interview Skills")
        skill1, skill2, skill3, skill4, skill5 = st.columns(5)
        with skill1:
            st.metric("🧠 Technical", f"{technical_score}/10")
        with skill2:
            st.metric("💬 Communication", f"{communication_score}/10")
        with skill3:
            st.metric("🔍 Clarity", f"{clarity_score}/10")
        with skill4:
            st.metric("🧩 Structure", f"{structure_score}/10")
        with skill5:
            st.metric("🎤 Confidence", f"{confidence_score}/10")

        st.divider()
        analysis_col1, analysis_col2 = st.columns(2)
        with analysis_col1:
            st.markdown("### ✅ Good Points")
            good_points = feedback.get("good_points", [])
            if good_points:
                for item in good_points:
                    st.write(f"• {item}")
            else:
                st.write("No specific good points returned.")
        with analysis_col2:
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
        st.info(feedback.get("better_answer", "No improved answer was returned."))

        st.divider()

        if current < total:
            if st.button("➡️ Next Question", use_container_width=True, type="primary"):
                st.session_state.current_question += 1
                with st.spinner("🤖 AI is preparing your next question..."):
                    try:
                        generate_next_question()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not generate next question: {e}")
        else:
            st.success("🎉 Interview completed!")
            if st.session_state.scores:
                final_average = sum(st.session_state.scores) / len(st.session_state.scores)
                st.metric("Interview Average Score", f"{final_average:.1f}/10")
            if st.button("🔄 Start New Interview", use_container_width=True):
                clear_current_interview_state()
                st.rerun()

# =========================================================
# PROGRESS
# =========================================================

elif page == "📊 Progress":
    st.markdown('<div class="hero-title">📊 Analytics & Skill Gap</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Understand your interview performance across key skills and identify areas to practice.</div>',
        unsafe_allow_html=True,
    )

    if not interviews:
        st.info("No interview data available yet. Complete an interview to unlock your analytics.")
    else:
        progress_scores = []
        skill_values = {
            "Technical": [],
            "Communication": [],
            "Clarity": [],
            "Structure": [],
            "Confidence": [],
        }

        for item in interviews:
            try:
                progress_scores.append(float(item[8]))
            except Exception:
                pass

            try:
                feedback_data = get_feedback_dict(item[9])
                for key, label in [
                    ("technical_score", "Technical"),
                    ("communication_score", "Communication"),
                    ("clarity_score", "Clarity"),
                    ("structure_score", "Structure"),
                    ("confidence_score", "Confidence"),
                ]:
                    value = float(feedback_data.get(key, 0))
                    if 0 <= value <= 10:
                        skill_values[label].append(value)
            except Exception:
                continue

        if progress_scores:
            average = sum(progress_scores) / len(progress_scores)
            best = max(progress_scores)
            latest = progress_scores[0]

            # Top-level analytics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Questions Completed", len(progress_scores))
            with col2:
                st.metric("Average Score", f"{average:.1f}/10")
            with col3:
                st.metric("Best Score", f"{best:.1f}/10")
            with col4:
                st.metric("Latest Score", f"{latest:.1f}/10")

            st.divider()

            # Skill analytics
            st.markdown("### 🧠 Skill Performance")
            skill_averages = {
                skill: (sum(values) / len(values) if values else 0)
                for skill, values in skill_values.items()
            }

            skill_chart = pd.DataFrame(
                {"Skill": list(skill_averages.keys()), "Average Score": list(skill_averages.values())}
            ).set_index("Skill")

            if any(skill_averages.values()):
                st.bar_chart(skill_chart, height=320)
            else:
                st.info("Skill-level analytics will appear after answers with detailed AI feedback are saved.")

            metric_cols = st.columns(5)
            skill_icons = {
                "Technical": "🧠",
                "Communication": "💬",
                "Clarity": "🔍",
                "Structure": "🧩",
                "Confidence": "🎤",
            }
            for col, skill in zip(metric_cols, skill_averages):
                with col:
                    value = skill_averages[skill]
                    display = f"{value:.1f}/10" if skill_values[skill] else "N/A"
                    st.metric(f"{skill_icons[skill]} {skill}", display)

            st.divider()

            # Focus areas / skill-gap analysis
            st.markdown("### 🎯 Skill Gap Analysis")
            valid_skills = {
                skill: score for skill, score in skill_averages.items()
                if skill_values[skill]
            }

            if valid_skills:
                lowest_skills = sorted(valid_skills.items(), key=lambda x: x[1])[:2]

                gap_col1, gap_col2 = st.columns(2)
                with gap_col1:
                    st.markdown("#### 📌 Focus Areas")
                    for skill, score in lowest_skills:
                        if score < 6:
                            status = "Needs more practice"
                        elif score < 8:
                            status = "Good foundation — keep improving"
                        else:
                            status = "Maintain consistency"
                        st.write(f"**{skill}: {score:.1f}/10** — {status}")

                with gap_col2:
                    st.markdown("#### 💡 Practice Guidance")
                    guidance = {
                        "Technical": "Review core concepts and practice explaining your reasoning step by step.",
                        "Communication": "Practice concise, professional answers and avoid unnecessary repetition.",
                        "Clarity": "Lead with your main point, then support it with a short example or explanation.",
                        "Structure": "Organize answers with a clear beginning, key details, and a conclusion.",
                        "Confidence": "Practice answering directly and support your statements with specific examples.",
                    }
                    shown = set()
                    for skill, _ in lowest_skills:
                        if skill not in shown:
                            st.write(f"**{skill}:** {guidance[skill]}")
                            shown.add(skill)
            else:
                st.info("Complete more evaluated answers to generate your skill-gap analysis.")

            st.divider()

            # Overall performance trend
            st.markdown("### 📈 Overall Performance Trend")
            trend_data = pd.DataFrame(
                {
                    "Question": range(1, len(progress_scores) + 1),
                    "Overall Score": progress_scores,
                }
            ).set_index("Question")
            st.line_chart(trend_data, height=320)

            # Recent vs previous performance
            if len(progress_scores) >= 4:
                recent_count = min(5, len(progress_scores) // 2)
                recent = progress_scores[:recent_count]
                previous = progress_scores[recent_count:recent_count * 2]

                if previous:
                    recent_avg = sum(recent) / len(recent)
                    previous_avg = sum(previous) / len(previous)
                    change = recent_avg - previous_avg

                    st.divider()
                    st.markdown("### 🔄 Recent Performance")
                    recent_col1, recent_col2, recent_col3 = st.columns(3)
                    with recent_col1:
                        st.metric("Recent Average", f"{recent_avg:.1f}/10")
                    with recent_col2:
                        st.metric("Previous Average", f"{previous_avg:.1f}/10")
                    with recent_col3:
                        st.metric("Difference", f"{change:+.1f}")

            st.divider()

            # Practice guidance
            st.markdown("### 🧭 What To Practice")
            practice1, practice2, practice3 = st.columns(3)
            with practice1:
                st.markdown(
                    '<div class="feature-card"><div class="feature-icon">🧠</div><div class="feature-title">Technical Knowledge</div><div class="feature-text">Review job-related concepts and practice explaining how you solve problems.</div></div>',
                    unsafe_allow_html=True,
                )
            with practice2:
                st.markdown(
                    '<div class="feature-card"><div class="feature-icon">💬</div><div class="feature-title">Communication</div><div class="feature-text">Keep answers concise, professional and easy to follow.</div></div>',
                    unsafe_allow_html=True,
                )
            with practice3:
                st.markdown(
                    '<div class="feature-card"><div class="feature-icon">🧩</div><div class="feature-title">Answer Structure</div><div class="feature-text">Use a logical structure and support important points with examples.</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No valid scores are available yet.")

# =========================================================
# HISTORY
# =========================================================

elif page == "📝 History":
    st.markdown('<div class="hero-title">📝 Interview History</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Review previous questions, answers and AI feedback.</div>',
        unsafe_allow_html=True,
    )

    if not interviews:
        st.info("No interview history yet.")
    else:
        history_col1, history_col2 = st.columns(2)
        with history_col1:
            st.metric("Saved Responses", len(interviews))
        with history_col2:
            try:
                history_avg = sum(float(item[8]) for item in interviews) / len(interviews)
                st.metric("Average Saved Score", f"{history_avg:.1f}/10")
            except Exception:
                st.metric("Average Saved Score", "N/A")

        st.divider()

        for index, item in enumerate(interviews, start=1):
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

            with st.expander(f"#{index}  🎯 {job_role} — Score: {score}/10"):
                meta1, meta2, meta3 = st.columns(3)
                with meta1:
                    st.write(f"**Field:** {field}")
                    st.write(f"**Experience:** {experience}")
                with meta2:
                    st.write(f"**Interview Type:** {interview_type}")
                    st.write(f"**Difficulty:** {difficulty}")
                with meta3:
                    st.write(f"**Date:** {created_at}")

                st.divider()
                st.markdown("### ❓ Question")
                st.info(question)

                st.markdown("### ✍️ Your Answer")
                st.write(answer)

                st.markdown("### 🤖 AI Feedback")
                feedback_data = get_feedback_dict(feedback)

                if feedback_data:
                    feedback_score = feedback_data.get("score", score)
                    st.metric("Overall Score", f"{feedback_score}/10")

                    s1, s2, s3, s4, s5 = st.columns(5)
                    with s1:
                        st.metric("Technical", f"{feedback_data.get('technical_score', 0)}/10")
                    with s2:
                        st.metric("Communication", f"{feedback_data.get('communication_score', 0)}/10")
                    with s3:
                        st.metric("Clarity", f"{feedback_data.get('clarity_score', 0)}/10")
                    with s4:
                        st.metric("Structure", f"{feedback_data.get('structure_score', 0)}/10")
                    with s5:
                        st.metric("Confidence", f"{feedback_data.get('confidence_score', 0)}/10")

                    good_points = feedback_data.get("good_points", [])
                    missing_points = feedback_data.get("missing_points", [])
                    improvements = feedback_data.get("improvements", [])

                    feedback_col1, feedback_col2 = st.columns(2)
                    with feedback_col1:
                        st.markdown("**✅ Good Points**")
                        for point in good_points:
                            st.write(f"• {point}")
                    with feedback_col2:
                        st.markdown("**⚠️ Missing Points**")
                        for point in missing_points:
                            st.write(f"• {point}")

                    st.markdown("**💡 Improvements**")
                    for point in improvements:
                        st.write(f"• {point}")

                    st.markdown("**✨ Better Answer**")
                    st.info(feedback_data.get("better_answer", ""))
                else:
                    st.write(feedback)
