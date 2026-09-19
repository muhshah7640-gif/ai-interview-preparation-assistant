import os
import json
from google import genai


# =========================================================
# GEMINI CONFIGURATION
# =========================================================

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "GEMINI_API_KEY was not found. "
        "Please set it in Windows Environment Variables."
    )

client = genai.Client(api_key=api_key)

MODEL = "gemini-3.6-flash"


# =========================================================
# SAFE GEMINI REQUEST
# =========================================================

def safe_generate_content(prompt):

    try:

        response = client.models.generate_content(
            model=MODEL,
            contents=prompt
        )

        if response is None:
            raise RuntimeError(
                "Gemini returned an empty response."
            )

        if not response.text:
            raise RuntimeError(
                "Gemini returned no text response."
            )

        return response

    except Exception as e:

        error_message = str(e)

        # Show quota / rate-limit problem clearly
        if (
            "429" in error_message
            or "RESOURCE_EXHAUSTED" in error_message
        ):
            raise RuntimeError(
                "Gemini API quota or request limit has been reached. "
                "Please try again after the quota resets."
            )

        # Show the actual error instead of hiding it
        raise RuntimeError(
            f"Gemini API error: {error_message}"
        )


# =========================================================
# GENERATE INTERVIEW QUESTION
# =========================================================

def generate_question(
    job_role,
    field,
    experience,
    interview_type,
    difficulty,
    resume_text=""
):

    # -----------------------------------------------------
    # Prepare resume information
    # -----------------------------------------------------

    if resume_text and resume_text.strip():

        resume_section = f"""
Candidate Resume:
{resume_text[:3000]}
"""

    else:

        resume_section = """
Candidate Resume:
No resume was provided.
"""

    # -----------------------------------------------------
    # Prompt
    # -----------------------------------------------------

    prompt = f"""
You are a professional AI interviewer conducting a realistic
job interview.

Generate ONE realistic interview question.

Candidate information:

Job Role: {job_role}
Field: {field}
Experience Level: {experience}
Interview Type: {interview_type}
Difficulty: {difficulty}

{resume_section}

Rules:

1. Make the question relevant to the selected job role and field.
2. Match the selected interview type.
3. Match the selected difficulty level.
4. If a resume is provided, personalize the question using
   the candidate's skills, education, projects, certifications,
   or experience.
5. Do not invent information that is not present in the resume.
6. If no resume is provided, generate a normal interview question.
7. Ask only ONE question.
8. Do not provide the answer.
9. Do not explain the question.
10. Return ONLY the interview question.

Generate the question now.
"""

    response = safe_generate_content(prompt)

    question = response.text.strip()

    if not question:
        raise RuntimeError(
            "Gemini generated an empty interview question."
        )

    return question


# =========================================================
# EVALUATE CANDIDATE ANSWER
# =========================================================

def evaluate_answer(
    job_role,
    question,
    answer
):

    prompt = f"""
You are a professional interview evaluator.

Job Role:
{job_role}

Interview Question:
{question}

Candidate Answer:
{answer}

Evaluate the candidate's answer.

Return ONLY valid JSON in exactly this format:

{{
    "score": 8,
    "good_points": [
        "Good point 1",
        "Good point 2"
    ],
    "missing_points": [
        "Missing point 1",
        "Missing point 2"
    ],
    "improvements": [
        "Improvement 1",
        "Improvement 2"
    ],
    "better_answer": "A clear and professional improved answer."
}}

Rules:

- Score must be a number from 0 to 10.
- Give constructive feedback.
- Do not be unnecessarily harsh.
- The better answer should directly answer the question.
- Return ONLY JSON.
"""

    response = safe_generate_content(prompt)

    result = response.text.strip()

    # -----------------------------------------------------
    # Remove markdown code fences
    # -----------------------------------------------------

    if result.startswith("```"):

        result = result.replace("```json", "")
        result = result.replace("```", "")
        result = result.strip()

    # -----------------------------------------------------
    # Convert JSON to Python dictionary
    # -----------------------------------------------------

    try:

        return json.loads(result)

    except json.JSONDecodeError:

        return {
            "score": 0,
            "good_points": [],
            "missing_points": [],
            "improvements": [
                "AI returned an unexpected response format."
            ],
            "better_answer": result
        }