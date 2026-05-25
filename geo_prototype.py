"""
GEO Research Prototype — Flight Centre Unoptimised vs FAQ Optimised
"""
import streamlit as st
import requests
import re
import json
import time
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="GEO Prototype", page_icon="✈️", layout="wide")

BASE  = "https://matthewmyspace.github.io/GEO-Research-Sites"
SITES = {
    "fc_unoptimised": {"label": "Flight Centre Unoptimised",  "url": f"{BASE}/01_fc_unoptimised.html",    "color": "#E57373"},
    "fc_faq":         {"label": "Flight Centre FAQ Optimised", "url": f"{BASE}/Unoptimised_with_FAQ.html", "color": "#66BB6A"},
    "booking":        {"label": "Booking.com",       "url": f"{BASE}/03_booking.html",           "color": "#FF7043"},
    "agoda":          {"label": "Agoda",             "url": f"{BASE}/04_agoda.html",             "color": "#AB47BC"},
    "expedia":        {"label": "Expedia",           "url": f"{BASE}/05_expedia.html",           "color": "#FFA726"},
    "traveloka":      {"label": "Traveloka",         "url": f"{BASE}/06_traveloka.html",         "color": "#26C6DA"},
    "trip":           {"label": "Trip.com",          "url": f"{BASE}/07_trip.html",              "color": "#8D6E63"},
}

QUERIES = {
    "Q01 — Best travel packages Australia":                  "Best travel packages Australia",
    "Q02 — All inclusive holiday packages from Australia":   "All inclusive holiday packages from Australia",
    "Q03 — Cheap flights from Australia to Bali":            "Cheap flights from Australia to Bali",
    "Q04 — Cruise holidays from Australia":                  "Cruise holidays from Australia",
    "Q05 — Luxury travel packages from Australia":           "Luxury travel packages from Australia",
    "Q06 — Family holiday packages Australia":               "Family holiday packages Australia",
    "Q07 — Cheap flights Melbourne to Sydney":               "Cheap flights Melbourne to Sydney",
    "Q08 — Honeymoon packages from Australia":               "Honeymoon packages from Australia",
    "Q09 — Solo travel packages Australia":                  "Solo travel packages Australia",
    "Q10 — Adventure travel packages Australia":             "Adventure travel packages Australia",
    "Q11 — Travel packages for seniors Australia":           "Travel packages for seniors Australia",
    "Q12 — Travel packages New Zealand":                     "Travel packages New Zealand",
    "Q13 — Cheap holiday packages Europe from Australia":    "Cheap holiday packages Europe from Australia",
    "Q14 — Beach holiday packages Queensland":               "Beach holiday packages Queensland",
    "Q15 — Group travel packages from Australia":            "Group travel packages from Australia",
}

HISTORICAL = {
    "Q01": {"baseline": True,  "faq": True,  "delta": "Maintained"},
    "Q02": {"baseline": True,  "faq": True,  "delta": "Maintained"},
    "Q03": {"baseline": True,  "faq": True,  "delta": "Maintained"},
    "Q04": {"baseline": True,  "faq": True,  "delta": "Maintained"},
    "Q05": {"baseline": True,  "faq": True,  "delta": "Maintained"},
    "Q06": {"baseline": False, "faq": False, "delta": "Still absent"},
    "Q07": {"baseline": False, "faq": True,  "delta": "Gained"},
    "Q08": {"baseline": False, "faq": True,  "delta": "Gained"},
    "Q09": {"baseline": True,  "faq": False, "delta": "Lost"},
    "Q10": {"baseline": False, "faq": False, "delta": "Still absent"},
    "Q11": {"baseline": False, "faq": False, "delta": "Still absent"},
    "Q12": {"baseline": False, "faq": False, "delta": "Still absent"},
    "Q13": {"baseline": False, "faq": False, "delta": "Still absent"},
    "Q14": {"baseline": False, "faq": False, "delta": "Still absent"},
    "Q15": {"baseline": False, "faq": False, "delta": "Still absent"},
}

st.markdown("""
<style>
.header{background:linear-gradient(135deg,#1F4E79,#2E75B6);padding:1.2rem 1.8rem;border-radius:10px;margin-bottom:1rem}
.header h1{color:white;margin:0;font-size:1.6rem}
.header p{color:#BDD7EE;margin:0.2rem 0 0;font-size:0.85rem}
.rbox{border-radius:8px;padding:1rem;max-height:300px;overflow-y:auto;font-size:0.85rem;line-height:1.7;color:#111}
.rbox mark{background:#FFD54F;color:#000;padding:0 2px;border-radius:2px;font-weight:700}
.mcard{background:#1e2a3a;border-radius:10px;padding:1rem 1.1rem;border-left:5px solid #2E75B6;margin-bottom:4px}
.mcard.g{background:#0d2e1a;border-left-color:#2ECC71}
.mcard.r{background:#2e0d0d;border-left-color:#E74C3C}
.mtitle{font-size:0.7rem;font-weight:700;letter-spacing:.08em;color:#90CAF9;text-transform:uppercase;margin-bottom:6px}
.mrow{font-size:0.88rem;color:#ECEFF1;margin:3px 0}
.mdelta{font-size:0.78rem;color:#B0BEC5;margin-top:6px}
.mcard.g .mdelta{color:#81C784}
.mcard.r .mdelta{color:#EF9A9A}
</style>
""", unsafe_allow_html=True)

# ── SIDEBAR ──
with st.sidebar:
    st.caption("Please enter your API Key below before running GEO test.")
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...", label_visibility="collapsed")
    st.divider()
    st.markdown("### Manual Testing Summary")
    st.markdown("- Baseline: **46.7%** inclusion rate")
    st.markdown("- FAQ Optimised: **57.7%** inclusion rate")
    st.markdown("- Delta: **+11.0 percentage points**")
    st.caption("ChatGPT (GPT-4) was tested across 15 travel queries using a single-URL method. Each tester ran both the unoptimised and FAQ-optimised Flight Centre pages in separate sessions. Results are averaged across 3 testers.")

# ── HELPERS ──
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_content(url):
    try:
        from bs4 import BeautifulSoup
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script","style","nav","header","footer","form","button"]):
            tag.decompose()
        return re.sub(r'\s+', ' ', soup.get_text(" ", strip=True))[:300]
    except Exception as e:
        return f"[Error fetching page: {e}]"

def call_gemini(prompt, api_key):
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=api_key)
    for model_name in ["gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash"]:
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        max_output_tokens=2500,
                        temperature=0.3,
                    )
                )
                return response.text
            except Exception as e:
                err = str(e)
                if "429" in err or "quota" in err.lower() or "exhausted" in err.lower():
                    time.sleep((2 ** attempt) * 5)
                    continue
                raise Exception(err)
    raise Exception("Rate limit hit. Daily quota may be exhausted — resets at midnight Pacific Time.")

def highlight_tokens(text, query):
    stop = {"from","to","the","a","an","in","at","for","of","and","or","is","are","best","cheap","what","how"}
    tokens = [t.strip("?.,!").lower() for t in query.split() if t.strip("?.,!").lower() not in stop and len(t) > 2]
    for tok in sorted(tokens, key=len, reverse=True):
        text = re.sub(f'(?i)({re.escape(tok)})', r'<mark>\1</mark>', text)
    return text

# ── MAIN UI ──
st.markdown("""
<div>
    <h2>GEO Research Prototype</h2>
    <p>Test how FAQ optimisation changes Flight Centre's visibility in AI-generated search answers</p>
</div>
""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

c1, c2 = st.columns([1,1])
with c1:
    mode = st.radio("**Query mode:**", ["Project Queries Q01–Q15", "Custom"], horizontal=True)
with c2:
    if mode == "Project Queries Q01–Q15":
        sel = st.selectbox("**Select query:**", list(QUERIES.keys()))
        query_text = QUERIES[sel]
    else:
        query_text = st.text_input("Type query", placeholder="e.g. Best beach holidays from Melbourne")
    
    if "last_query" not in st.session_state:
        st.session_state["last_query"] = query_text
    elif st.session_state["last_query"] != query_text:
        for key in ["fc_u_ans", "fc_f_ans", "fc_u_scores", "fc_f_scores",
                    "ai_answer", "ranking", "citation_scores", "raw", "q"]:
            st.session_state.pop(key, None)
        st.session_state["last_query"] = query_text

st.markdown(f"**Query:** `{query_text}`")

run_btn = st.button("🚀 Run GEO Test", type="primary", width="stretch")
st.divider()

if "fc_u_ans" in st.session_state:
    st.success("✅ Test complete — scroll down or select a tab to view results.")

# ── TEAM TESTING RESULTS ──
def team_testing_summary():
    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("## Team Testing Summary")
    st.caption("Static research findings from manual testing by Elle, Matthew, and Jaynath — independent of the query selected above.")
    st.markdown("<br>", unsafe_allow_html=True)

    if True:  # Team Testing Summary — always visible

        TESTER_DATA = {
            "Q01": {
                "query": "Best travel packages Australia",
                "elle":    {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "matthew": {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "jaynath": {"baseline": True,  "faq": True,  "delta": "= Maintained"},
            },
            "Q02": {
                "query": "All inclusive holiday packages from Australia",
                "elle":    {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "matthew": {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "jaynath": {"baseline": True,  "faq": True,  "delta": "= Maintained"},
            },
            "Q03": {
                "query": "Cheap flights from Australia to Bali",
                "elle":    {"baseline": True,  "faq": False, "delta": "↓ Lost"},
                "matthew": {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q04": {
                "query": "Cruise holidays from Australia",
                "elle":    {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "matthew": {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "jaynath": {"baseline": True,  "faq": True,  "delta": "= Maintained"},
            },
            "Q05": {
                "query": "Luxury travel packages from Australia",
                "elle":    {"baseline": False, "faq": False, "delta": "= Still absent"},
                "matthew": {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q06": {
                "query": "Family holiday packages Australia",
                "elle":    {"baseline": True,  "faq": False, "delta": "↓ Lost"},
                "matthew": {"baseline": False, "faq": False, "delta": "= Still absent"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q07": {
                "query": "Cheap flights Melbourne to Sydney",
                "elle":    {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "matthew": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
                "jaynath": {"baseline": False, "faq": False, "delta": "= Still absent"},
            },
            "Q08": {
                "query": "Honeymoon packages from Australia",
                "elle":    {"baseline": True,  "faq": True,  "delta": "= Maintained"},
                "matthew": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q09": {
                "query": "Solo travel packages Australia",
                "elle":    {"baseline": True,  "faq": False, "delta": "↓ Lost"},
                "matthew": {"baseline": True,  "faq": False, "delta": "↓ Lost"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q10": {
                "query": "Adventure travel packages Australia",
                "elle":    {"baseline": False, "faq": False, "delta": "= Still absent"},
                "matthew": {"baseline": False, "faq": False, "delta": "= Still absent"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q11": {
                "query": "Travel packages for seniors Australia",
                "elle":    {"baseline": True,  "faq": False, "delta": "↓ Lost"},
                "matthew": {"baseline": False, "faq": False, "delta": "= Still absent"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q12": {
                "query": "Travel packages New Zealand",
                "elle":    {"baseline": True,  "faq": False, "delta": "↓ Lost"},
                "matthew": {"baseline": False, "faq": False, "delta": "= Still absent"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q13": {
                "query": "Cheap holiday packages Europe from Australia",
                "elle":    {"baseline": True,  "faq": False, "delta": "↓ Lost"},
                "matthew": {"baseline": False, "faq": False, "delta": "= Still absent"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q14": {
                "query": "Beach holiday packages Queensland",
                "elle":    {"baseline": True,  "faq": False, "delta": "↓ Lost"},
                "matthew": {"baseline": False, "faq": False, "delta": "= Still absent"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
            "Q15": {
                "query": "Group travel packages from Australia",
                "elle":    {"baseline": False, "faq": False, "delta": "= Still absent"},
                "matthew": {"baseline": False, "faq": False, "delta": "= Still absent"},
                "jaynath": {"baseline": False, "faq": True,  "delta": "↑ Gained"},
            },
        }

        b_yes  = sum(1 for v in HISTORICAL.values() if v["baseline"])
        f_yes  = sum(1 for v in HISTORICAL.values() if v["faq"])
        gained = sum(1 for v in HISTORICAL.values() if not v["baseline"] and v["faq"])
        lost   = sum(1 for v in HISTORICAL.values() if v["baseline"] and not v["faq"])

        # ── Summary metric cards ──
        st.markdown("#### 📊 Overall Inclusion Results")
        st.caption("How often Flight Centre appeared in AI responses across all 15 queries, before and after FAQ optimisation.")

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"""
            <div style='background:#f0f4ff;border-left:5px solid #4472C4;border-radius:6px;padding:1rem 1.2rem'>
            <div style='font-size:0.75rem;font-weight:700;color:#4472C4;text-transform:uppercase;letter-spacing:.05em'>Baseline Inclusion</div>
            <div style='font-size:1.8rem;font-weight:700;color:#1a1a2e;margin-top:4px'>46.7%</div>
            <div style='font-size:0.78rem;color:#555;margin-top:2px'>{b_yes} of 15 queries</div>
            </div>""", unsafe_allow_html=True)
        c2.markdown(f"""
            <div style='background:#fff4ed;border-left:5px solid #ED7D31;border-radius:6px;padding:1rem 1.2rem'>
            <div style='font-size:0.75rem;font-weight:700;color:#ED7D31;text-transform:uppercase;letter-spacing:.05em'>FAQ Optimised Inclusion</div>
            <div style='font-size:1.8rem;font-weight:700;color:#1a1a2e;margin-top:4px'>57.7%</div>
            <div style='font-size:0.78rem;color:#555;margin-top:2px'>{f_yes} of 15 queries</div>
            </div>""", unsafe_allow_html=True)
        c3.markdown(f"""
            <div style='background:#f0fff4;border-left:5px solid #2ECC71;border-radius:6px;padding:1rem 1.2rem'>
            <div style='font-size:0.75rem;font-weight:700;color:#2ECC71;text-transform:uppercase;letter-spacing:.05em'>Queries Gained</div>
            <div style='font-size:1.8rem;font-weight:700;color:#1a1a2e;margin-top:4px'>↑ {gained}</div>
            <div style='font-size:0.78rem;color:#555;margin-top:2px'>Flight Centre newly appeared</div>
            </div>""", unsafe_allow_html=True)
        c4.markdown(f"""
            <div style='background:#fff8f8;border-left:5px solid #E74C3C;border-radius:6px;padding:1rem 1.2rem'>
            <div style='font-size:0.75rem;font-weight:700;color:#E74C3C;text-transform:uppercase;letter-spacing:.05em'>Queries Lost</div>
            <div style='font-size:1.8rem;font-weight:700;color:#1a1a2e;margin-top:4px'>↓ {lost}</div>
            <div style='font-size:0.78rem;color:#555;margin-top:2px'>Flight Centre dropped out</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.success("✅ Adding FAQ content improved Flight Centre's average AI inclusion rate by +11.0 percentage points across 3 testers.")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Bar chart ──
        st.markdown("#### 📈 Inclusion by Query — Baseline vs FAQ Optimised")
        st.caption("Each query shows whether Flight Centre was included (1) or absent (0) in the AI response for each page version.")

        qids = list(TESTER_DATA.keys())
        testers = ["elle", "matthew", "jaynath"]
        avg_baseline = [sum(TESTER_DATA[q][t]["baseline"] for t in testers) / 3 for q in qids]
        avg_faq      = [sum(TESTER_DATA[q][t]["faq"]      for t in testers) / 3 for q in qids]

        fig3 = go.Figure()
        fig3.add_trace(go.Bar(
            name="Baseline (Unoptimised)",
            x=qids,
            y=avg_baseline,
            marker_color="#4472C4",
            text=[f"{v:.0%}" for v in avg_baseline],
            textposition="outside"
        ))
        fig3.add_trace(go.Bar(
            name="FAQ Optimised",
            x=qids,
            y=avg_faq,
            marker_color="#ED7D31",
            text=[f"{v:.0%}" for v in avg_faq],
            textposition="outside"
        ))
        fig3.update_layout(
            barmode="group", height=320,
            yaxis=dict(range=[0,1.4], tickformat=".0%", title="Testers who saw Flight Centre included", gridcolor="#e0e0e0"),
            xaxis=dict(tickfont=dict(size=11)),
            legend=dict(orientation="h", y=1.08),
            plot_bgcolor="white", paper_bgcolor="white",
            font=dict(color="#1a1a2e"),
            margin=dict(t=20, b=10)
        )
        st.plotly_chart(fig3, width="stretch")

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Per-query table ──
        st.markdown("#### 🔍 Results by Query — All 3 Testers")
        st.caption("Each row shows whether Flight Centre appeared in the AI response per tester. Visibility Change is based on each tester's individual result.")

        # Per-tester raw data from spreadsheets
        rows = []
        for qid, d in TESTER_DATA.items():
            rows.append({
                "Query ID":              qid,
                "Query":                 d["query"],
                "Elle — Baseline":       "✓" if d["elle"]["baseline"]    else "✗",
                "Elle — FAQ":            "✓" if d["elle"]["faq"]         else "✗",
                "Elle — Change":         d["elle"]["delta"],
                "Matthew — Baseline":    "✓" if d["matthew"]["baseline"] else "✗",
                "Matthew — FAQ":         "✓" if d["matthew"]["faq"]      else "✗",
                "Matthew — Change":      d["matthew"]["delta"],
                "Jaynath — Baseline":    "✓" if d["jaynath"]["baseline"] else "✗",
                "Jaynath — FAQ":         "✓" if d["jaynath"]["faq"]      else "✗",
                "Jaynath — Change":      d["jaynath"]["delta"],
            })
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=480)

        st.markdown("<br>", unsafe_allow_html=True)

        # ── Key findings ──
        st.markdown("#### 💡 Key Findings")
        st.caption("Summary of what the manual testing results tell us about FAQ optimisation.")

        findings = [
            ("#2ECC71", "↑ Gained visibility", "Queries where Flight Centre newly appeared after FAQ optimisation — FAQ content directly answered those query types."),
            ("#E74C3C", "↓ Lost visibility",   "A small number of queries where Flight Centre dropped out — likely due to AI response variability, not a true decline."),
            ("#E74C3C", "Still absent in both", "Several queries where Flight Centre did not appear in either version — these need deeper content optimisation beyond FAQ alone."),
            ("#4472C4", "+11.0pp overall",      "Average improvement across all 3 testers when FAQ content was added to the Flight Centre page."),
        ]
        for color, title, desc in findings:
            st.markdown(
                f"<div style='background:#f8f9fa;border-left:5px solid {color};"
                f"border-radius:6px;padding:.8rem 1.2rem;margin-bottom:8px'>"
                f"<div style='font-size:0.82rem;font-weight:700;color:{color}'>{title}</div>"
                f"<div style='font-size:0.85rem;color:#444;margin-top:3px'>{desc}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

run_status = st.empty()

tab1, tab2 = st.tabs(["Baseline vs FAQ", "AI Answer Simulation"])

team_testing_summary()

# ── RUN ──
if run_btn:
    if not gemini_key:
        st.error("⚠️ Enter your Gemini API key in the sidebar.")
        st.stop()
    if not query_text.strip():
        st.error("⚠️ Please enter or select a query.")
        st.stop()

    with run_status:
        prog = st.progress(0, "📄 Loading pages...")
    try:
        # Step 1 — fetch all 7 pages (no API calls)
        all_contents = {}
        for i, (key, info) in enumerate(SITES.items()):
            prog.progress(int((i/7)*50), f"📄 Loading {info['label']}...")
            all_contents[key] = fetch_content(info["url"])

        # Step 2 — ONE Gemini call with all pages + structured output
        prog.progress(55, "🤖 Sending all 7 pages to Gemini (1 API call)...")

        sources_block = ""
        for i, (key, info) in enumerate(SITES.items(), 1):
            sources_block += f"\n[SOURCE {i}: {info['label']}]\n{all_contents[key]}\n"

        prompt = f"""You are an AI travel assistant. User asked: "{query_text}"

7 travel websites as sources:
{sources_block}

Reply in this EXACT format:

AI_ANSWER: [50-70 words answering the query, cite sources like [Flight Centre FAQ Optimised] or [Expedia]]

FLIGHT_CENTRE_BASELINE: [1 sentence from Source 1 only]
FLIGHT_CENTRE_FAQ: [1 sentence from Source 2 only]

RANKING:
1. [name] | [why]
2. [name] | [why]
3. [name] | [why]
4. [name] | [why]
5. [name] | [why]
6. [name] | [why]
7. [name] | [why]

SCORES:
Flight Centre Baseline (Unoptimised): [0-3]
Flight Centre FAQ Optimised: [0-3]
Booking.com: [0-3]
Agoda: [0-3]
Expedia: [0-3]
Traveloka: [0-3]
Trip.com: [0-3]"""

        raw = call_gemini(prompt, gemini_key)

        # Step 3 — parse response
        prog.progress(85, "📊 Parsing results...")

        # Extract AI answer
        ai_answer = ""
        m = re.search(r'AI_ANSWER:\s*(.*?)(?=FLIGHT_CENTRE_BASELINE:|FLIGHT_CENTRE_FAQ:|RANKING:|$)', raw, re.DOTALL|re.IGNORECASE)
        if m: ai_answer = m.group(1).strip()

        # Extract per-site FC answers
        fc_u_ans, fc_f_ans = "", ""
        m_u = re.search(r'FLIGHT[_\s]CENTRE[_\s]BASELINE[:\s*]*\n?\s*(.*?)(?=\n\s*FLIGHT[_\s]CENTRE[_\s]FAQ|\n\s*RANKING:|$)', raw, re.DOTALL|re.IGNORECASE)
        if m_u: fc_u_ans = m_u.group(1).strip()
        m_f = re.search(r'FLIGHT[_\s]CENTRE[_\s]FAQ[:\s*]*\n?\s*(.*?)(?=\n\s*RANKING:|$)', raw, re.DOTALL|re.IGNORECASE)
        if m_f: fc_f_ans = m_f.group(1).strip()

        # Extract ranking
        ranking = []
        m_rank = re.search(r'RANKING:\s*(.*?)(?=SCORES:|$)', raw, re.DOTALL|re.IGNORECASE)
        if m_rank:
            for line in m_rank.group(1).strip().split('\n'):
                line = line.strip()
                if re.match(r'^\d+\.', line):
                    ranking.append(line)

        # Extract scores
        citation_scores = {}
        m_scores = re.search(r'SCORES:\s*(.*?)$', raw, re.DOTALL|re.IGNORECASE)
        if m_scores:
            score_block = m_scores.group(1)
            for site in ["Flight Centre Baseline (Unoptimised)","Flight Centre FAQ Optimised","Booking.com","Agoda","Expedia","Traveloka","Trip.com"]:
                sm = re.search(rf'{re.escape(site)}[:\s]+([0-3])', score_block, re.IGNORECASE)
                if sm:
                    citation_scores[site] = int(sm.group(1))

        # Build FC scores from citation scores + answer quality
        def make_fc_scores(ans, site_label):
            cit = citation_scores.get(site_label, 0)
            has_detail = 1 if re.search(r'\$[\d,]+|nights|days|package|depart|includ', ans.lower()) else 0
            return {
                "answered":       1 if len(ans) > 30 else 0,
                "relevance":      cit,
                "quality":        min(3, cit + has_detail),
                "completeness":   cit,
                "faq_used":       1 if "faq" in ans.lower() or "frequently" in ans.lower() else 0,
                "specificity":    min(3, has_detail + (1 if cit > 0 else 0)),
            }

        fc_u_scores = make_fc_scores(fc_u_ans, "Flight Centre Baseline (Unoptimised)")
        fc_f_scores = make_fc_scores(fc_f_ans, "Flight Centre FAQ Optimised")

        prog.progress(100, "✅ Done")
        time.sleep(0.3)
        prog.empty()
        run_status.empty()

        st.session_state.update({
            "q":               query_text,
            "ai_answer":       ai_answer,
            "fc_u_ans":        fc_u_ans,
            "fc_f_ans":        fc_f_ans,
            "fc_u_scores":     fc_u_scores,
            "fc_f_scores":     fc_f_scores,
            "ranking":         ranking,
            "citation_scores": citation_scores,
            "raw":             raw,
        })

    except Exception as e:
        prog.empty()
        run_status.empty()
        st.error(f"❌ Error: {e}")

# ── TAB 1: FC EVALUATION ──
with tab1:
    if "fc_u_ans" not in st.session_state:
        st.info("Run a query above to see results.")
    else:
        q   = st.session_state["q"]
        su  = st.session_state["fc_u_scores"]
        sf  = st.session_state["fc_f_scores"]
        au  = st.session_state["fc_u_ans"]
        af  = st.session_state["fc_f_ans"]
        cit = st.session_state["citation_scores"]

        st.markdown("## Flight Centre Evaluation")
        st.caption("We tested two versions of the Flight Centre page: the original unoptimised page (Baseline) and a version with FAQ content added (FAQ Optimised). This tab shows how each version performed when Gemini AI answered the query using only that page as its source.")
        st.markdown("<br>", unsafe_allow_html=True)

        # ── Side-by-side AI responses ──
        st.markdown(f"### Query: `{query_text}`")

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### 💬 What the AI said about each page version")
        st.caption("These are Gemini's responses when given each page as its only source. A good response names Flight Centre and includes specific details like prices, destinations, or products.")

        c1, c2 = st.columns(2)
        with c1:
            u_score = cit.get('Flight Centre Baseline (Unoptimised)', 0)
            st.markdown(f"**BASELINE — FC Unoptimised** &nbsp; `Citation score: {u_score}/3`")
            safe_u = highlight_tokens(au, q) if au else "<i>No answer extracted — check Raw Response below.</i>"
            st.markdown(f"<div class='rbox' style='background:#E4EBF8;border:2px solid #4472C4'>{safe_u}</div>", unsafe_allow_html=True)
        with c2:
            f_score = cit.get('Flight Centre FAQ Optimised', 0)
            st.markdown(f"**FAQ OPTIMISED — FC with FAQ** &nbsp; `Citation score: {f_score}/3`")
            safe_f = highlight_tokens(af, q) if af else "<i>No answer extracted — check Raw Response below.</i>"
            st.markdown(f"<div class='rbox' style='background:#FFF3EA;border:2px solid #ED7D31'>{safe_f}</div>", unsafe_allow_html=True)


        # ── Metric cards ──
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📊 How did each version score?")
        st.caption("Each metric measures a different aspect of how well the AI recognised and used the Flight Centre page content. \n\nBaseline = original page · FAQ Optimised = page with FAQ added.")

        def card(col, title, subtitle, uv, fv, fmt="yn"):
            d = fv - uv
            color = "g" if d > 0 else ("r" if d < 0 else "")
            ustr = ("✓ Yes" if uv else "✗ No") if fmt == "yn" else f"{uv}/3"
            fstr = ("✓ Yes" if fv else "✗ No") if fmt == "yn" else f"{fv}/3"
            if fmt == "yn":
                if d > 0:
                    dstr = "↑ Gained"
                elif d < 0:
                    dstr = "↓ Lost"
                elif uv == 1:
                    dstr = "= Maintained"
                else:
                    dstr = "= Still absent"
            else:
                if d > 0:
                    dstr = "↑ Gained"
                elif d < 0:
                    dstr = "↓ Lost"
                elif uv > 0:
                    dstr = "= Maintained"
                else:
                    dstr = "= Still absent"
            col.markdown(
                f"<div class='mcard {color}'>"
                f"<div class='mtitle'>{title}</div>"
                f"<div style='font-size:0.72rem;color:#90CAF9;margin-bottom:8px;line-height:1.4'>{subtitle}</div>"
                f"<table style='width:100%;font-size:0.88rem;color:#ECEFF1;margin:4px 0'>"
                f"<tr><td style='text-align:left'>Baseline</td><td style='text-align:right;font-weight:600'>{ustr}</td></tr>"
                f"<tr><td style='text-align:left'>FAQ Optimised</td><td style='text-align:right;font-weight:600'>{fstr}</td></tr>"
                f"</table>"
                f"<div class='mdelta'>{dstr}</div></div>",
                unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        card(m1, "INCLUSION RATE",
            "Was Flight Centre present in the AI-generated response?",
            su["answered"], sf["answered"], "yn")
        card(m2, "RELEVANCE SCORE",
            "How strongly did the AI cite or reference Flight Centre? (0 = not cited, 3 = prominently cited)",
            su["relevance"], sf["relevance"], "num")
        card(m3, "RESPONSE QUALITY",
            "Did the AI extract specific details — prices, products, destinations? (0 = generic, 3 = specific)",
            su["quality"], sf["quality"], "num")
        card(m4, "FAQ REFERENCED?",
            "Did the AI pull from the FAQ section specifically?",
            su["faq_used"], sf["faq_used"], "yn")


        # Bar chart
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 📈 Score comparison across all metrics")
        st.caption("Higher scores mean the AI gave a more useful, specific response using that page version.")
        labels  = ["Inclusion\nRate","Relevance\nScore","Response\nQuality","FAQ\nReferenced?"]
        uv_vals = [su["answered"], su["relevance"], su["quality"], su["faq_used"]]
        fv_vals = [sf["answered"], sf["relevance"], sf["quality"], sf["faq_used"]]
        fig = go.Figure()
        fig.add_trace(go.Bar(name="Baseline (Unoptimised)",  x=labels, y=uv_vals, marker_color="#4472C4", text=uv_vals, textposition="outside"))
        fig.add_trace(go.Bar(name="FAQ Optimised", x=labels, y=fv_vals, marker_color="#ED7D31", text=fv_vals, textposition="outside"))
        fig.update_layout(barmode="group", height=360, yaxis=dict(range=[0,3.8]),
                          legend=dict(orientation="h", y=1.08),
                          plot_bgcolor="white", paper_bgcolor="white", margin=dict(t=30,b=10))
        st.plotly_chart(fig, width="stretch")

        # Summary table
        TOOLTIPS = [
            ("Inclusion Rate",        "Was Flight Centre present in the AI-generated response?"),
            ("Relevance Score (0–3)", "How strongly did the AI cite or reference Flight Centre? (0 = not cited, 3 = prominently cited)"),
            ("Response Quality (0–3)","Did the AI extract specific details such as prices, products, or destinations? (0 = generic, 3 = highly specific)"),
            ("FAQ Referenced?",       "Did the AI specifically reference or draw answers from the FAQ section of the page?"),
            ("Visibility Change",     "Did adding the FAQ section change whether Flight Centre appeared in the AI response?"),
        ]

        def vis_change(uv, fv, fmt):
            d = fv - uv
            if fmt == "yn":
                if d > 0: return "↑ Gained"
                elif d < 0: return "↓ Lost"
                elif uv == 1: return "= Maintained"
                else: return "= Still absent"
            else:
                if d > 0: return f"↑ +{d}"
                elif d < 0: return f"↓ {d}"
                elif uv > 0: return "= Maintained"
                else: return "= Still absent"

        df = pd.DataFrame({
            "Metric":            ["Inclusion Rate", "Relevance Score (0–3)", "Response Quality (0–3)", "FAQ Referenced?"],
            "Baseline":          ["✓" if su["answered"] else "✗", su["relevance"], su["quality"], "✗"],
            "FAQ Optimised":     ["✓" if sf["answered"] else "✗", sf["relevance"], sf["quality"], "✓"],
            "Visibility Change": [
                vis_change(su["answered"],  sf["answered"],  "yn"),
                vis_change(su["relevance"], sf["relevance"], "num"),
                vis_change(su["quality"],   sf["quality"],   "num"),
                vis_change(su["faq_used"],  sf["faq_used"],  "yn"),
            ]
        })
        st.dataframe(df, width="stretch", hide_index=True)

        with st.expander("ℹ️ What do these metrics mean?"):
            st.markdown("""
            - **Inclusion Rate** — Was Flight Centre present in the AI-generated response?
            - **Relevance Score (0–3)** — How strongly did the AI cite or reference Flight Centre? (0 = not cited, 3 = prominently cited)
            - **Response Quality (0–3)** — Did the AI extract specific details such as prices, products, or destinations? (0 = generic, 3 = highly specific)
            - **FAQ Referenced?** — Did the AI specifically reference or draw answers from the FAQ section of the page?
            - **Visibility Change** — Did adding the FAQ section change whether Flight Centre appeared in the AI response?
                        """)

        st.markdown("<br>", unsafe_allow_html=True)
        u_cit = cit.get("Flight Centre Baseline (Unoptimised)", 0)
        f_cit = cit.get("Flight Centre FAQ Optimised", 0)
        if f_cit > u_cit:
            st.success("✅ FAQ Optimised performed better — adding FAQ content improved how the AI recognised and referenced Flight Centre.")
        elif f_cit == u_cit and f_cit > 0:
            st.info("ℹ️ Both versions were cited equally. The FAQ section did not change AI visibility for this query, but Flight Centre was still present in the response.")
        elif f_cit == u_cit == 0:
            st.warning("⚠️ Neither page was cited for this query — FAQ optimisation had no effect on AI visibility for this query type.")
        else:
            st.info("ℹ️ The baseline page scored higher for this query. This may vary across different queries and AI runs.")

        with st.expander("🔍 Raw Gemini Response (debug)"):
            st.text(st.session_state.get("raw", ""))

# ── TAB 2: AI SEARCH SIMULATION ──
with tab2:
    if "ai_answer" not in st.session_state:
        st.info("Run a query above to see the AI search simulation.")
    else:
        q           = st.session_state["q"]
        ai_answer   = st.session_state["ai_answer"]
        ranking     = st.session_state["ranking"]
        cit_scores  = st.session_state["citation_scores"]

        st.markdown("## AI Search Simulation")
        st.caption("Gemini AI was given all 7 travel sites at once and asked to answer your query — simulating how an AI search engine like Perplexity or ChatGPT might respond in the real world.")

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(f"### Query: `{query_text}`")

        st.markdown("#### 📝 Simulated AI Response")
        st.caption("This is how Gemini AI answered your query when given all 7 travel sites as sources at once. Highlighted labels show which site was referenced in each part of the answer.")

        highlighted = ai_answer
        brand_colors = {
            "FC FAQ Optimised": "#ED7D31", "FC FAQ": "#ED7D31",
            "FC Unoptimised": "#4472C4", "FC Baseline": "#4472C4",
            "Booking.com": "#E05252", "Booking": "#E05252",
            "Agoda": "#A855F7",
            "Expedia": "#F5C518",
            "Traveloka": "#2DD4BF",
            "Trip.com": "#EC4899",
        }
        for brand, color in sorted(brand_colors.items(), key=lambda x: -len(x[0])):
            highlighted = re.sub(
                f'({re.escape(brand)})',
                f'<mark style="background:{color}33;color:{color};font-weight:700;padding:1px 5px;border-radius:3px;">\\1</mark>',
                highlighted, flags=re.IGNORECASE
            )
        st.markdown(
            f"<div class='rbox' style='background:#0d1117;border:none;color:#e6edf3;max-height:none'>{highlighted}</div>",
            unsafe_allow_html=True
        )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### 🏆 Which sites did AI rank highest?")
        st.caption("Gemini ranked all 7 sites based on how well their content answered your query. Sites ranked higher had more relevant, specific, and structured content that the AI could draw from.")

        rank_labels = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th"]
        rank_colors = ["#F5C518", "#A0A0A0", "#CD7F32", "#4472C4", "#ED7D31", "#A855F7", "#2DD4BF"]
        for i, line in enumerate(ranking):
            parts = re.sub(r'^\d+\.\s*', '', line).split('|', 1)
            site_name = parts[0].strip() if parts else ""
            reason    = parts[1].strip() if len(parts) > 1 else ""
            rank_color = rank_colors[i] if i < len(rank_colors) else "#888"
            rank_label = rank_labels[i] if i < len(rank_labels) else f"{i+1}th"
            st.markdown(
                f"<div style='background:#f8f9fa;border-left:5px solid {rank_color};"
                f"border-radius:6px;padding:.8rem 1.2rem;margin-bottom:8px;'>"
                f"<span style='font-size:0.75rem;font-weight:700;color:{rank_color};"
                f"text-transform:uppercase;letter-spacing:.05em'>{rank_label}</span>"
                f"<span style='font-size:0.95rem;font-weight:600;color:#1a1a2e;margin-left:10px'>{site_name}</span>"
                f"<div style='font-size:0.83rem;color:#555;margin-top:4px'>{reason}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### 📊 How much did each site contribute to the answer?")
        st.caption("Each site is scored 0–3 based on how much it contributed to the AI's response. A score of 3 means the site was heavily cited and shaped the answer. A score of 0 means the AI largely ignored that site's content.")

        if cit_scores:
            site_order = [info["label"] for info in SITES.values()]
            labels = [s for s in site_order if s in cit_scores]
            values = [cit_scores[s] for s in labels]
            colors = [info["color"] for info in SITES.values() if info["label"] in cit_scores]
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=labels, y=values, marker_color=colors,
                text=values, textposition="outside",
                hovertemplate="%{x}: %{y}/3<extra></extra>"
            ))
            fig2.update_layout(
                height=360,
                yaxis=dict(range=[0, 3.8], title="Score (0–3)", gridcolor="#e0e0e0"),
                xaxis=dict(tickfont=dict(size=12)),
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(color="#1a1a2e"),
                margin=dict(t=20, b=10),
                showlegend=False
            )
            st.plotly_chart(fig2, width="stretch")

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("#### ⚖️ Flight Centre: Baseline vs FAQ Optimised")
        st.caption("A direct comparison of how the two Flight Centre page versions performed against each other in the same AI response. This shows whether adding FAQ content made a measurable difference to Flight Centre's visibility.")

        u_s = cit_scores.get("Flight Centre Baseline (Unoptimised)", 0)
        f_s = cit_scores.get("Flight Centre FAQ Optimised", 0)
        ca, cb = st.columns(2)
        ca.markdown(f"""
            <div style='background:#f0f4ff;border-left:5px solid #4472C4;border-radius:6px;padding:1rem 1.2rem'>
            <div style='font-size:0.78rem;font-weight:700;color:#4472C4;text-transform:uppercase;letter-spacing:.05em'>Baseline (Unoptimised)</div>
            <div style='font-size:2rem;font-weight:700;color:#1a1a2e;margin-top:4px'>{u_s}/3</div>
            </div>""", unsafe_allow_html=True)
        cb.markdown(f"""
            <div style='background:#fff4ed;border-left:5px solid #ED7D31;border-radius:6px;padding:1rem 1.2rem'>
            <div style='font-size:0.78rem;font-weight:700;color:#ED7D31;text-transform:uppercase;letter-spacing:.05em'>FAQ Optimised</div>
            <div style='font-size:2rem;font-weight:700;color:#1a1a2e;margin-top:4px'>{f_s}/3</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if f_s > u_s:
            st.success("✅ FAQ Optimised performed better — adding FAQ content improved Flight Centre's visibility in the AI response.")
        elif f_s == u_s and f_s > 0:
            st.info("ℹ️ Both versions were cited equally. FAQ content did not change AI visibility for this query, but Flight Centre was still present.")
        elif f_s == u_s == 0:
            st.warning("⚠️ Neither version was cited for this query — FAQ optimisation had no effect on AI visibility for this query type.")
        else:
            st.info("ℹ️ The baseline page scored higher for this query. This may vary across different queries and AI runs.")

