import streamlit as st
import requests
import json
from docx import Document
from io import BytesIO
import os
import logging
import streamlit as st
st.write("Session State Contents:", dict(st.session_state))

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)

# --- Retrieve Data from Phase 2 ---
case_name = st.session_state.get("case_name", "")
case_number = st.session_state.get("case_number", "")
facts = st.session_state.get("phase2_facts", "")         # This is the Raw Facts
tags = st.session_state.get("phase2_tags", "")           # Tagged Events
issues = st.session_state.get("phase2_issues", [])
defenses = st.session_state.get("phase2_defenses", [])

# Log for debugging
logging.info(f"✅ Received facts from Phase 2: {facts}")
logging.info(f"✅ Received tags from Phase 2: {tags}")

# --- GPT Call (OpenAI) ---
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

# --- Summarize Facts for Motion ---
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

# --- Fetch Real Caselaw from CourtListener ---
def fetch_caselaw_from_courtlistener(issue, jurisdiction=None, limit=3):
    headers = {}
    params = {
        "q": issue,
        "type": "o",
        "page_size": limit,
        "order_by": "-date_filed"
    }
    if jurisdiction:
        params["jurisdiction"] = jurisdiction
    url = "https://www.courtlistener.com/api/rest/v3/search/"
    response = requests.get(url, params=params, headers=headers)
    if response.status_code != 200:
        return []
    data = response.json()
    results = []
    for result in data.get("results", []):
        case = {
            "case_name": result.get("caseName", result.get("case_name", "")),
            "citation": result.get("citation", ""),
            "court": result.get("court", {}).get("name", ""),
            "date": result.get("dateFiled", result.get("date_filed", "")),
            "url": result.get("absolute_url", "")
        }
        results.append(case)
    return results

# --- Generate Argument for Suppression Issue ---
def generate_argument_for_issue(issue, facts, caselaw, jurisdiction):
    caselaw_text = ""
    for case in caselaw:
        caselaw_text += f"- {case['case_name']} ({case['citation']}, {case['court']}, {case['date']}): {case['url']}\n"
    prompt = f"""
You are a defense attorney drafting a legal argument for a motion to suppress.
Issue: {issue['title']}
Facts: {facts}
Explanation: {issue['explanation']}
Relevant Caselaw:
{caselaw_text}
Jurisdiction: {jurisdiction}

Write a detailed, professional legal argument for this issue, referencing the provided facts and caselaw. Cite cases by name and citation.
"""
    return gpt_call(prompt)

# --- Generate Strategy Memo for Defense ---
def generate_strategy_for_defense(defense, facts):
    prompt = f"""
You are a criminal defense strategist.
Defense: {defense['title']}
Facts: {facts}
Explanation: {defense['explanation']}

Write a practical strategy memo for this defense. Include recommendations for investigation, evidence, and trial tactics. Do not draft legal arguments or cite caselaw.
"""
    return gpt_call(prompt)

# --- Streamlit UI ---
st.title("ExonaScope Phase 3 – Motion Generator & Defense Strategy")

jurisdiction = st.text_input("Jurisdiction Code (e.g., 'vi' for Virgin Islands)", value="vi", key="phase3_jurisdiction")

st.header("Case Information")
st.markdown(f"**Case Name:** {case_name}")
st.markdown(f"**Case Number:** {case_number}")

# --- Generate & Display the Summarized Facts ---
if "motion_facts" not in st.session_state:
    if facts:
        with st.spinner("Summarizing facts for motion..."):
            summarized_facts = summarize_facts_for_motion(facts, tags)
        st.session_state["motion_facts"] = summarized_facts
    else:
        st.error("❌ Facts not found. Please make sure Phase 2 passed 'phase2_facts'.")

# Display editable facts summary
if "motion_facts" in st.session_state:
    st.header("Summarized Facts for Motion")
    summarized_facts_editable = st.text_area(
        "Edit the summarized facts if needed:",
        value=st.session_state["motion_facts"],
        height=200,
        key="summarized_facts_editable"
    )
    st.session_state["motion_facts"] = summarized_facts_editable
else:
    st.warning("⚠️ No summarized facts available to edit.")

# --- Generate Motion to Suppress ---
if st.button("Generate Motion to Suppress", key="generate_motion"):
    motion_sections = []
    for i, issue in enumerate(issues):
        st.info(f"Fetching caselaw for: {issue['title']}")
        caselaw = fetch_caselaw_from_courtlistener(issue['title'], jurisdiction=jurisdiction, limit=3)
        argument = generate_argument_for_issue(issue, st.session_state["motion_facts"], caselaw, jurisdiction)
        motion_sections.append(f"## {issue['title']}\n\n{argument}\n")

    motion_text = (
        f"# Motion to Suppress\n\n"
        f"**Case Name:** {case_name}\n"
        f"**Case Number:** {case_number}\n\n"
        f"## Statement of Facts\n{st.session_state['motion_facts']}\n\n"
        f"## Argument\n" + "\n".join(motion_sections) +
        "\n## Conclusion\nWHEREFORE, the defense respectfully requests that the Court grant the motion to suppress as set forth above.\n\n"
        "Respectfully submitted,\n\n[Signature Block]\n\n*This document was AI-assisted.*"
    )

    st.subheader("Draft Motion to Suppress")
    st.text_area("Motion to Suppress", motion_text, height=400, key="motion_text_area")

    # Word download
    docx_bytes = BytesIO()
    Document().add_paragraph(motion_text).save(docx_bytes)
    docx_bytes.seek(0)
    st.download_button(
        "Download Motion (.docx)",
        docx_bytes.getvalue(),
        file_name="motion_to_suppress.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="download_motion"
    )

# --- Generate Defense Strategy Memo ---
if st.button("Generate Defense Strategy Memo", key="generate_defense_strategy"):
    strategy_sections = []
    for j, defense in enumerate(defenses):
        strategy = generate_strategy_for_defense(defense, st.session_state["motion_facts"])
        strategy_sections.append(f"## {defense['title']}\n\n{strategy}\n")

    strategy_text = (
        f"# Defense Strategy Memo\n\n"
        f"**Case Name:** {case_name}\n"
        f"**Case Number:** {case_number}\n\n"
        f"## Overview of Defenses\n" + "\n".join(strategy_sections) +
        "\n*This document was AI-assisted and is for internal defense team use only.*"
    )

    st.subheader("Defense Strategy Memo")
    st.text_area("Defense Strategy", strategy_text, height=400, key="defense_text_area")

    docx_bytes = BytesIO()
    Document().add_paragraph(strategy_text).save(docx_bytes)
    docx_bytes.seek(0)
    st.download_button(
        "Download Defense Strategy (.docx)",
        docx_bytes.getvalue(),
        file_name="defense_strategy.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        key="download_defense"
    )

