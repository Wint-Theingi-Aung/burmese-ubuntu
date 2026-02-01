import streamlit as st
import polib, os, google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
# API Key ကို ရယူသည်
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

# အရေးကြီးသည်- 'models/' prefix မပါဘဲ model name ကို တိုက်ရိုက်သုံးပါ
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Final PO Translator", layout="wide")
st.title("🚀 Fast Auto-Fill Translator")

file = st.file_uploader("Upload .po", type=['po'])

if file:
    # Session State ထဲတွင် ဒေတာများကို ကနဦး သိမ်းဆည်းခြင်း
    if 'po' not in st.session_state or st.session_state.file_name != file.name:
        st.session_state.po = polib.pofile(file.getvalue().decode("utf-8"))
        st.session_state.file_name = file.name
        # Dictionary စနစ်သည် UI update ဖြစ်ရန် အကောင်းဆုံးဖြစ်သည်
        st.session_state.translations = {e.msgid: e.msgstr for e in st.session_state.po}

    po = st.session_state.po
    # ဘာသာပြန်ရန် ကျန်ရှိသော စာကြောင်းများကို ရှာဖွေသည်
    untranslated = [e for e in po if not st.session_state.translations.get(e.msgid) and e.msgid]
    
    if untranslated:
        page_size = 10
        total_pages = (len(untranslated) // page_size) + (1 if len(untranslated) % page_size > 0 else 0)
        page = st.sidebar.number_input("Page", 1, total_pages, 1)
        
        start_idx = (page - 1) * page_size
        current_batch = untranslated[start_idx : start_idx + page_size]

        st.info(f"ကျန်ရှိသော Untranslated: {len(untranslated)} (Page {page}/{total_pages})")

        # --- Batch Translation ခလုတ် ---
        if st.button(f"⚡ Auto-Translate Page {page}"):
            with st.spinner("Batch Processing..."):
                combined_text = "\n---\n".join([e.msgid for e in current_batch])
                prompt = f"Translate these to Burmese for software UI. Separate with '---'. Keep variables intact. Strings:\n{combined_text}"
                
                try:
                    # Model ခေါ်ယူမှု (ဒီနေရာတွင် 404 မတက်စေရန် အပေါ်တွင် model ကို ပြင်ဆင်ထားသည်)
                    response = model.generate_content(prompt)
                    # အဖြေများကို ခွဲထုတ်ပြီး session state ထဲ တန်းထည့်ခြင်းက auto-fill ဖြစ်စေသည်
                    results = [r.strip() for r in response.text.split('---') if r.strip()]
                    
                    for i, entry in enumerate(current_batch):
                        if i < len(results):
                            st.session_state.translations[entry.msgid] = results[i]
                    
                    # မျက်နှာပြင်ကို အလိုအလျောက် ပြန်ဆွဲခြင်း (Auto-fill မြင်ရစေရန်)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        # --- UI ပိုင်း (Auto-fill အတွက် အဓိကအပိုင်း) ---
        st.divider()
        for entry in current_batch:
            col1, col2 = st.columns(2)
            col1.text_area("English", entry.msgid, height=70, disabled=True)
            
            # Key နှင့် Value ကို session_state နှင့် တိုက်ရိုက်ချိတ်ဆက်ထားသည်
            # ဒါမှသာ AI က ပြန်ပေးလိုက်တဲ့ စာသားတွေ ချက်ချင်း ပေါ်လာမှာပါ
            val = st.session_state.translations.get(entry.msgid, "")
            updated_val = col2.text_area("Burmese", value=val, height=70, key=f"t_{entry.msgid}")
            
            # User လက်ဖြင့် ပြင်ဆင်ပါကလည်း ချက်ချင်း မှတ်သားသည်
            st.session_state.translations[entry.msgid] = updated_val

    else:
        st.success("အားလုံး ပြီးသွားပါပြီ!")

    st.divider()
    # ဖိုင်ကို သိမ်းဆည်းရန် ပြင်ဆင်ခြင်း
    if st.button("Download Final .PO"):
        for entry in po:
            entry.msgstr = st.session_state.translations.get(entry.msgid, "")
        st.download_button("Click to Confirm Download", data=po.__str__(), file_name="translated.po")