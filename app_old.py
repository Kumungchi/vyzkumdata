# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import time

from utils import standardize_hand_columns, compute_deltas
from pdf_utils import build_pdf_report
from error_handler import (
    safe_read_csv, validate_data_structure, safe_numeric_conversion,
    validate_user_id, handle_exception, log_user_activity, logger
)

st.set_page_config(page_title="Osobní emoční profil", layout="wide", page_icon="📊")

DATA_DIR = Path("data")
HELP_TEXT_INTRO = """
**Jak číst prostor emocí:**
- **Osa X = Valence** (negativní ↔ pozitivní)
- **Osa Z = Arousal** (nízký ↔ vysoký)
- **Osa Y = Dominance** (nízká ↔ vysoká kontrola)

**Jak číst Δ metriky:**
- **Δ valence** = o kolik jsi posunul(a) slovo v ose X oproti jeho výchozímu „štítku".
- **Δ arousal**  = o kolik jsi posunul(a) slovo v ose Z oproti jeho výchozímu „štítku".
- **Reakční doba** = průměrný čas rozhodnutí (menší = rychlejší).
"""

# Přidání cachingu pro lepší performance
@st.cache_data(ttl=3600)  # Cache na 1 hodinu
def load_and_process_data():
    """Načte a zpracuje data s cachingem"""
    start_time = time.time()
    
    # Načítání dat s error handlingem
    vybrana = safe_read_csv(DATA_DIR / "vybrana_slova_30.csv")
    hand = safe_read_csv(DATA_DIR / "hand_dataset.csv", sep=";", engine="python")
    
    if vybrana is None or hand is None:
        st.stop()
    
    # Validace struktury dat
    vybrana_required = ["Valence", "Arousal"] 
    hand_required = ["ID", "Term", "Pos X", "Pos Y", "Pos Z", "First reaction time"]
    
    if not validate_data_structure(vybrana, vybrana_required, "baseline dataset"):
        st.stop()
    if not validate_data_structure(hand, hand_required, "hand dataset"):
        st.stop()
    
    # Standardizace a numerická konverze
    hand = standardize_hand_columns(hand)
    numeric_cols = ["Pos X", "Pos Y", "Pos Z", "First reaction time", "Total reaction time"]
    hand = safe_numeric_conversion(hand, numeric_cols)
    
    # Načtení uživatelů (volitelné)
    users = None
    if (DATA_DIR / "users.csv").exists():
        users = safe_read_csv(DATA_DIR / "users.csv")
    
    load_time = time.time() - start_time
    logger.info(f"Data načtena za {load_time:.2f} sekund")
    
    return vybrana, hand, users

@handle_exception
def main():
    """Hlavní funkce aplikace s error handlingem"""

DATA_DIR = Path("data")
HELP_TEXT_INTRO = """
**Jak číst prostor emocí:**
- **Osa X = Valence** (negativní ↔ pozitivní)
- **Osa Z = Arousal** (nízký ↔ vysoký)
- **Osa Y = Dominance** (nízká ↔ vysoká kontrola)

**Jak číst Δ metriky:**
- **Δ valence** = o kolik jsi posunul(a) slovo v ose X oproti jeho výchozímu „štítku“.
- **Δ arousal**  = o kolik jsi posunul(a) slovo v ose Z oproti jeho výchozímu „štítku“.
- **Reakční doba** = průměrný čas rozhodnutí (menší = rychlejší).
"""

# -----------------------------
# 1) Načítání dat (pouze z /data složky)
# -----------------------------
try:
    vybrana = pd.read_csv(DATA_DIR / "vybrana_slova_30.csv")
    hand = pd.read_csv(DATA_DIR / "hand_dataset.csv", sep=";", engine="python")
except FileNotFoundError as e:
    st.error(f"Chyba při načítání dat: {e}")
    st.error("Ujistěte se, že jsou v složce 'data' soubory: vybrana_slova_30.csv a hand_dataset.csv")
    st.stop()

users = None
if (DATA_DIR / "users.csv").exists():
    users = pd.read_csv(DATA_DIR / "users.csv")

hand = standardize_hand_columns(hand)

# -----------------------------
# 2) Validace dat
# -----------------------------
missing_v = [c for c in ["Valence","Arousal"] if c not in vybrana.columns]
missing_h = [c for c in ["ID","Term","Pos X","Pos Y","Pos Z","First reaction time"] if c not in hand.columns]

if missing_v:
    st.error(f"Baseline chybí sloupce: {missing_v}. Zkontroluj hlavičky v CSV (30 slov).")
if missing_h:
    st.error(f"Hand dataset chybí sloupce: {missing_h}. Zkontroluj hlavičky v CSV.")
if missing_v or missing_h:
    st.stop()
else:
    st.success("✅ Data vypadají v pořádku. Pokračuji…")

# -----------------------------
# 3) Získání ID z URL (povinné)
# -----------------------------
deltas_all = compute_deltas(hand, vybrana)

# ID musí být zadáno v URL
try:
    q = st.query_params
    selected_id = q.get("ID", None)
    if isinstance(selected_id, list):
        selected_id = selected_id[0] if selected_id else None
except Exception:
    try:
        q = st.experimental_get_query_params()
        selected_id = q.get("ID", [None])[0] if q else None
    except:
        selected_id = None

if not selected_id:
    st.error("🚫 **Chyba přístupu**")
    st.error("Pro zobrazení vašeho osobního reportu je potřeba validní ID v URL.")
    st.info("Správný formát: `?ID=vase_id`")
    st.info("Příklad: `http://localhost:8501?ID=12345`")
    st.stop()

# Zkontroluj, zda ID existuje v datech
available_ids = sorted(deltas_all["ID"].dropna().astype(str).unique())
if str(selected_id) not in available_ids:
    st.error(f"🚫 **ID '{selected_id}' nebylo nalezeno**")
    st.error("Vaše ID není v databázi účastníků. Kontaktujte prosím organizátory studie.")
    st.stop()

sub = deltas_all[deltas_all["ID"].astype(str) == str(selected_id)].copy()
if sub.empty:
    st.error(f"Pro ID `{selected_id}` nebyla nalezena data.")
    st.stop()

# Skupinové průměry (dominance = Pos Y; bez baseline)
# Počítáme z dat všech účastníků pro srovnání, ale nezobrazujeme konkrétní hodnoty jiných
overall = deltas_all[["delta_valence","delta_arousal","First reaction time","Pos Y"]].mean(numeric_only=True)

# Uživatelské průměry
user_val = sub["delta_valence"].mean()
user_ar  = sub["delta_arousal"].mean()
user_rt  = sub["First reaction time"].mean()
user_dom = sub["Pos Y"].mean()
words_n  = sub["Term"].nunique()

# -----------------------------
# 4) Úvod + metriky + PDF (nahoře)  
# -----------------------------
st.title(f"🎯 Tvůj osobní report — {selected_id}")
st.markdown("**Děkujeme za účast ve studii!** Níže najdeš svůj osobní přehled výsledků.")
st.info("💡 **Tip:** Tento report si můžeš stáhnout jako PDF pomocí tlačítka níže.")
st.markdown(HELP_TEXT_INTRO)

    # Zbytek kódu se přesune do main() funkce
    
    # Metrickky
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Hodnocených slov", f"{words_n}")
    c2.metric("Δ valence (X)", f"{user_val:.2f}", f"{user_val - overall['delta_valence']:+.2f} vs. průměr")
    c3.metric("Δ arousal (Z)", f"{user_ar:.2f}",  f"{user_ar - overall['delta_arousal']:+.2f} vs. průměr")
    c4.metric("Dominance (Y)", f"{user_dom:.2f}", f"{user_dom - overall['Pos Y']:+.2f} vs. průměr")

    # Pokračování implementace...

# -----------------------------
# 5) Grafy – tvorba
# -----------------------------
# Radar
radar_categories = ["Δ valence (X)","Δ arousal (Z)","Reakční doba"]
fig_radar = go.Figure()
fig_radar.add_trace(go.Scatterpolar(r=[user_val,user_ar,user_rt], theta=radar_categories, fill='toself', name='Ty'))
fig_radar.add_trace(go.Scatterpolar(r=[overall["delta_valence"],overall["delta_arousal"],overall["First reaction time"]],
                                    theta=radar_categories, fill='toself', name='Průměr'))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True)), showlegend=True)

# Histogramy
fig_hist_val = px.histogram(deltas_all, x="delta_valence", nbins=20, title="Distribuce Δ valence (pro srovnání)")
fig_hist_val.add_vline(x=user_val, line_dash="dash", line_color="red", annotation_text="Tvá hodnota")

fig_hist_ar = px.histogram(deltas_all, x="delta_arousal", nbins=20, title="Distribuce Δ arousal (pro srovnání)")
fig_hist_ar.add_vline(x=user_ar, line_dash="dash", line_color="red", annotation_text="Tvá hodnota")

# Scatter (bubliny)
fig_scatter = px.scatter(
    sub, x="delta_arousal", y="delta_valence",
    size="First reaction time",
    hover_data={"Term":True,"delta_arousal":":.2f","delta_valence":":.2f","First reaction time":":.2f"},
    labels={"delta_arousal":"Δ arousal (Z)","delta_valence":"Δ valence (X)","First reaction time":"Reakční doba (s)"},
    title="Tvoje slova: Δ arousal (Z) × Δ valence (X) – velikost = reakční doba"
)

# Kontury
fig_contour = px.density_contour(
    deltas_all, x="delta_arousal", y="delta_valence",
    labels={"delta_arousal":"Δ arousal (Z)","delta_valence":"Δ valence (X)"},
    title="Emoční mapa skupiny (pro srovnání) + tvá slova"
)
fig_contour.update_traces(contours_coloring="fill", contours_showlabels=True)
fig_contour.add_scatter(x=sub["delta_arousal"], y=sub["delta_valence"], mode="markers+text",
                        text=sub["Term"], textposition="top center",
                        marker=dict(color="red", size=7, opacity=0.85), name="Tvá slova")

# Line chart (pokud je Order)
fig_line = None
if "Order" in sub.columns:
    srt = sub.sort_values("Order")
    fig_line = px.line(srt, x="Order", y="First reaction time", markers=True,
                    labels={"Order":"Pořadí","First reaction time":"Reakční doba (s)"},
                    title="Jak se měnila tvoje reakční doba během úkolu")

# -----------------------------
# 6) Insight engine (osobní texty)
# -----------------------------
insights = []
# Valence
if user_val > overall["delta_valence"] + 0.1:
    insights.append("Celkově vnímáš slova **pozitivněji** než většina účastníků.")
elif user_val < overall["delta_valence"] - 0.1:
    insights.append("Celkově vnímáš slova **negativněji** než většina účastníků.")
else:
    insights.append("Tvoje vnímání pozitivnosti je **podobné** většině účastníků.")

# Arousal
if user_ar > overall["delta_arousal"] + 0.1:
    insights.append("Slova v tobě vyvolávala **silnější emoční odezvu** než u ostatních.")
elif user_ar < overall["delta_arousal"] - 0.1:
    insights.append("Reaguješ spíše **klidněji** (mírnější emoční intenzita) než většina.")
else:
    insights.append("Intenzita prožívání je **blízko průměru** skupiny.")

# Reakční doba
overall_rt = overall["First reaction time"]
if pd.notna(user_rt) and pd.notna(overall_rt):
    if user_rt < overall_rt - 0.2:
        insights.append("Rozhoduješ se **rychleji** než je průměr skupiny.")
    elif user_rt > overall_rt + 0.2:
        insights.append("Rozhoduješ se **pomaleji** než je průměr skupiny.")
    else:
        insights.append("Tvoje reakční doba je **srovnatelná** se skupinou.")

# Dominance – popisně vůči skupině
if user_dom > overall["Pos Y"] + 0.1:
    insights.append("V průměru se cítíš **více dominantně** (silnější pocit kontroly) než většina.")
elif user_dom < overall["Pos Y"] - 0.1:
    insights.append("V průměru se cítíš **méně dominantně** než většina.")
else:
    insights.append("Pocit kontroly (dominance) je **blízko průměru**.")

# TOP 3 nejodlišnější slova
sub["abs_dev"] = sub["delta_valence"].abs() + sub["delta_arousal"].abs()
top3 = sub.sort_values("abs_dev", ascending=False).head(3)[["Term","delta_valence","delta_arousal"]]
if not top3.empty:
    msg = "Nejosobitější slova: " + "; ".join(
        f"{r.Term} (ΔV {r.delta_valence:+.2f}, ΔA {r.delta_arousal:+.2f})"
        for r in top3.itertuples()
    )
    insights.append(msg)

insight_text = " • " + "\n • ".join(insights)

# -----------------------------
# 7) Připrav PDF a tlačítko ke stažení (nahoře)
# -----------------------------
figs = {
    "radar":    fig_radar,
    "hist_val": fig_hist_val,
    "hist_ar":  fig_hist_ar,
    "scatter":  fig_scatter,
    "contour":  fig_contour
}
if fig_line is not None:
    figs["line_rt"] = fig_line

summary_text = (
    "Tento report shrnuje tvé výsledky v úkolu s prostorem emocí.\n"
    "- Osa X = Valence (negativní ↔ pozitivní)\n"
    "- Osa Z = Arousal (nízký ↔ vysoký)\n"
    "- Osa Y = Dominance (nízká ↔ vysoká kontrola)\n\n"
    "Δ metriky ukazují, o kolik jsi posunul(a) slova vůči jejich výchozím štítkům."
)
pdf_bytes = build_pdf_report(selected_id, summary_text, insight_text, figs)

st.download_button("📄 Stáhnout osobní PDF report", data=pdf_bytes,
                file_name=f"{selected_id}_emocni_profil.pdf", mime="application/pdf")

st.divider()

# -----------------------------
# 8) Vizualizace v appce + mini-legendy
# -----------------------------
st.subheader("Srovnání s průměrem skupiny (radar)")
st.caption("**Co to je:** Porovnání tvých průměrných hodnot s průměrem skupiny.  \n**Jak číst:** Čím blíž se tvůj tvar kryje s průměrem, tím podobnější jsi skupině v dané metrice.")
st.plotly_chart(fig_radar, use_container_width=True)

left,right = st.columns(2)
with left:
    st.subheader("Tvá pozice v distribuci Δ valence")
    st.caption("**Co to je:** Rozložení všech hodnot pro srovnání.  \n**Jak číst:** Červená čára = tvá průměrná hodnota.")
    st.plotly_chart(fig_hist_val, use_container_width=True)
with right:
    st.subheader("Tvá pozice v distribuci Δ arousal")
    st.caption("**Co to je:** Rozložení všech hodnot pro srovnání.  \n**Jak číst:** Červená čára = tvá průměrná hodnota.")
    st.plotly_chart(fig_hist_ar, use_container_width=True)

st.subheader("Tvá slova v emočním prostoru")
st.caption("**Co to je:** Každý bod = tvé slovo; větší bublina = delší reakce.  \n**Jak číst:** Najetím myší uvidíš přesné hodnoty a název slova.")
st.plotly_chart(fig_scatter, use_container_width=True)

st.subheader("Tvá slova na mapě skupiny")
st.caption("**Co to je:** Konturová mapa celé skupiny; červené body = tvá slova.  \n**Jak číst:** Hustší oblasti = častější umístění slov ve skupině.")
st.plotly_chart(fig_contour, use_container_width=True)

if fig_line is not None:
    st.subheader("Vývoj reakční doby")
    st.caption("**Co to je:** Jak se měnila tvoje rychlost během úkolu.  \n**Jak číst:** Trend dolů = zrychlování; trend nahoru = zpomalování.")
    st.plotly_chart(fig_line, use_container_width=True)

# -----------------------------
# 9) Osobní insighty a druhé PDF tlačítko
# -----------------------------
st.divider()
st.subheader("🔍 Tvé osobní insighty")
st.markdown(insight_text)

st.download_button("📄 Stáhnout PDF report (znovu)", data=pdf_bytes,
                file_name=f"{selected_id}_emocni_profil.pdf", mime="application/pdf")

st.divider()
st.markdown("---")
st.markdown("**🔒 Ochrana soukromí:** Tento report je určen pouze pro tebe. Obsahuje pouze tvá data a anonymizované skupinové průměry pro srovnání.")
st.markdown("**❓ Máš dotazy?** Kontaktuj organizátory studie.")
