import streamlit as st
from io import BytesIO
from docx import Document
from fpdf import FPDF
import os
import requests
import re

# --- Elite Argument Generation ---
def gpt_memo_argument_for_issue(issue, facts, jurisdiction, caselaw_text):
    api_key = os.getenv("OPENAI_API_KEY")
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    prompt = f"""
You are a distinguished criminal defense attorney and appellate strategist with 30+ years’ experience. Draft a thorough, internally confidential legal memorandum analyzing the following suppression issue:

Issue: {issue['title']}
Jurisdiction: {jurisdiction or '[Unknown]'}
Facts: {facts}

- Provide a rigorous constitutional and legal analysis, integrating practical trial and appellate strategy.
- Use the following caselaw (quoted or summarized as appropriate):

{caselaw_text}

- Highlight the issue’s complexity, cite relevant controlling or persuasive appellate/Supreme Court cases (formal citations and summaries), and analyze anticipated prosecution counterarguments.
- Write with the clarity and depth expected of an elite defense practitioner prepping for both trial and review.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a seasoned defense legal memo writer."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

# --- Robust Caselaw Fetch ---
def fetch_caselaw_from_courtlistener(query, explanation, facts, jurisdiction, appellate_only=True, limit=4):
    params = {
        "q": f"{query} {explanation} {facts}",
        "type": "o",
        "page_size": limit,
        "order_by": "-date_filed",
    }
    if jurisdiction:
        params["jurisdiction"] = jurisdiction
    if appellate_only:
        params["court_type"] = "A"
    try:
        r = requests.get("https://www.courtlistener.com/api/rest/v3/search/", params=params)
        r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("results", []):
            case_name = item.get("caseName", "") or item.get("case_name", "")
            citation = item.get("citation", "")
            court = item.get("court", {}).get("name", "")
            date = item.get("dateFiled", item.get("date_filed", ""))
            url = item.get("absolute_url", "")
            summary = item.get("plain_text", "")
            if summary:
                summary = summary[:350].replace("\n", " ") + ("..." if len(summary) > 340 else "")
            results.append({
                "case_name": case_name,
                "citation": citation,
                "court": court,
                "date": date,
                "url": f"https://www.courtlistener.com{url}" if url else "",
                "summary": summary
            })
        return results
    except Exception:
        return []

# --- PDF Export Helper ---
def text_to_pdf(text, filename="memo.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in text.split('\n'):
        pdf.multi_cell(0, 10, line)
    pdf_output = BytesIO()
    pdf.output(pdf_output)
    pdf_output.seek(0)
    return pdf_output

# --- Suppression Memo Formatter ---
def format_suppression_issues_memo(case_name, case_number, facts_summary, issues, issue_caselaw_edits, court="INTERNAL LEGAL MEMO", state=""):
    memo = []
    memo.append(f"{court}\n{state}\n\nMemo regarding: {case_name}\nCase Number: {case_number}\n")
    memo.append("CONFIDENTIAL DEFENSE MEMORANDUM\n" + "="*42 + "\n\n")
    memo.append("This memorandum analyzes potential bases for suppression of evidence, providing in-depth legal arguments, trial and appellate strategies, and relevant controlling authority for team review. Not for filing without attorney review.\n")
    memo.append("SUMMARY OF PERTINENT FACTS\n\n" + facts_summary + "\n")
    memo.append("SUPPRESSION ISSUES ANALYSIS\n")
    for i, issue in enumerate(issues, 1):
        memo.append(f"---\n\nISSUE {i}: {issue['title']}\n\n{issue['argument_full']}\n\n{issue_caselaw_edits.get(i, '')}\n")
    memo.append("\n[End of Memorandum]\n")
    return "\n".join(memo)

# --- Defense Memo Formatter (unchanged from before) ---
def format_defense_strategy(case_name, case_number, defenses):
    output = []
    output.append(f"# Defense Strategy Memo – {case_name}")
    output.append(f"**Case Number**: {case_number}\n")
    for d in defenses:
        output.append(f"## {d['title']}\n\n{d['explanation']}\n")
    output.append("*This document is for internal defense team use only.*")
    return "\n".join(output)

# ==== UI: ExonaScope Memo Mode ====
case_name = st.session_state.get("case_name", "")
case_number = st.session_state.get("case_number", "")
facts = st.session_state.get("phase2_facts", "")
tags = st.session_state.get("phase2_tags", "")
issues = st.session_state.get("phase2_issues", [])
defenses = st.session_state.get("phase2_defenses", [])
memo_facts = st.session_state.get("motion_facts", "")
jurisdiction = st.text_input("Jurisdiction Code (e.g., 'ca', 'ny', 'tx')", value="")
appellate_only = st.checkbox("Appellate Cases Only", value=True)

st.title("ExonaScope Phase 3 – Elite Suppression Issues Memo & Defense Strategy")

st.subheader("📂 Case Information")
st.markdown(f"**Case Name**: {case_name}")
st.markdown(f"**Case Number**: {case_number}")

# --- Collect arguments and editable caselaw per issue ---
issue_caselaw_edits = {}
elite_issues = []

if issues and memo_facts:
    st.subheader("🧠 AI-Generated Suppression Issues Memo")
    with st.spinner("Conducting advanced legal research and drafting arguments..."):
        for idx, issue in enumerate(issues, 1):
            # Get robust, jurisdiction-specific caselaw
            caselaw = fetch_caselaw_from_courtlistener(
                issue['title'], issue['explanation'], facts, jurisdiction, appellate_only=appellate_only, limit=4
            )
            caselaw_md = ""
            if caselaw:
                for c in caselaw:
                    citation = f"*{c['case_name']}*, {c['citation']} ({c['court']} {c['date']})"
                    link = f"[Full Opinion]({c['url']})" if c['url'] else ""
                    summary = c['summary']
                    caselaw_md += f"- {citation} {link}\n    {summary}\n"
            else:
                caselaw_md = "_No relevant caselaw retrieved. Try varying your jurisdiction or keywords._\n"
            # Use LLM argument generator with elite-level prompt
            argument_text = gpt_memo_argument_for_issue(issue, facts, jurisdiction, caselaw_md)
            issue_caselaw_edits[idx] = st.text_area(
                f"Edit/Annotate Caselaw for Issue {idx} ({issue['title']})",
                value=caselaw_md,
                height=120,
                key=f"caselaw_edit_{idx}"
            )
            elite_issues.append(dict(**issue, argument_full=argument_text))

    memo_text = format_suppression_issues_memo(
        case_name, case_number, memo_facts, elite_issues, issue_caselaw_edits
    )
    st.text_area("Memo Preview", value=memo_text, height=500, key="suppression_memo_display")

    # --- Download as DOCX ---
    docx_bytes = BytesIO()
    doc = Document()
    for line in memo_text.split('\n'):
        doc.add_paragraph(line)
    doc.save(docx_bytes)
    docx_bytes.seek(0)
    st.download_button("📥 Download Suppression Memo (.docx)",
        data=docx_bytes.getvalue(),
        file_name="Suppression_Memo.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    # --- Download as PDF ---
    pdf_bytes = text_to_pdf(memo_text)
    st.download_button("📄 Download Suppression Memo as PDF",
        data=pdf_bytes,
        file_name="Suppression_Memo.pdf",
        mime="application/pdf")

else:
    st.info("Awaiting issues and facts from Phase 2.")

# --- Defense Strategy Memo remains accessible/downloadable ---
if defenses:
    st.subheader("🛡️ Defense Strategy Memo")
    defense_text = format_defense_strategy(case_name, case_number, defenses)
    st.text_area("Strategy Memo Preview", value=defense_text, height=400, key="defense_preview")

    docx_defense = BytesIO()
    doc = Document()
    for line in defense_text.split("\n"):
        doc.add_paragraph(line)
    doc.save(docx_defense)
    docx_defense.seek(0)
    st.download_button("📥 Download Defense Memo (.docx)",
        data=docx_defense.getvalue(),
        file_name="Defense_Strategy_Memo.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    pdf_defense = text_to_pdf(defense_text)
    st.download_button("📄 Download Defense Memo as PDF",
        data=pdf_defense,
        file_name="Defense_Strategy_Memo.pdf",
        mime="application/pdf")
else:
    st.info("No defenses available.")

if st.checkbox("🪵 Debug Session State"):
    st.json(dict(st.session_state))

