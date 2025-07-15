import streamlit as st
import json
from docx import Document
from io import BytesIO
import os

# --- User Input Section ---
st.title("ExonaScope Phase 2 – Fact & Issue Collection")

# Collect case information
case_name = st.text_input("Case Name", value=st.session_state.get("case_name", ""))
case_number = st.text_input("Case Number", value=st.session_state.get("case_number", ""))

# Collect raw facts and tagged events
facts = st.text_area("Enter Raw Facts", value=st.session_state.get("phase2_facts", ""), height=150)
tags = st.text_area("Enter Tagged Legal Events", value=st.session_state.get("phase2_tags", ""), height=100)

# Collect suppression issues
st.subheader("Suppression Issues")
if "phase2_issues" not in st.session_state:
    st.session_state["phase2_issues"] = []
if st.button("Add Suppression Issue"):
    st.session_state["phase2_issues"].append({"title": "", "explanation": ""})

for i, issue in enumerate(st.session_state["phase2_issues"]):
    st.session_state["phase2_issues"][i]["title"] = st.text_input(f"Issue {i+1} Title", value=issue["title"], key=f"issue_title_{i}")
    st.session_state["phase2_issues"][i]["explanation"] = st.text_area(f"Issue {i+1} Explanation", value=issue["explanation"], key=f"issue_expl_{i}")

# Collect defenses
st.subheader("Potential Defenses")
if "phase2_defenses" not in st.session_state:
    st.session_state["phase2_defenses"] = []
if st.button("Add Defense"):
    st.session_state["phase2_defenses"].append({"title": "", "explanation": ""})

for j, defense in enumerate(st.session_state["phase2_defenses"]):
    st.session_state["phase2_defenses"][j]["title"] = st.text_input(f"Defense {j+1} Title", value=defense["title"], key=f"defense_title_{j}")
    st.session_state["phase2_defenses"][j]["explanation"] = st.text_area(f"Defense {j+1} Explanation", value=defense["explanation"], key=f"defense_expl_{j}")

# Save all data to session state
st.session_state["case_name"] = case_name
st.session_state["case_number"] = case_number
st.session_state["phase2_facts"] = facts
st.session_state["phase2_tags"] = tags

# --- Summarize Facts for Motion ---
def gpt_call(prompt):
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a precise legal assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def summarize_facts_for_motion(raw_facts, tagged_events):
    prompt = f"""
You are a legal writing assistant. Given the following raw facts and tagged legal events, write a concise, professional, and neutral summary of the facts suitable for the 'Statement of Facts' section of a legal motion. Focus on clarity, chronology, and relevance to the legal issues.

Raw Facts:
{raw_facts}

Tagged Events:
{tagged_events}

Return only the summarized facts, in narrative paragraph form.
"""
    return gpt_call(prompt)

if st.button("Summarize Facts for Motion"):
    with st.spinner("Summarizing facts for motion..."):
        summarized_facts = summarize_facts_for_motion(facts, tags)
    st.session_state["motion_facts"] = summarized_facts

# Display and allow editing of the summarized facts
if "motion_facts" in st.session_state:
    st.header("Summarized Facts for Motion")
    summarized_facts_editable = st.text_area(
        "Edit the summarized facts if needed:",
        value=st.session_state["motion_facts"],
        height=200,
        key="summarized_facts_editable"
    )
    st.session_state["motion_facts"] = summarized_facts_editable

# --- Push to Phase 3 (Save Data to File) ---
if st.button("Push to Phase 3"):
    data = {
        "case_name": st.session_state.get("case_name", ""),
        "case_number": st.session_state.get("case_number", ""),
        "phase2_facts": st.session_state.get("phase2_facts", ""),
        "phase2_tags": st.session_state.get("phase2_tags", ""),
        "phase2_issues": st.session_state.get("phase2_issues", []),
        "phase2_defenses": st.session_state.get("phase2_defenses", []),
        "motion_facts": st.session_state.get("motion_facts", "")
    }
    json_bytes = json.dumps(data, indent=2).encode("utf-8")
    st.download_button(
        label="Download Data for Phase 3",
        data=json_bytes,
        file_name="phase2_to_phase3.json",
        mime="application/json"
    )
    st.success("Data prepared! Download and upload this file in Phase 3.")

# --- Optional: Show Current Session State for Debugging ---
if st.checkbox("Show Session State (Debug)"):
    st.write(dict(st.session_state))
