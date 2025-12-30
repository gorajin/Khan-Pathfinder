import streamlit as st
import json
import os
import ai_engine

# Page Config
st.set_page_config(page_title="Khan Pathfinder", page_icon="🧭")

# 1. Load Curriculum
with open('curriculum.json', 'r') as f:
    curriculum = json.load(f)

# 2. Setup Session State
if 'current_standard' not in st.session_state:
    st.session_state.current_standard = "7.EE.B.4a"
if 'mode' not in st.session_state:
    st.session_state.mode = "ASSESSMENT" 
if 'current_question' not in st.session_state:
    st.session_state.current_question = None

# 3. Sidebar UI (The Map)
st.sidebar.title("🗺️ Knowledge Map")
st.sidebar.markdown(f"**Current Level:** `{st.session_state.current_standard}`")
if st.session_state.mode == "REMEDIATION":
    st.sidebar.error("⚠️ Gap Detected! Diverting to prerequisites.")
    if st.sidebar.button("Reset to Grade Level"):
        st.session_state.current_standard = "7.EE.B.4a"
        st.session_state.mode = "ASSESSMENT"
        st.session_state.current_question = None
        st.rerun()
else:
    st.sidebar.success("✅ On Track")

# 4. Main App Logic
st.title("Khan Academy Candidate: Diagnostic Prototype")
st.caption("A Generative Assessment Engine that detects 'Skill Gaps' vs 'Logic Gaps'")

std_data = curriculum[st.session_state.current_standard]
st.subheader(f"🎯 Objective: {std_data['description']}")

# Check for API Key
if not st.secrets.get("GEMINI_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
    st.warning("⚠️ No Gemini API Key found. Please add it to .streamlit/secrets.toml")
    st.stop()

# Generate Question
if not st.session_state.current_question:
    with st.spinner("AI is crafting a unique problem..."):
        q_data = ai_engine.generate_question(
            st.session_state.current_standard, 
            std_data['description'],
            error_context="Previous failure" if st.session_state.mode == "REMEDIATION" else None
        )
        st.session_state.current_question = q_data

# Display Question
q = st.session_state.current_question
st.write(q.get('question_text', "Error loading question."))

# User Input
options = q.get('options', [])
user_answer = st.radio("Choose your answer:", options, key="ans")

if st.button("Submit Answer"):
    if user_answer == q['correct_answer']:
        st.balloons()
        st.success("Correct! Great work.")
        if st.button("Next Problem"):
            st.session_state.current_question = None
            st.rerun()
    else:
        st.error(f"Incorrect. The answer was {q['correct_answer']}.")
        
        # DIAGNOSIS ENGINE
        with st.spinner("Analyzing your learning gap..."):
            diagnosis = ai_engine.diagnose_gap(
                q['question_text'], 
                user_answer, 
                st.session_state.current_standard
            )
            
            error_type = diagnosis.get('error_type', 'CONCEPTUAL')
            st.info(f"AI Diagnosis: {diagnosis.get('explanation', '')}")
            
            # Auto-Route to Prerequisite
            prereqs = std_data.get('prerequisites', {})
            if error_type in prereqs:
                new_standard = prereqs[error_type]
                st.warning(f"📉 Routing to foundation skill: {new_standard}")
                
                # Update State
                st.session_state.current_standard = new_standard
                st.session_state.mode = "REMEDIATION"
                st.session_state.current_question = None 
                st.rerun()

# Teacher Debug View
with st.expander("👨‍🏫 Teacher / Developer View (Debug)"):
    st.json(q)
