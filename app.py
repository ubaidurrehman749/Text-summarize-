import re
from collections import Counter

import streamlit as st

st.set_page_config(page_title="Text Summarizer · Study Sparks AI", page_icon="✦", layout="wide")

# ---------- Styling ----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:wght@600;800&family=DM+Sans:wght@400;500;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.5rem; max-width: 1150px; }
.brand { font-family:'Bricolage Grotesque',sans-serif; font-weight:800; font-size:1.4rem; color:#1B1740; }
.brand span { color:#FFB627; } .brand b { color:#6B4EFF; }
.hero h1 { font-family:'Bricolage Grotesque',sans-serif; font-weight:800; font-size:2.6rem;
           line-height:1.1; color:#1B1740; margin:.6rem 0 .3rem; letter-spacing:-.02em; }
.hero p { color:#4B466F; font-size:1.1rem; margin-bottom:1.2rem; }
.summary-box { background:#fff; border-left:6px solid #FFB627; border-radius:14px; padding:18px 20px;
               font-size:1.05rem; line-height:1.75; color:#1B1740; box-shadow:0 14px 30px -22px rgba(27,23,64,.5); }
.chip { display:inline-block; background:rgba(107,78,255,.12); color:#6B4EFF; padding:4px 12px;
        border-radius:999px; font-weight:700; font-size:.88rem; margin:0 6px 6px 0; }
div.stButton > button:first-child, div.stDownloadButton > button {
    background:#6B4EFF; color:#fff; border:0; border-radius:12px; padding:.65rem 1.2rem; font-weight:700; }
div.stButton > button:first-child:hover, div.stDownloadButton > button:hover { background:#5237E0; color:#fff; }
[data-testid="stMetricValue"] { color:#23B89A; font-family:'Bricolage Grotesque',sans-serif; }
textarea { border-radius:14px !important; }
</style>
<div class="brand"><span>✦</span> Study Sparks <b>AI</b></div>
<div class="hero">
  <h1>Turn long notes into a summary you can revise from.</h1>
  <p>Paste a chapter, article or lecture transcript. Pick a length. Get the key points.</p>
</div>
""", unsafe_allow_html=True)

# ---------- Summarizer logic ----------
STOP = set("""a about above after again all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have having he her
here hers him his how i if in into is it its just me more most my no nor not now of off on once only or other our
out over own same she should so some such than that the their them then there these they this those through to too
under until up very was we were what when where which while who whom why will with would you your""".split())

LEVELS = {"Short": (0.15, 2, 4), "Medium": (0.30, 3, 8), "Detailed": (0.45, 4, 14)}
MIN_WORDS = 40


def words_of(text):
    return re.findall(r"[\w'’-]+", text)


def split_sentences(text):
    text = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p for p in parts if len(words_of(p)) >= 4]


def local_summarize(text, level):
    sentences = split_sentences(text)
    freq = Counter(w for w in (x.lower() for x in words_of(text))
                   if w not in STOP and len(w) > 2 and not w.isdigit())
    if not freq:
        return []
    top = max(freq.values())
    scored = []
    for i, s in enumerate(sentences):
        ws = [w.lower() for w in words_of(s)]
        score = sum(freq[w] / top for w in ws if w in freq) / (len(ws) ** 0.5)
        if i == 0:
            score *= 1.35
        elif i == len(sentences) - 1:
            score *= 1.1
        if len(ws) > 45:
            score *= 0.75
        if re.search(r"\b(important|key|main|therefore|in conclusion|significant|defined as|means)\b", s, re.I):
            score *= 1.15
        scored.append((score, i, s))
    ratio, lo, hi = LEVELS[level]
    n = min(hi, max(lo, round(len(sentences) * ratio)))
    best = sorted(scored, reverse=True)[:n]
    return [s for _, _, s in sorted(best, key=lambda x: x[1])]


def top_keywords(text, n=8):
    f = Counter(w for w in (x.lower() for x in words_of(text))
                if w not in STOP and len(w) > 3 and not w.isdigit())
    return [w for w, _ in f.most_common(n)]


def ai_summarize(text, level, fmt):
    import anthropic
    client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    size = {"Short": "2-3 sentences", "Medium": "4-6 sentences", "Detailed": "8-10 sentences"}[level]
    style = ('Return only bullet points, one per line, each starting with "- ".'
             if fmt == "Bullet points" else "Return a single clear paragraph with no heading.")
    prompt = (f"Summarize the following study material for a student. Keep it accurate and simple, in the "
              f"original language. Length: about {size}. {style} No commentary.\n\n<text>\n{text[:60000]}\n</text>")
    msg = client.messages.create(model="claude-sonnet-5-5", max_tokens=1000,
                                 messages=[{"role": "user", "content": prompt}])
    out = msg.content[0].text.strip()
    return [re.sub(r"^[-•*]\s*", "", l).strip() for l in out.splitlines() if l.strip()]


def ai_available():
    try:
        return "ANTHROPIC_API_KEY" in st.secrets
    except Exception:
        return False


SAMPLE = ("Photosynthesis is the process by which green plants, algae and some bacteria convert light energy into "
          "chemical energy. It takes place mainly in the chloroplasts, which contain a green pigment called "
          "chlorophyll. Chlorophyll absorbs sunlight, especially in the red and blue wavelengths, and reflects "
          "green light, which is why leaves look green. The process has two main stages. In the light-dependent "
          "reactions, sunlight splits water molecules, releasing oxygen and producing the energy carriers ATP and "
          "NADPH. In the Calvin cycle, the plant uses ATP and NADPH to turn carbon dioxide from the air into "
          "glucose. Glucose is then used for growth, stored as starch, or broken down during cellular respiration "
          "to release energy. Light intensity, carbon dioxide concentration and temperature all affect the rate of "
          "photosynthesis. If any of these is in short supply it becomes a limiting factor and slows the whole "
          "process. Photosynthesis is important for life on Earth because it produces the oxygen we breathe, forms "
          "the base of nearly every food chain, and removes carbon dioxide from the atmosphere.")

if "text" not in st.session_state:
    st.session_state.text = ""
if "result" not in st.session_state:
    st.session_state.result = None


def load_sample():
    st.session_state.text = SAMPLE


def clear_all():
    st.session_state.text = ""
    st.session_state.result = None


# ---------- Layout ----------
left, right = st.columns(2, gap="large")

with left:
    st.subheader("Your text")
    st.text_area("Paste or type at least 40 words", key="text", height=280,
                 placeholder="Paste your notes or article here…", label_visibility="collapsed")
    n_words = len(words_of(st.session_state.text))
    st.caption(f"{n_words:,} words · {max(1 if n_words else 0, round(n_words / 220))} min read")

    b1, b2, _ = st.columns([1, 1, 2])
    b1.button("Try sample", on_click=load_sample, use_container_width=True)
    b2.button("Clear", on_click=clear_all, use_container_width=True)

    level = st.select_slider("Summary length", options=list(LEVELS), value="Medium")
    fmt = st.radio("Format", ["Paragraph", "Bullet points"], horizontal=True)
    engines = ["Quick (offline)"] + (["AI (smarter)"] if ai_available() else [])
    engine = st.radio("Engine", engines, horizontal=True)

    go = st.button("Summarize text", type="primary", use_container_width=True)

if go:
    text = st.session_state.text.strip()
    if len(words_of(text)) < MIN_WORDS:
        st.session_state.result = {"error": f"Add a bit more text. At least {MIN_WORDS} words are needed."}
    else:
        try:
            with st.spinner("Reading your text…"):
                sents = ai_summarize(text, level, fmt) if engine.startswith("AI") else local_summarize(text, level)
            if not sents:
                raise ValueError("Could not find enough sentences. Try longer text with full sentences.")
            st.session_state.result = {"sents": sents, "fmt": fmt, "orig": text}
        except Exception as e:
            st.session_state.result = {"error": f"Something went wrong: {e}"}

with right:
    st.subheader("Summary")
    r = st.session_state.result
    if not r:
        st.info("Your summary will appear here. Paste some text and select **Summarize text**.")
    elif "error" in r:
        st.error(r["error"])
    else:
        sents = r["sents"]
        if r["fmt"] == "Bullet points":
            body = "<ul>" + "".join(f"<li>{s}</li>" for s in sents) + "</ul>"
            plain = "\n".join("• " + s for s in sents)
        else:
            body = " ".join(sents)
            plain = body
        st.markdown(f'<div class="summary-box">{body}</div>', unsafe_allow_html=True)

        in_w, out_w = len(words_of(r["orig"])), len(words_of(" ".join(sents)))
        m1, m2, m3 = st.columns(3)
        m1.metric("Words in summary", f"{out_w:,}")
        m2.metric("Shorter by", f"{max(0, round((1 - out_w / in_w) * 100))}%")
        m3.metric("Key sentences", len(sents))

        st.markdown("**Key terms**")
        st.markdown("".join(f'<span class="chip">{k}</span>' for k in top_keywords(r["orig"])),
                    unsafe_allow_html=True)
        st.download_button("Download .txt", plain, file_name="study-sparks-summary.txt")
        with st.expander("Copy summary"):
            st.code(plain, language=None)

st.markdown("<hr><center style='color:#4B466F'>© Study Sparks AI · Made for curious students</center>",
            unsafe_allow_html=True)
