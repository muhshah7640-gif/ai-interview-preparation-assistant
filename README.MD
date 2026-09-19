# AI Interview Preparation Assistant SaaS

An AI-powered SaaS application that helps users prepare for job interviews through personalized interview questions, AI feedback, scoring, and interview history.

## Features

- Personalized interview preparation
- Supports different job roles and fields
- Experience-level selection
- Interview type selection
- Difficulty selection
- AI-generated interview questions
- AI evaluation of user answers
- Score and detailed feedback
- Suggestions for improvement
- Better-answer suggestions
- Interview history
- Progress tracking
- CV/resume parsing
- SQLite database
- Streamlit web interface
- Gemini AI integration

## Technologies Used

- Python
- Streamlit
- Google Gemini API
- SQLite
- Pandas
- Python-dotenv
- Resume parsing

## Project Structure

- `app.py` — Main Streamlit application
- `ai_engine.py` — AI question generation and answer evaluation
- `auth.py` — Authentication functionality
- `database.py` — Database operations
- `resume_parser.py` — Resume/CV processing
- `style.css` — Application styling
- `requirements.txt` — Python dependencies
- `.gitignore` — Protects private files

## How to Run

1. Clone the repository.
2. Create and activate a Python virtual environment.
3. Install dependencies:

```bash
pip install -r requirements.txt