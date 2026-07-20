import json

import streamlit as st

from src.pipeline import load_topics, run_pipeline


st.set_page_config(page_title="YouTube Otomasyon MVP", page_icon="🎬", layout="wide")
st.title("YouTube Otomasyon MVP")
st.caption("Güvenli test modu • API ücreti yok • Otomatik YouTube yüklemesi yok")

topics = load_topics()
selected_title = st.selectbox("Konu seçin", [item["title"] for item in topics])
minutes = st.slider("Hedef video süresi", 5, 8, 5)
topic = next(item for item in topics if item["title"] == selected_title)

st.info(f"Yaklaşım: {topic['angle']}\n\nHedef kitle: {topic['audience']}")

if st.button("Test videosu paketini üret", type="primary"):
    with st.spinner("Senaryo, sahneler, test sesi ve görseller hazırlanıyor..."):
        try:
            result = run_pipeline(topic, minutes)
        except Exception as exc:
            st.error(f"Üretim tamamlanamadı: {exc}")
        else:
            st.session_state["result"] = result

result = st.session_state.get("result")
if result:
    content = result["content"]
    st.success(result["message"])
    st.subheader(content.title)
    col1, col2 = st.columns(2)
    with col1:
        st.image(str(result["project_dir"] / "thumbnail.png"), caption="Test kapak görseli")
        st.text_area("Açıklama", content.description, height=150)
        st.write("Etiketler:", ", ".join(content.tags))
    with col2:
        st.text_area("Senaryo", content.script, height=360)

    st.warning(
        "Bu çıktı sahte/test verisidir. Bilgi, kaynak, telif, ses ve görseller insan tarafından "
        "kontrol edilmeden yayınlanmamalıdır."
    )
    approved = st.checkbox("İçeriği insan olarak kontrol ettim ve onaylıyorum")
    if st.button("Onayı kaydet", disabled=not approved):
        status_file = result["project_dir"] / "approval_status.json"
        status_file.write_text(
            json.dumps(
                {"approved": True, "youtube_uploaded": False, "note": "Yalnızca yerel onay kaydedildi."},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        st.success("Onay kaydedildi. YouTube'a yükleme yapılmadı.")
