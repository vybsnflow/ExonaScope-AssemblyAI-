# ExonaScope Phase 2 – Legal Tagging, Issue Spotting, and Motion Drafting (with CourtListener integration)

import streamlit as st
import requests
import json
from docx import Document
from io import BytesIO
import os

# -------------------- SECTION 1: Legal Tagging --------------------
def tag_legal_events(facts: str):
    prompt = f"""
You are a legal tagging assistant. Classify each factual statement below using the following categories only:
Traffic Stop, Investigative Detention, Search (Consent/Warrant/No Consent), Arrest, Interrogation, Miranda Warning, 
Statement (Incriminating/Exculpatory), Use of Force, Seizure of Property, Probable Cause Determination.

Return a JSON list: [ {{"fact": ..., "tag": ...}}, ... ]

FACTS:
{facts}
"""
    return gpt_call(prompt)

# -------------------- SECTION 2: Issue & Defense Spotting --------------------
def analyze_legal_issues_and_defenses(tagged_json):
    prompt = f"""
You are a criminal defense legal analyst. Based on the tagged events below, identify:

A. Potential Constitutional or Procedural Issues (e.g., unlawful stop, Miranda violation, illegal search)
B. Potential Legal Defenses (e.g., self-defense, duress, alibi, mistaken identity, lack of intent)

Output in this format:
{{
  "legal_issues": [...],
  "possible_defenses": [...]
}}

TAGGED EVENTS:
{tagged_json}
"""
    return gpt_call(prompt)

# -------------------- SECTION 3: Caselaw Lookup via CourtListener --------------------
API_URL = "https://www.courtlistener.com/api/rest/v3/opinions/"

def get_cases_for_issue(issue_tag: str, jurisdiction: str = "vi", limit=3):
    params = {
        "q": issue_tag,
        "jurisdiction": jurisdiction,
        "page_size": limit,
        "order_by": "-date_filed"
    }
    response = requests.get(API_URL, params=params)
    results = []
    if response.status_code == 200:
        data = response.json()
        for result in data.get("results", []):
            results.append({
                "name": result.get("case_name"),
                "citation": result.get("citations", [{}])[0].get("cite"),
                "court": result.get("court", {}).get("name"),
                "url": result.get("absolute_url")
            })
    return results

# -------------------- SECTION 4: Motion Drafting --------------------
def draft_motion(case_name, case_number, facts, issues, defenses, caselaw, motion_type):
    template = {
        "suppress_statements": "Motion to Suppress Statements",
        "suppress_evidence": "Motion to Suppress Physical Evidence",
        "dismiss_case": "Motion to Dismiss Case",
    }.get(motion_type, "Motion to Suppress")

    jurisdiction_language = {
        "vi": "Pursuant to the Revised Organic Act and Title 5 of the Virgin Islands Code...",
        "3rd": "Under precedents from the Third Circuit Court of Appeals...",
        "default": "Under established federal constitutional principles..."
    }.get(jurisdiction, jurisdiction_language["default"])

    prompt = f"""
You are a defense attorney drafting a {template} for:
CASE: {case_name}\nCASE NO.: {case_number}

FACTS:
{facts}

LEGAL ISSUES:
{json.dumps(issues, indent=2)}
DEFENSES:
{json.dumps(defenses, indent=2)}

You may ONLY cite the following verified cases:
{json.dumps(caselaw, indent=2)}

Include a signature block and an audit disclaimer that this document was AI-assisted.
Start the argument with: {jurisdiction_language}
"""
    return gpt_call(prompt)

# -------------------- SECTION 5: GPT Wrapper --------------------
def gpt_call(prompt):
    import openai
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a precise legal assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

# -------------------- SECTION 6: Whisper-Based Transcription --------------------
def transcribe_with_whisper(audio_path):
    import openai
    openai.api_key = st.secrets["OPENAI_API_KEY"]
    audio_file = open(audio_path, "rb")
    transcript = openai.Audio.transcribe("whisper-1", audio_file)
    return transcript["text"]

# -------------------- SECTION 7: Save/Load Case History --------------------
CASE_HISTORY_FILE = "case_history.json"

def save_case_to_history(case_name, case_number, facts, issues, defenses, motion):
    case_data = {
        "case_name": case_name,
        "case_number": case_number,
        "facts": facts,
        "issues": issues,
        "defenses": defenses,
        "motion": motion
    }
    if os.path.exists(CASE_HISTORY_FILE):
        with open(CASE_HISTORY_FILE, "r") as f:
            history = json.load(f)
    else:
        history = []
    history.append(case_data)
    with open(CASE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

def load_case_history():
    if os.path.exists(CASE_HISTORY_FILE):
        with open(CASE_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

# -------------------- SECTION 8: Streamlit Interface --------------------
st.title("ExonaScope Phase 2 – Legal Analysis & Motion Builder")

case_name = st.text_input("Case Name")
case_number = st.text_input("Case Number")
audio_file = st.file_uploader("(Optional) Upload audio to transcribe via Whisper", type=["mp3", "wav", "m4a"])
if audio_file:
    with open("temp_audio", "wb") as f:
        f.write(audio_file.read())
    with st.spinner("Transcribing audio..."):
        facts = transcribe_with_whisper("temp_audio")
else:
    facts = st.text_area("Paste Extracted Facts from Phase 1", height=300)

motion_type = st.selectbox("Motion Type", ["suppress_statements", "suppress_evidence", "dismiss_case"])
jurisdiction = st.text_input("Jurisdiction Code (e.g., 'vi' for Virgin Islands)", value="vi")

if st.button("🔍 Analyze Case"):
    with st.spinner("Tagging legal events..."):
        tags = tag_legal_events(facts)
    tags_editable = st.text_area("📝 Edit/Reclassify Tagged Events (JSON)", value=tags, height=200)

    with st.spinner("Spotting issues and defenses..."):
        analysis = analyze_legal_issues_and_defenses(tags_editable)
    st.code(analysis, language="json")

    with st.spinner("Fetching caselaw for issues..."):
        parsed = json.loads(analysis)
        issues = parsed.get("legal_issues", [])
        defenses = parsed.get("possible_defenses", [])
        case_refs = []
        for issue in issues:
            case_refs.extend(get_cases_for_issue(issue, jurisdiction=jurisdiction))
    st.code(case_refs, language="json")

    with st.spinner("Drafting motion to suppress..."):
        motion = draft_motion(case_name, case_number, facts, issues, defenses, case_refs, motion_type)
    st.text_area("📄 Motion to Suppress", motion, height=400)
    docx_bytes = BytesIO()
    Document().add_paragraph(motion).save(docx_bytes)
    docx_bytes.seek(0)
    st.download_button("Download Motion (.docx)", docx_bytes, file_name="motion_to_suppress.docx")

    save_case_to_history(case_name, case_number, facts, issues, defenses, motion)

if st.checkbox("📚 Load Previous Cases"):
    history = load_case_history()
    for i, item in enumerate(history):
        st.markdown(f"**{item['case_name']} ({item['case_number']})**")
        with st.expander("View Summary"):
            st.text_area("Facts", item["facts"], height=150)
            st.text_area("Motion", item["motion"], height=200)
