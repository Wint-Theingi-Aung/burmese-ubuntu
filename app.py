import os, polib, pandas as pd, streamlit as st, time
import google.generativeai as genai
from dotenv import load_dotenv

# Environment variables ကို load လုပ်ခြင်း
load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")

# SDK ကို configure လုပ်ခြင်း
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.sidebar.error("GOOGLE_API_KEY မတွေ့ပါ။ .env ဖိုင်ကို စစ်ဆေးပေးပါ။")

st.set_page_config(page_title="PO Translator", layout="wide")

# UI Layout ကို သေသပ်အောင် CSS နဲ့ ပြင်ဆင်ခြင်း
st.markdown("""
    <style>
    [data-testid="stSidebar"] { min-width: 200px; max-width: 250px; }
    .stButton button { border-radius: 6px; height: 3em; }
    .stTextArea textarea { font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# Session State များ ကနဦးသတ်မှတ်ခြင်း
if "df" not in st.session_state: st.session_state.df = None
if "po" not in st.session_state: st.session_state.po = None
if "page" not in st.session_state: st.session_state.page = 0
if "filename" not in st.session_state: st.session_state.filename = "messages"

def translate_batch(texts, target_lang):
    """Google Generative AI SDK ကို အသုံးပြု၍ ဘာသာပြန်ခြင်း"""
    try:
        # Model နာမည်ကို gemini-1.5-flash-latest ဟု တိကျစွာ ပြောင်းလဲထားပါသည်
        # ၎င်းသည် v1beta နှင့် v1 နှစ်ခုလုံးတွင် အဆင်ပြေဆုံး version ဖြစ်ပါသည်
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = f"""Translate these {len(texts)} software strings into {target_lang}.
Output format: Return ONLY the translated strings, one per line.
Rules:
- No markdown formatting.
- No numbering.
- No quotes.
- Keep original line count.

TEXTS:
""" + "\n".join(texts)
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            raw_text = response.text.strip()
            # Markdown block များ ပါလာပါက ဖယ်ထုတ်ရန်
            clean_text = raw_text.replace("```text", "").replace("```", "").strip()
            lines = [l.strip() for l in clean_text.split("\n") if l.strip()]
            return lines
    except Exception as e:
        # Error တက်ခဲ့လျှင် မည်သည့်အချက်ကြောင့်ဖြစ်သည်ကို sidebar တွင်ပြသရန်
        st.sidebar.error(f"AI Error: {str(e)}")
    return []

# --- Sidebar (ဘေးဘား) ---
with st.sidebar:
    st.markdown("## Settings")
    lang = st.selectbox("Target Language", ["Burmese", "Shan", "Mon", "Karen"])
    st.divider()
    
    if st.session_state.df is not None:
        base_name = os.path.splitext(st.session_state.filename)[0]
        final_filename = f"{base_name}_{lang.lower()}.po"
        
        # DataFrame မှ ပြင်ဆင်ချက်များကို PO file ထဲသို့ ပြန်လည်ထည့်သွင်းခြင်း
        for _, r in st.session_state.df.iterrows():
            st.session_state.po[r["ID"]].msgstr = r["Translation"]
            
        st.download_button("Download PO File", st.session_state.po.__str__(), final_filename, use_container_width=True)

st.title("PO Translator")

# ဖိုင်တင်ရန်နေရာ
up_file = st.file_uploader("Upload .po file", type=["po"])
if up_file:
    if st.session_state.po is None or up_file.name != st.session_state.filename:
        st.session_state.filename = up_file.name
        st.session_state.po = polib.pofile(up_file.getvalue().decode("utf-8"))
        
        # --- UNTRANSLATED ONLY LOGIC ---
        data = []
        for i, entry in enumerate(st.session_state.po):
            if not entry.msgstr:
                data.append({"ID": i, "Original": entry.msgid, "Translation": ""})
        
        st.session_state.df = pd.DataFrame(data)
        st.session_state.page = 0

# ဘာသာပြန်ရမည့် ဇယားကို ပြသခြင်း
if st.session_state.df is not None:
    df = st.session_state.df
    if df.empty:
        st.success("ဘာသာပြန်ရန် မကျန်တော့ပါ။ အားလုံးပြီးစီးပါပြီ!")
    else:
        size, pg = 10, st.session_state.page
        total_pgs = (len(df) // size) + (1 if len(df) % size > 0 else 0)
        start, end = pg * size, (pg + 1) * size

        st.caption(f"Untranslated items: {len(df)} | Page {pg + 1} of {total_pgs}")

        for i in range(start, min(end, len(df))):
            c1, c2 = st.columns(2)
            with c1: st.text_area("Original", df.at[i, "Original"], height=85, disabled=True, key=f"o_{i}", label_visibility="collapsed")
            with c2:
                val = st.text_area("Translation", value=df.at[i, "Translation"], height=85, key=f"t_{i}", label_visibility="collapsed")
                st.session_state.df.at[i, "Translation"] = val

        st.divider()

        # ခလုတ်များ
        c_auto, c_prev, c_next = st.columns([2, 1, 1])

        with c_auto:
            if st.button(f"Autofill with AI ({lang})", use_container_width=True):
                page_data = df.iloc[start:end]
                target_idxs = page_data[page_data["Translation"].str.strip() == ""].index.tolist()
                texts = [df.at[idx, "Original"] for idx in target_idxs]
                
                if texts:
                    with st.spinner("AI ဘာသာပြန်နေပါသည်..."):
                        results = translate_batch(texts, lang)
                        if results:
                            for j, res in enumerate(results):
                                if j < len(target_idxs):
                                    st.session_state.df.at[target_idxs[j], "Translation"] = res
                            st.rerun()
                else:
                    st.info("ဤစာမျက်နှာအတွက် ဖြည့်စွက်ပြီးပါပြီ။")

        with c_prev:
            if st.button("Previous", use_container_width=True, disabled=(pg == 0)):
                st.session_state.page -= 1
                st.rerun()

        with c_next:
            if st.button("Next", use_container_width=True, disabled=(pg >= total_pgs - 1)):
                st.session_state.page += 1
                st.rerun()