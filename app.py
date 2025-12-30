import streamlit as st
import json
import ai_engine

# --- PAGE CONFIG ---
st.set_page_config(page_title="Khan MS Math Navigator", page_icon="🗺️", layout="wide")

# --- CUSTOM CSS FOR BETTER TEXT SIZING ---
st.markdown("""
<style>
    /* Reduce main title size */
    h1 {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        line-height: 1.3 !important;
    }
    
    /* Reduce subheader sizes */
    h2 {
        font-size: 1.25rem !important;
    }
    
    h3 {
        font-size: 1.1rem !important;
    }
    
    /* Sidebar info box - smaller text */
    .stSidebar [data-testid="stAlert"] {
        font-size: 0.85rem !important;
        padding: 0.5rem 0.75rem !important;
    }
    
    .stSidebar [data-testid="stAlert"] p {
        font-size: 0.85rem !important;
        line-height: 1.4 !important;
    }
    
    /* Sidebar header */
    .stSidebar h2 {
        font-size: 1.1rem !important;
    }
    
    /* Sidebar subheader */
    .stSidebar h3 {
        font-size: 0.95rem !important;
    }
    
    /* Caption text - slightly larger for readability */
    .stCaption {
        font-size: 0.8rem !important;
    }
    
    /* General markdown text in main area */
    .stMarkdown p {
        font-size: 0.95rem !important;
        line-height: 1.6 !important;
    }
    
    /* Tab labels */
    .stTabs [data-baseweb="tab"] {
        font-size: 0.9rem !important;
    }
</style>
""", unsafe_allow_html=True)

# --- LOAD CURRICULUM ---
@st.cache_data
def load_curriculum():
    with open('curriculum.json', 'r') as f:
        return json.load(f)

data = load_curriculum()
curriculum = data['nodes']
strands = data['strands']

# --- SESSION STATE ---
if 'current_std' not in st.session_state: st.session_state.current_std = "8.F.B.4" 
if 'student_q' not in st.session_state: st.session_state.student_q = None

# --- SIDEBAR: THE CURRICULUM BROWSER ---
st.sidebar.header("📚 MS Math Curriculum")

# 1. Strand Selector (The Vertical Filter)
selected_strand_key = st.sidebar.selectbox(
    "Select Learning Domain:", 
    list(strands.keys()),
    format_func=lambda x: strands[x]['name']
)
selected_strand = strands[selected_strand_key]

st.sidebar.info(f"**Focus:** {selected_strand['description']}")
st.sidebar.markdown("---")

# 2. The Standard Ladder (Sorted by Grade 8 -> 6)
strand_nodes = [curriculum[sid] for sid in selected_strand['standards'] if sid in curriculum]
strand_nodes.sort(key=lambda x: x['grade'], reverse=True)

st.sidebar.subheader("📍 Progression Path")
for node in strand_nodes:
    label = f"{node['id']} (Gr {node['grade']})"
    if node['id'] == st.session_state.current_std:
        # Feature #2: Enhanced Standard Highlighting with green background
        st.sidebar.markdown(
            f"""<div style="background-color:#d4edda; padding:10px; border-radius:5px; border-left: 5px solid #28a745; margin-bottom: 8px;">
                <strong>👉 {label}</strong><br><small>{node['description'][:50]}...</small>
            </div>""", 
            unsafe_allow_html=True
        )
    else:
        if st.sidebar.button(label, key=f"nav_{node['id']}"):
            st.session_state.current_std = node['id']
            st.session_state.student_q = None 
            st.rerun()

# --- MAIN APP LOGIC ---
curr_node = curriculum[st.session_state.current_std]

st.caption(f"Domain: {selected_strand['name']} > Grade {curr_node['grade']}")
st.title(f"{curr_node['id']}: {curr_node['description']}")

# TABS
tab_practice, tab_map = st.tabs(["🎓 Adaptive Practice", "🔗 Vertical Alignment Map"])

# --- TAB 1: PRACTICE ---
with tab_practice:
    if not st.session_state.student_q:
        with st.spinner(f"AI is crafting a {curr_node['id']} problem..."):
            st.session_state.student_q = ai_engine.generate_question(
                curr_node['id'], curr_node['description']
            )

    q = st.session_state.student_q
    if q and "question_text" in q:
        st.markdown(f"**Problem:** {q['question_text']}")
        opts = q.get('options', ["Error"])
        ans = st.radio("Your Answer:", opts, key="main_q")
        
        # Feature #5: Interactive Hint System
        col_hint, col_submit = st.columns([1, 1])
        with col_hint:
            if st.button("💡 Need a Hint?", use_container_width=True):
                with st.spinner("Generating hint..."):
                    # Calls the engine instead of the raw client (proper separation of concerns)
                    hint_text = ai_engine.generate_hint(q['question_text'])
                    st.info(f"**💡 Hint:** {hint_text}")
        
        with col_submit:
            submit_clicked = st.button("Submit Answer", use_container_width=True, type="primary")
        
        if submit_clicked:
            if ans == q['correct_answer']:
                st.success("✅ Correct! Mastery Verified.")
                if st.button("Next Problem"):
                    st.session_state.student_q = None
                    st.rerun()
            else:
                # Feature #8: Clearer Fix Gap Navigation
                st.error("❌ Incorrect. The AI detected a gap in your foundation.")
                with st.spinner("Analyzing Gap..."):
                    diag = ai_engine.diagnose_gap(q['question_text'], ans, curr_node['id'])
                    st.info(f"**AI Insight:** {diag['explanation']}")
                    
                    err_type = diag.get('error_type', 'CONCEPTUAL')
                    prereqs = curr_node.get('prerequisites', {})
                    if err_type in prereqs:
                        gap_id = prereqs[err_type]
                        if gap_id in curriculum:
                            gap_node = curriculum[gap_id]
                            st.markdown(f"### 🚨 Critical Gap Found: {gap_node['id']}")
                            st.markdown(f"*{gap_node['description']}*")
                            # Big, prominent button to fix the gap
                            if st.button(f"🚑 Fix {gap_node['id']} Now", type="primary", use_container_width=True):
                                st.session_state.current_std = gap_id
                                st.session_state.student_q = None
                                st.rerun()

# --- TAB 2: THE MAP ---
with tab_map:
    st.markdown("### 🗺️ Where does this fit?")
    col1, col2, col3 = st.columns(3)
    
    with col2:
        st.markdown(f"**CURRENT:**\n\n`{curr_node['id']}`")
        st.caption(curr_node['description'])
    with col1:
        st.markdown("**FOUNDATIONS (Prerequisites):**")
        for r_type, pid in curr_node.get('prerequisites', {}).items():
            if pid in curriculum:
                p = curriculum[pid]
                if st.button(f"⬅️ Go to {pid} (Gr {p['grade']})", key=f"pre_{pid}"):
                     st.session_state.current_std = pid
                     st.session_state.student_q = None
                     st.rerun()
    with col3:
        st.markdown("**UNLOCKS (Post-requisites):**")
        unlocks = [n for nid, n in curriculum.items() if curr_node['id'] in n.get('prerequisites', {}).values()]
        for node in unlocks:
            if st.button(f"➡️ Go to {node['id']} (Gr {node['grade']})", key=f"post_{node['id']}"):
                 st.session_state.current_std = node['id']
                 st.session_state.student_q = None
                 st.rerun()
