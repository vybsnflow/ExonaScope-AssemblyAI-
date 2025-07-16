import streamlit as st
import json
import os
import ast
import re

# --- GPT Call Utility ---
def gpt_call(prompt):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        st.error("OPENAI_API_KEY is not set in your environment variables.")
        st.stop()
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a precise, formal legal assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        if not response or not hasattr(response, "choices") or not response.choices:
            st.error("No response from AI. Check API key or network.")
            return ""
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"OpenAI call failed: {e}")
        return ""

def parse_ai_output(result):
    result = result.strip()
    if result.startswith("```"):
        result = re.sub(r"^```(?:json)?\n?", "", result, flags=re.IGNORECASE)
        result = re.sub(r"\n?```$", "", result)
    try:
        return json.loads(result)
    except Exception:
        try:
            return ast.literal_eval(result)
        except Exception:
            return []

def generate_suppression_issues(facts, tags):
    prompt = f"""
You are a criminal defense attorney. Based on the following raw facts and tagged events, list plausible suppression issues related to constitutional violations.

For each issue, return:
- "title" (e.g., "Unlawful Search and Seizure")
- "explanation" (1–2 sentence summary, referencing the facts)

Facts:
{facts}

Tagged Events:
{tags}

Return a JSON list of objects with "title" and "explanation".
"""
    result = gpt_call(prompt)
    issues = parse_ai_output(result)
    return [i for i in issues if "title" in i and "explanation" in i]

def generate_defenses(facts, tags):
    prompt = f"""
You are a criminal defense strategist. Based on the facts and tagged legal events, identify all non-suppression legal defenses.

For each defense:
- "title" (e.g., "Mistaken Identity", "Alibi")
- "explanation" (2–3 sentence reasoning)

Facts:
{facts}

Tagged Events:
{tags}

Return a JSON list formatted with "title" and "explanation" for each defense.
"""
    result = gpt_call(prompt)
    defenses = parse_ai_output(result)
    return [d for d in defenses if "title" in d and "explanation" in d]

# ----------------- UI Starts -----------------
st.title("ExonaScope Phase 2 – Auto-Generated Legal Strategy")

# Case input
case_name = st.text_input("Case Name", value=st.session_state.get("case_name", ""))
case_number = st.text_input("Case Number", value=st.session_state.get("case_number", ""))
facts = st.text_area("📝 Raw Facts", value=st.session_state.get("phase2_facts", ""), height=150)
tags = st.text_area("📍 Tagged Legal Events", value=st.session_state.get("phase2_tags", ""), height=100)

# Fallback for tags if empty
if not tags.strip():
    tags = "[No tagged legal events provided]"

# Save input to session
st.session_state["case_name"] = case_name
st.session_state["case_number"] = case_number
st.session_state["phase2_facts"] = facts
st.session_state["phase2_tags"] = tags

# ----------------- AUTO-GENERATE -----------------
if facts.strip():
    if "phase2_issues" not in st.session_state or not st.session_state["phase2_issues"]:
        with st.spinner("Auto-generating suppression issues..."):
            st.session_state["phase2_issues"] = generate_suppression_issues(facts, tags)

    if "phase2_defenses" not in st.session_state or not st.session_state["phase2_defenses"]:
        with st.spinner("Auto-generating potential defenses..."):
            st.session_state["phase2_defenses"] = generate_defenses(facts, tags)

# ----------------- DISPLAY RESULTS -----------------
st.subheader("📑 AI-Generated Suppression Issues")
issues = st.session_state.get("phase2_issues", [])
if issues:
    for idx, issue in enumerate(issues, 1):
        st.markdown(f"**{idx}. {issue['title']}**  \n{issue['explanation']}")
else:
    st.info("No suppression issues generated yet.")

st.subheader("⚖️ AI-Generated Defenses")
defenses = st.session_state.get("phase2_defenses", [])
if defenses:
    for idx, defense in enumerate(defenses, 1):
        st.markdown(f"**{idx}. {defense['title']}**  \n{defense['explanation']}")
else:
    st.info("No defenses generated yet.")

# ----------------- Summarize Facts -----------------
def summarize_facts_for_motion(raw_facts, tagged_events):
    prompt = f"""
You are a legal writing assistant. Given the facts and tagged legal events below, write a clear and neutral 'Statement of Facts' for a legal motion. Be chronological and professional.

Facts:
{raw_facts}

Tagged Events:
{tagged_events}

Return a formal narrative paragraph.
"""
    return gpt_call(prompt)

if st.button("📝 Summarize Facts for Motion", key="summarize_facts"):
    with st.spinner("Drafting summary..."):
        summary = summarize_facts_for_motion(facts, tags)
    st.session_state["motion_facts"] = summary

if "motion_facts" in st.session_state:
    st.subheader("📖 Statement of Facts")
    st.text_area("Review or edit:", value=st.session_state["motion_facts"], height=200, key="final_facts")

    # (Assumes you already generated and saved st.session_state vars)

    st.subheader("⬆️ Proceed to Phase 3")
    st.success("Data is ready and passed automatically to Phase 3!")

    if st.button("Go to Phase 3"):
        st.switch_page("pages/ExonaScope_Phase3.py")  # Adjust as needed


# Debug Output
if st.checkbox("🪵 Debug Session State"):
    st.json(dict(st.session_state))

