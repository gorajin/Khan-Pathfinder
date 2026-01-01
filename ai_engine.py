import os
import json
import streamlit as st
from google import genai
from google.genai import types

# Lazy client initialization to work with Streamlit Cloud secrets
_client = None

def get_client():
    global _client
    if _client is None:
        # Try Streamlit secrets first (for Streamlit Cloud), then environment variable (for local)
        try:
            api_key = st.secrets["GEMINI_API_KEY"]
        except (KeyError, FileNotFoundError):
            api_key = os.environ.get("GEMINI_API_KEY")
        
        if not api_key:
            st.error("⚠️ GEMINI_API_KEY not found! Add it to .streamlit/secrets.toml or set as environment variable.")
            st.stop()
        
        _client = genai.Client(api_key=api_key)
    return _client

def generate_question(standard_id, description, error_context=None):
    prompt = f"""
    Create a 7th-grade math word problem for Standard: {standard_id} - {description}.
    
    CONTEXT:
    - Theme: Space Exploration, Video Games, or Sports.
    - {f"PREVIOUS ERROR: Student failed due to {error_context}. Make this question simpler (scaffolding)." if error_context else "Difficulty: Medium."}
    
    FORMATTING RULES:
    - Use LaTeX for all math expressions (enclose in single dollar signs, e.g., $x^2 + 5$).
    
    OUTPUT JSON FORMAT ONLY:
    {{
        "question_text": "The word problem text...",
        "correct_answer": "The correct option text",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "analysis": {{
            "Option A": "Why this is wrong (specific misconception)...",
            "Option B": "Why this is wrong...",
            "Option C": "Why this is wrong..."
        }}
    }}
    """
    
    try:
        response = get_client().models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        result = json.loads(response.text)
        # Handle case where API returns a list instead of dict
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        return result if isinstance(result, dict) else {
            "question_text": "Error: Unexpected API response format.",
            "options": ["Error"],
            "correct_answer": "Error",
            "analysis": {"Error": f"Got {type(result)} instead of dict"}
        }
    except Exception as e:
        return {
            "question_text": "Error generating question. Please check API Key.",
            "options": ["Error"],
            "correct_answer": "Error",
            "analysis": {"Error": str(e)}
        }

def diagnose_gap(question_text, wrong_answer, standard_id):
    prompt = f"""
    Task: Diagnose the student's error.
    Standard: {standard_id}
    Question: {question_text}
    Student Answer: {wrong_answer}
    
    Decide which category best describes the error:
    1. 'ARITHMETIC' - Calculation error, integer/decimal mistake, sign error
    2. 'CONCEPTUAL' - Misunderstanding the core concept, wrong formula, logic error
    3. 'ALGEBRAIC' - Equation manipulation error, variable isolation mistake, slope/intercept confusion
    4. 'SKILL' - Procedural error, missing a step, applying wrong procedure
    5. 'GRAPHICAL' - Misreading or plotting graphs incorrectly, coordinate errors
    6. 'GEOMETRIC' - Shape/angle misconception, area/perimeter confusion, spatial reasoning error
    
    OUTPUT JSON ONLY:
    {{
        "error_type": "ARITHMETIC" or "CONCEPTUAL" or "ALGEBRAIC" or "SKILL" or "GRAPHICAL" or "GEOMETRIC",
        "explanation": "Brief explanation for the teacher."
    }}
    """
    
    try:
        response = get_client().models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        result = json.loads(response.text)
        # Handle case where API returns a list instead of dict
        if isinstance(result, list) and len(result) > 0:
            result = result[0]
        return result if isinstance(result, dict) else {"error_type": "CONCEPTUAL", "explanation": "Unexpected response format."}
    except Exception as e:
        return {"error_type": "CONCEPTUAL", "explanation": "API Error, defaulting to Conceptual."}

def generate_hint(question_text):
    """Generate a pedagogical hint without revealing the answer."""
    prompt = f"""
    You are a helpful tutor. The student is stuck on this problem:
    "{question_text}"
    
    Provide a concise HINT. 
    - Do NOT solve it.
    - Do NOT give the answer.
    - Just give the first conceptual step.
    - Use LaTeX for math (e.g., $x^2$).
    """
    try:
        response = get_client().models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return response.text
    except Exception:
        return "Review the properties of operations and try again."

