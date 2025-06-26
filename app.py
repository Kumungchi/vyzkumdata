import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils import load_data, compute_deltas

st.set_page_config(page_title="Hodnocení slov v 3D", layout="wide")

# 1) Načti ID z URL pomocí experimental_get_query_params
params = st.experimental_get_query_params()
selected_id = params.get("ID", [None])[0]

# 2) Načtení dat
vybrana, hand, codebook = load_data()
deltas_all              = compute_deltas(hand, vybrana)
overall                 = deltas_all[["delta_arousal","delta_valence","First reaction time"]].mean()

# 3) Validace
if selected_id not in hand["ID"].unique():
    st.error(f"❌ Neplatné nebo chybějící ID: {selected_id!r} – "
            "ujisti se, že máš v URL `?ID=PCZ003` apod.")
    st.stop()

# 5) Výpočty pro vybraného účastníka  
subset   = hand[hand["ID"] == selected_id]
deltas   = compute_deltas(subset, vybrana)
user_val = deltas["delta_valence"].mean()
user_ar  = deltas["delta_arousal"].mean()
user_rt  = deltas["First reaction time"].mean()
val_diff = user_val - overall["delta_valence"]
ar_diff  = user_ar  - overall["delta_arousal"]

# --- Kvantitativní rozbor ---
st.title(f"Kvantitativní rozbor — {selected_id}")

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

# Metričky  
c1, c2, c3 = st.columns(3)
c1.metric("Δ valence", f"{user_val:.2f}", f"{val_diff:+.2f} vs. průměr")
c2.metric("Δ arousal", f"{user_ar:.2f}", f"{ar_diff:+.2f} vs. průměr")
c3.metric("Reakční doba (s)", f"{user_rt:.2f}", f"{user_rt - overall['First reaction time']:+.2f} vs. průměr")

# Histogram Δ valence  
fig_hv = px.histogram(
    deltas_all, x="delta_valence", nbins=20,
    title="Distribuce Δ valence (všichni)", template="plotly_dark"
)
fig_hv.add_vline(x=user_val, line_dash="dash", line_color="red",
                annotation_text="Tvé Δ valence", annotation_position="top right")
st.plotly_chart(fig_hv, use_container_width=True)

# Histogram Δ arousal  
fig_ha = px.histogram(
    deltas_all, x="delta_arousal", nbins=20,
    title="Distribuce Δ arousal (všichni)", template="plotly_dark"
)
fig_ha.add_vline(x=user_ar, line_dash="dash", line_color="red",
                annotation_text="Tvé Δ arousal", annotation_position="top right")
st.plotly_chart(fig_ha, use_container_width=True)

# Boxplot Δ valence  
fig_box_v = px.box(
    deltas_all, y="delta_valence", points="all",
    title="Boxplot Δ valence (všichni)", template="plotly_dark"
)
fig_box_v.add_scatter(x=[0], y=[user_val], mode="markers",
                    marker=dict(color="red", size=12), name="Ty")
st.plotly_chart(fig_box_v, use_container_width=True)

# Boxplot Δ arousal  
fig_box_a = px.box(
    deltas_all, y="delta_arousal", points="all",
    title="Boxplot Δ arousal (všichni)", template="plotly_dark"
)
fig_box_a.add_scatter(x=[0], y=[user_ar], mode="markers",
                    marker=dict(color="red", size=12), name="Ty")
st.plotly_chart(fig_box_a, use_container_width=True)

# Radar chart  

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
# Sized scatter  
fig_sz = px.scatter(
    deltas, x="delta_arousal", y="delta_valence",
    size="First reaction time", hover_data=["Term"],
    title="Δ valence vs. Δ arousal (velikost = reakční doba)",
    template="plotly_dark"
)
st.plotly_chart(fig_sz, use_container_width=True)

# Konturová hustota + tvé body s názvy slov  
fig_cont = px.density_contour(
    deltas_all, x="delta_arousal", y="delta_valence",
    title="Konturová hustota Δ hodnot + tvé body", template="plotly_dark"
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

# Vysvětlivky  
st.markdown("""
**Interpretace konturové hustoty + tvých bodů**  
- **Barevné oblasti**: frekvence skupinových Δ hodnot.  
- **Světlejší (žluté/oranžové) zóny** značí největší četnost – většina účastníků.  
- **Tmavé (modré) zóny** ukazují řídké výskyty.  
- **Červené body + štítky**: tvoje Δ hodnoty a názvy slov.  
- Uvnitř světlejších oblastí = blíže průměru skupiny.  
- Mimo zóny = slova, u kterých ses nejvíc lišil(a).
""")
