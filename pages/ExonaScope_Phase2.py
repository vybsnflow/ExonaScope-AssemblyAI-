import streamlit as st
import json
import os

# ---------- GPT UTILITY ----------
def gpt_call(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "system", "content": "You are a precise legal assistant."},
                  {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# ---------- GENERATION LOGIC ----------
def generate_suppression_issues(facts, tags):
    import ast
    prompt = f"""
You are a criminal defense attorney. Given the following raw facts and tagged legal events, identify plausible suppression issues for a motion to suppress. For each issue, give:
- A short title (e.g., "Unlawful Stop")
- A 1-2 sentence explanation

Facts:
{facts}

Tagged Events:
{tags}

Return a JSON list with "title" and "explanation" fields.
"""
    try:
        result = gpt_call(prompt)
        st.write("AI output (Suppression Issues):", result)
        issues = json.loads(result)
    except Exception:
        try:
            issues = ast.literal_eval(result)
        except Exception:
            issues = []
    return [i for i in issues if "title" in i and "explanation" in i]

def generate_defenses(facts, tags):
    import ast
    prompt = f"""
You are a criminal defense strategist. Based on the facts and tagged legal events, list plausible defenses that could be raised (aside from suppression issues). For each, give:
- A short title (e.g., "Alibi")
- A brief explanation (1-2 sentences)

Facts:
{facts}

Tagged Events:
{tags}

Return a JSON list with "title" and "explanation" fields.
"""
    try:
        result = gpt_call(prompt)
        st.write("AI output (Defenses):", result)
        defenses = json.loads(result)
    except Exception:
        try:
            defenses = ast.literal_eval(result)
        except Exception:
            defenses = []
    return [d for d in defenses if "title" in d and "explanation" in d]

# ---------- UI START ----------
st.title("ExonaScope Phase 2 – Automated Issue & Defense Generation")

# Store or retrieve case data
case_name = st.text_input("Case Name", value=st.session_state.get("case_name", ""))
case_number = st.text_input("Case Number", value=st.session_state.get("case_number", ""))
facts = st.text_area("Raw Facts", value=st.session_state.get("phase2_facts", ""), height=150)
tags = st.text_area("Tagged Legal Events", value=st.session_state.get("phase2_tags", ""), height=100)

# Save info
st.session_state["case_name"] = case_name
st.session_state["case_number"] = case_number
st.session_state["phase2_facts"] = facts
st.session_state["phase2_tags"] = tags

# Initialize data structure if not already
if "phase2_issues" not in st.session_state:
    st.session_state["phase2_issues"] = []
if "phase2_defenses" not in st.session_state:
    st.session_state["phase2_defenses"] = []
if "defense_attempted" not in st.session_state:
    st.session_state["defense_attempted"] = False
if "issues_attempted" not in st.session_state:
    st.session_state["issues_attempted"] = False

# ---------- BUTTONS TO GENERATE ----------
col1, col2 = st.columns(2)

with col1:
    if st.button("🔍 Auto-Generate Suppression Issues", key="auto_issues"):
        st.session_state["issues_attempted"] = True
        with st.spinner("Generating suppression issues..."):
            issues = generate_suppression_issues(facts, tags)
        if issues:
            st.session_state["phase2_issues"] = issues
            st.success("Suppression issues generated!")
        else:
            st.warning("No suppression issues generated. Review the facts and try again.")

with col2:
    if st.button("🛡️ Auto-Generate Defenses", key="auto_defenses"):
        st.session_state["defense_attempted"] = True
        with st.spinner("Generating defenses..."):
            defenses = generate_defenses(facts, tags)
        if defenses:
            st.session_state["phase2_defenses"] = defenses
            st.success("Defenses generated!")
        else:
            st.session_state["phase2_defenses"] = []

# Only show warning if user clicked button but defenses are empty
if st.session_state["defense_attempted"] and not st.session_state.get("phase2_defenses"):
    st.warning("No defenses generated. Please review the facts and try again.")

# ---------- REVIEW & EDIT ISSUES ----------
st.subheader("📑 Suppression Issues")

if st.button("➕ Add New Issue", key="add_issue"):
    st.session_state["phase2_issues"].append({"title": "", "explanation": ""})

for idx, issue in enumerate(st.session_state["phase2_issues"]):
    st.text_input(f"Issue {idx+1} Title", value=issue["title"], key=f"issue_title_{idx}")
    st.text_area(f"Issue {idx+1} Explanation", value=issue["explanation"], key=f"issue_expl_{idx}")
    if st.button(f"❌ Remove Issue {idx+1}", key=f"remove_issue_{idx}"):
        st.session_state["phase2_issues"].pop(idx)
        st.experimental_rerun()

# ---------- REVIEW & EDIT DEFENSES ----------
st.subheader("⚖️ Potential Defenses")

if st.button("➕ Add New Defense", key="add_defense"):
    st.session_state["phase2_defenses"].append({"title": "", "explanation": ""})

for idx, defense in enumerate(st.session_state["phase2_defenses"]):
    st.text_input(f"Defense {idx+1} Title", value=defense["title"], key=f"defense_title_{idx}")
    st.text_area(f"Defense {idx+1} Explanation", value=defense["explanation"], key=f"defense_expl_{idx}")
    if st.button(f"❌ Remove Defense {idx+1}", key=f"remove_defense_{idx}"):
        st.session_state["phase2_defenses"].pop(idx)
        st.experimental_rerun()

# ---------- MOTION FACT SUMMARY ----------
def summarize_facts_for_motion(raw_facts, tagged_events):
    prompt = f"""
You are a legal writing assistant. Based on the following, summarize the facts into a concise, professional narrative suitable for the 'Statement of Facts' in a legal motion.

Raw Facts:
{raw_facts}

Tagged Events:
{tagged_events}

Keep it chronologically structured and legally neutral.
"""
    return gpt_call(prompt)

if st.button("📝 Summarize Facts for Motion", key="summarize_facts"):
    with st.spinner("Summarizing facts..."):
        summarized_facts = summarize_facts_for_motion(facts, tags)
    st.session_state["motion_facts"] = summarized_facts

if "motion_facts" in st.session_state:
    st.subheader("📖 Summarized Facts for Motion")
    facts_editable = st.text_area("Edit Summary (if desired):", value=st.session_state["motion_facts"], height=200, key="edit_facts")
    st.session_state["motion_facts"] = facts_editable

# ---------- PUSH TO PHASE 3 ----------
st.subheader("⬇️ Export Phase 2 Data")

if st.button("Push to Phase 3", key="push_phase3"):
    output_data = {
        "case_name": st.session_state.get("case_name", ""),
        "case_number": st.session_state.get("case_number", ""),
        "phase2_facts": st.session_state.get("phase2_facts", ""),
        "phase2_tags": st.session_state.get("phase2_tags", ""),
        "phase2_issues": st.session_state.get("phase2_issues", []),
        "phase2_defenses": st.session_state.get("phase2_defenses", []),
        "motion_facts": st.session_state.get("motion_facts", "")
    }
    json_bytes = json.dumps(output_data, indent=2).encode("utf-8")
    st.download_button(
        label="Download → Phase 3 (.json)",
        data=json_bytes,
        file_name="phase2_to_phase3.json",
        mime="application/json",
        key="phase3_dl"
    )
    st.success("Data prepared for Phase 3! Please upload the JSON file there.")

# ---------- DEBUGGING SESSION STATE ----------
if st.checkbox("🧪 Show Session State (Debug)", key="debug"):
    st.json(dict(st.session_state))
