import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import CountVectorizer
import numpy as np
import re

from utils import load_data, compute_deltas

# 1) Nastavení tmavého motivu
st.set_page_config(page_title="Hodnocení slov v 3D", layout="wide")

# 2) Načtení dat
vybrana, hand, codebook = load_data()
deltas_all               = compute_deltas(hand, vybrana)
overall                  = deltas_all[["delta_arousal","delta_valence","First reaction time"]].mean()

# 3) Sidebar – výběr účastníka
st.sidebar.title("Výběr účastníka")
selected_id = st.sidebar.selectbox("Vyber ID", sorted(hand["ID"].unique()))

# 4) Výpočty pro uživatele
subset   = hand[hand["ID"] == selected_id]
deltas   = compute_deltas(subset, vybrana)
user_val = deltas["delta_valence"].mean()
user_ar  = deltas["delta_arousal"].mean()
user_rt  = deltas["First reaction time"].mean()
val_diff = user_val - overall["delta_valence"]
ar_diff  = user_ar  - overall["delta_arousal"]

# --- Kvantitativní rozbor ---
st.title("Kvantitativní rozbor")

st.markdown("""
**Interpretace metrik**  
- **Δ valence**: rozdíl mezi tím, jak jsi slova posunul(a) v ose kladnost/negativita oproti výchozí valencí.  
  (kladnější = pozitivnější pocit)  
- **Δ arousal**: rozdíl mezi tím, jak jsi slova posunul(a) v ose intenzita emocí oproti výchozímu arousalu.  
  (vyšší = silnější reakce)  
- **Reakční doba**: průměrná doba, za kterou jsi reagoval(a) na slova.  
- **Průměrné hodnoty**: průměrné hodnoty pro všechny účastníky.  
- **Znamení Δ**: jak se tvoje skóre liší od průměru skupiny.
""")

# 5) Metričky
c1, c2, c3 = st.columns(3)
c1.metric("Δ valence", f"{user_val:.2f}", f"{val_diff:+.2f} vs. průměr")
c2.metric("Δ arousal", f"{user_ar:.2f}", f"{ar_diff:+.2f} vs. průměr")
c3.metric("Reakční doba (s)", f"{user_rt:.2f}", f"{user_rt - overall['First reaction time']:+.2f} vs. průměr")

# 6) Histogram Δ valence
fig_hv = px.histogram(
    deltas_all, x="delta_valence", nbins=20,
    title="Distribuce Δ valence (všichni)", template="plotly_dark"
)
fig_hv.add_vline(x=user_val, line_dash="dash", line_color="red",
                 annotation_text="Tvé Δ valence", annotation_position="top right")
fig_hv.update_layout(xaxis_title="Δ valence", yaxis_title="Počet")
st.plotly_chart(fig_hv, use_container_width=True)
st.markdown(f"""
**Příklad interpretace:**  
Tvoje průměrné Δ valence je **{user_val:.2f}**, což znamená, že jsi slova posunul(a) o {user_val:.2f} jednotky směrem k {"pozitivnějšímu" if user_val>0 else "negativnějšímu"} vnímání.  
V porovnání s průměrem (**{overall['delta_valence']:.2f}**) jsi {"o něco pozitivnější" if val_diff>0 else "o něco méně pozitivní"}.
""")

# 7) Histogram Δ arousal
fig_ha = px.histogram(
    deltas_all, x="delta_arousal", nbins=20,
    title="Distribuce Δ arousal (všichni)", template="plotly_dark"
)
fig_ha.add_vline(x=user_ar, line_dash="dash", line_color="red",
                 annotation_text="Tvé Δ arousal", annotation_position="top right")
fig_ha.update_layout(xaxis_title="Δ arousal", yaxis_title="Počet")
st.plotly_chart(fig_ha, use_container_width=True)
st.markdown(f"""
**Příklad interpretace:**  
Tvoje průměrné Δ arousal je **{user_ar:.2f}**, tedy slova jsi v průměru označil(a) za {"více stimulující" if user_ar>0 else "klidnější"}.  
Ve srovnání s průměrem (**{overall['delta_arousal']:.2f}**) jsi {"o něco více vzrušený/á" if ar_diff>0 else "klidnější"} než ostatní.
""")

# 8) Boxplot Δ valence
fig_box_v = px.box(
    deltas_all, y="delta_valence", points="all",
    title="Boxplot Δ valence (všichni)", template="plotly_dark"
)
fig_box_v.add_scatter(x=[0], y=[user_val], mode="markers",
                      marker=dict(color="red", size=12), name="Ty")
fig_box_v.update_layout(yaxis_title="Δ valence")
st.plotly_chart(fig_box_v, use_container_width=True)
st.markdown("""
**Jak číst boxplot Δ valence?**  
- Krabice = 25.–75. percentil, čára = medián.  
- „Fousy“ = 1.5×IQR.  
- Modré body = ostatní účastníci.  
- Červený bod = tvoje průměrné Δ valence.
""")

# 9) Boxplot Δ arousal
fig_box_a = px.box(
    deltas_all, y="delta_arousal", points="all",
    title="Boxplot Δ arousal (všichni)", template="plotly_dark"
)
fig_box_a.add_scatter(x=[0], y=[user_ar], mode="markers",
                      marker=dict(color="red", size=12), name="Ty")
fig_box_a.update_layout(yaxis_title="Δ arousal")
st.plotly_chart(fig_box_a, use_container_width=True)
st.markdown("""
**Jak číst boxplot Δ arousal?**  
- Krabice = 25.–75. percentil, čára = medián.  
- „Fousy“ = 1.5×IQR.  
- Modré body = ostatní účastníci.  
- Červený bod = tvoje průměrné Δ arousal.
""")

# 10) Radar chart
categories = ["Δ valence","Δ arousal","Reakční doba"]
fig_radar = go.Figure()
fig_radar.add_trace(go.Scatterpolar(
    r=[user_val, user_ar, user_rt], theta=categories,
    fill="toself", name="Ty"))
fig_radar.add_trace(go.Scatterpolar(
    r=[overall["delta_valence"], overall["delta_arousal"], overall["First reaction time"]],
    theta=categories, fill="toself", name="Průměr skupiny"))
fig_radar.update_layout(
    title="Srovnání Ty vs. průměr skupiny",
    polar=dict(radialaxis=dict(visible=True)),
    template="plotly_dark"
)
st.plotly_chart(fig_radar, use_container_width=True)
st.markdown("""
**Příklad interpretace radarového grafu:**  
Vidíš svou červenou plochu proti modré ploše průměru.  
Např. osa „Δ valence“ ukazuje, zda jsi byl(a) pozitivnější/negativnější než průměr.
""")

# 11) Sized scatter
fig_sz = px.scatter(
    deltas, x="delta_arousal", y="delta_valence",
    size="First reaction time", hover_data=["Term"],
    title="Δ valence vs. Δ arousal (velikost = reakční doba)",
    template="plotly_dark"
)
fig_sz.update_layout(xaxis_title="Δ arousal", yaxis_title="Δ valence")
st.plotly_chart(fig_sz, use_container_width=True)
st.markdown("""
**Příklad interpretace:**  
Větší body znamenají, že jsi na slovo reagoval(a) pomaleji.  
Např. slovo „XYZ“ bylo umístěno s Δ valence = {0:.2f} a arousal = {1:.2f}, ale trvalo ti {2:.2f}s jej zpracovat.
""".format(
    deltas.loc[deltas["Term"].idxmax(), "delta_valence"],
    deltas.loc[deltas["Term"].idxmax(), "delta_arousal"],
    deltas.loc[deltas["Term"].idxmax(), "First reaction time"]
))

# 12) Density contour + tvé body s názvy slov
fig_cont = px.density_contour(
    deltas_all,
    x="delta_arousal",
    y="delta_valence",
    title="Konturová hustota Δ hodnot + tvé body",
    template="plotly_dark"
)
fig_cont.update_traces(contours_coloring="fill", contours_showlabels=True)
fig_cont.add_scatter(
    x=deltas["delta_arousal"],
    y=deltas["delta_valence"],
    mode="markers+text",
    text=deltas["Term"],
    textposition="top center",
    marker=dict(color="red", size=6, opacity=0.8),
    name="Tvé Δ hodnoty"
)
fig_cont.update_layout(xaxis_title="Δ arousal", yaxis_title="Δ valence")
st.plotly_chart(fig_cont, use_container_width=True)

# Vysvětlivky k interpretaci posledního grafu
st.markdown("""
**Interpretace konturové hustoty + tvých bodů**  
- **Barevné oblasti**: vykreslují, jak často celá skupina umístila slova do daných kombinací Δ arousal (osa X) a Δ valence (osa Y).  
- **Světlejší (žluté/oranžové) zóny** značí největší četnost – většina účastníků hodnotila slova v těchto oblastech.  
- **Tmavé (modré) zóny** ukazují, že tam byla malá nebo žádná koncentrace slov.  
- **Červené body a štítky** = tvoje individuální Δ hodnoty spolu s názvy slov.  
- Pokud se nacházejí uvnitř světlejších oblastí, tvé hodnocení je blíže průměru skupiny.  
- Body a štítky mimo tyto zóny reprezentují slova, u kterých ses nejvíc lišil(a) od ostatních.
""")
