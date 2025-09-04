# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import time
import traceback

from utils import standardize_hand_columns, compute_deltas
from pdf_utils import build_pdf_report
from error_handler import (
    safe_read_csv, validate_data_structure, safe_numeric_conversion,
    validate_user_id, handle_exception, log_user_activity, logger
)
from thematic_analysis import (
    load_thematic_data, analyze_user_strategy, 
    get_matching_quotes, generate_qualitative_insights
)

st.set_page_config(page_title="Osobní emoční profil", layout="wide", page_icon="📊")

DATA_DIR = Path("data")

# Úvodní text o výzkumu
RESEARCH_INTRO = """
## 🔬 O čem byl výzkum

Účastnili jste se studie zaměřené na **prostorové vnímání emocí**. Hodnotili jste 30 přídavných jmen, která se liší v emoční intenzitě a náladě, kterou mohou vyvolávat. 

**Váš úkol bylo:** Umisťovat slova do 3D prostoru podle toho, jak na vás působí. Neexistovala správná nebo špatná odpověď – zajímal nás pouze váš vnitřní dojem.

**Na co jsme se zaměřili:**
- **Valence** - jestli slovo působí příjemně nebo nepříjemně
- **Arousal** - jestli v nás vyvolává silnou nebo slabou reakci  
- **Dominance** - jak moc se při slově cítíme v kontrole

**Proč 3D prostor?** Používali jsme formu „tělesného" nebo prostorového hodnocení, což souvisí s teorií **embodiment** – naše tělo a pohyb mají vliv na to, jak myslíme a cítíme. Cílem bylo zjistit, zda takto hodnocená slova odpovídají našim vnitřním dojmům lépe než klasické škály.
"""

HELP_TEXT_INTRO = """
**Jak číst prostor emocí:**
- **Osa X = Valence** (negativní ↔ pozitivní) - *jak příjemné/nepříjemné slovo působí*
- **Osa Z = Arousal** (nízký ↔ vysoký) - *jak silnou emoční reakci vyvolává*
- **Osa Y = Dominance** (nízká ↔ vysoká kontrola) - *jak moc se při slově cítíte v kontrole*

**Jak číst Δ (delta) hodnoty:**
- **Δ valence** = o kolik jste posunuli slovo v příjemnosti oproti očekávané hodnotě
- **Δ arousal** = o kolik jste posunuli slovo v intenzitě oproti očekávané hodnotě  
- **Reakční doba** = průměrný čas vašeho rozhodnutí (kratší = rychlejší intuice)
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
    
    # Načtení a zpracování dat
    vybrana, hand, users = load_and_process_data()

    # -----------------------------
    # Získání ID z URL (povinné)
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

    # Validace uživatelského ID
    available_ids = sorted(deltas_all["ID"].dropna().astype(str).unique())
    if not validate_user_id(selected_id, available_ids):
        st.stop()

    # Log aktivity uživatele
    log_user_activity(selected_id, "page_access", f"Přístup k osobnímu reportu")

    sub = deltas_all[deltas_all["ID"].astype(str) == str(selected_id)].copy()
    if sub.empty:
        logger.error(f"Prázdná data pro ID {selected_id}")
        st.error(f"🚫 **Pro ID `{selected_id}` nebyla nalezena žádná data.**")
        st.stop()

    # Skupinové průměry
    overall = deltas_all[["delta_valence","delta_arousal","First reaction time","Pos Y"]].mean(numeric_only=True)

    # Uživatelské průměry
    user_val = sub["delta_valence"].mean()
    user_ar  = sub["delta_arousal"].mean()
    user_rt  = sub["First reaction time"].mean()
    user_dom = sub["Pos Y"].mean()
    words_n  = sub["Term"].nunique()

    # Log statistik
    log_user_activity(selected_id, "stats_calculated", f"Words: {words_n}, Avg RT: {user_rt:.2f}")

    # -----------------------------
    # Úvod + metriky + PDF
    # -----------------------------
    st.title(f"🎯 Tvůj osobní report — {selected_id}")
    st.markdown("**Děkujeme za účast ve studii!** Níže najdeš svůj osobní přehled výsledků.")
    
    # Přidání úvodního textu o výzkumu
    with st.expander("🔬 **Připomenutí: O čem byl výzkum**", expanded=False):
        st.markdown(RESEARCH_INTRO)
    
    st.info("💡 **Tip:** Tento report si můžeš stáhnout jako PDF pomocí tlačítka níže.")
    st.markdown(HELP_TEXT_INTRO)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Hodnocených slov", f"{words_n}")
    c2.metric("Δ valence (X)", f"{user_val:.2f}", f"{user_val - overall['delta_valence']:+.2f} vs. průměr")
    c3.metric("Δ arousal (Z)", f"{user_ar:.2f}",  f"{user_ar - overall['delta_arousal']:+.2f} vs. průměr")
    c4.metric("Dominance (Y)", f"{user_dom:.2f}", f"{user_dom - overall['Pos Y']:+.2f} vs. průměr")

    # Grafy – tvorba s error handlingem
    # -----------------------------
    try:
        # Kontrola dat před vytvořením grafů
        if deltas_all.empty or sub.empty:
            st.error("🚫 **Chyba:** Prázdná data pro vizualizaci.")
            st.info(f"Debug info: deltas_all má {len(deltas_all)} řádků, sub má {len(sub)} řádků")
            st.stop()
        
        # Dodatečná kontrola numerických sloupců
        required_numeric_cols = ["delta_valence", "delta_arousal", "First reaction time"]
        missing_cols = [col for col in required_numeric_cols if col not in sub.columns]
        if missing_cols:
            st.error(f"🚫 **Chyba:** Chybí sloupce v datech: {missing_cols}")
            st.info(f"Dostupné sloupce: {list(sub.columns)}")
            st.stop()
            
        # Kontrola, zda máme alespoň nějaká numerická data
        if sub[required_numeric_cols].isna().all().all():
            st.error("🚫 **Chyba:** Všechna numerická data jsou prázdná (NaN)")
            st.stop()
            
        # Radar chart - elegantní moderní gradient design
        radar_categories = ["Δ valence (X)","Δ arousal (Z)","Reakční doba"]
        fig_radar = go.Figure()
        
        fig_radar.add_trace(go.Scatterpolar(
            r=[user_val,user_ar,user_rt], 
            theta=radar_categories, 
            fill='toself', 
            name='<b>Tvůj profil</b>',
            line=dict(color='#F59E0B', width=3, smoothing=1.3),  # Amber s vyhlazením
            fillcolor='rgba(245, 158, 11, 0.2)',
            marker=dict(size=8, color='#D97706')
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[overall["delta_valence"],overall["delta_arousal"],overall["First reaction time"]],
            theta=radar_categories, 
            fill='toself', 
            name='<b>Průměr skupiny</b>',
            line=dict(color='#6366F1', width=2.5, dash='dot', smoothing=1.3),  # Indigo s tečkami
            fillcolor='rgba(99, 102, 241, 0.15)',
            marker=dict(size=6, color='#4F46E5')
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    gridcolor='rgba(156, 163, 175, 0.4)',
                    linecolor='rgba(156, 163, 175, 0.6)',
                    tickfont=dict(size=10, color='#6B7280')
                ),
                angularaxis=dict(
                    gridcolor='rgba(156, 163, 175, 0.4)',
                    linecolor='rgba(156, 163, 175, 0.6)',
                    tickfont=dict(size=12, color='#374151', family="Inter, system-ui, sans-serif")
                ),
                bgcolor='rgba(249, 250, 251, 0.5)'
            ), 
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.1,
                xanchor="center",
                x=0.5,
                font=dict(size=12, color='#374151', family="Inter, system-ui, sans-serif"),
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="rgba(229, 231, 235, 1)",
                borderwidth=1
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#111827', size=12, family="Inter, system-ui, sans-serif"),
            title=dict(
                text="<b>Tvůj emoční radar</b>",
                font=dict(size=18, color='#111827', family="Inter, system-ui, sans-serif"),
                x=0.5,
                pad=dict(t=20, b=20)
            ),
            margin=dict(l=60, r=60, t=80, b=80),
            height=500
        )

        # Boxploty - moderní design s gradientem
        import numpy as np
        
        # Boxplot pro valenci - moderní design s gradientním pozadím
        fig_hist_val = go.Figure()
        
        # Přidání boxplotu populace - elegantní moderní styl
        fig_hist_val.add_trace(go.Box(
            y=deltas_all["delta_valence"],
            name="Všichni účastníci",
            boxpoints=False,
            fillcolor='rgba(99, 102, 241, 0.15)',  # Indigo s transparentností
            line=dict(color='#6366F1', width=2.5),
            marker=dict(color='#6366F1', size=6),
            whiskerwidth=0.8,
            boxmean=True  # Zobrazí průměr
        ))
        
        # Přidání tvé hodnoty jako stylový bod
        fig_hist_val.add_trace(go.Scatter(
            x=["Všichni účastníci"],
            y=[user_val],
            mode="markers",
            name="Tvá hodnota",
            marker=dict(
                color='#F59E0B',  # Moderní amber
                size=16,
                symbol="diamond",
                line=dict(color='#D97706', width=2.5),
                opacity=0.9
            )
        ))
        
        # Výpočet percentilu pro interpretaci
        val_percentile = (deltas_all["delta_valence"] < user_val).mean() * 100
        val_interpretation = f"Tvoje hodnocení bylo pozitivnější než u {val_percentile:.0f}% účastníků" if user_val > 0 else f"Tvoje hodnocení bylo negativnější než u {100-val_percentile:.0f}% účastníků"
        
        fig_hist_val.update_layout(
            title=dict(
                text=f"<b>Jak vnímáš příjemnost slov oproti ostatním</b><br><span style='color:#6B7280; font-size:13px'>{val_interpretation}</span>",
                font=dict(size=16, color='#111827', family="Inter, system-ui, sans-serif"),
                x=0.5,
                pad=dict(t=20, b=20)
            ),
            yaxis_title="<b>Δ valence</b> (negativnější ← 0 → pozitivnější)",
            yaxis=dict(
                title_font=dict(size=13, color='#374151', family="Inter, system-ui, sans-serif"),
                tickfont=dict(size=11, color='#6B7280'),
                gridcolor='rgba(156, 163, 175, 0.3)',
                zerolinecolor='#9CA3AF',
                zerolinewidth=1.5
            ),
            xaxis_title="",
            xaxis=dict(
                tickfont=dict(size=12, color='#374151', family="Inter, system-ui, sans-serif"),
                showgrid=False
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=11, color='#374151')
            ),
            plot_bgcolor='rgba(249, 250, 251, 1)',
            paper_bgcolor='white',
            font=dict(color='#111827', family="Inter, system-ui, sans-serif"),
            margin=dict(l=60, r=20, t=120, b=40),
            height=450,
            annotations=[
                dict(
                    x=0, y=user_val,
                    text=f"<b>Ty: {user_val:.2f}</b>",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#F59E0B",
                    arrowwidth=2,
                    ax=70, ay=-10,
                    font=dict(color='#D97706', size=12, family="Inter, system-ui, sans-serif"),
                    bgcolor="rgba(255, 255, 255, 0.9)",
                    bordercolor="#F59E0B",
                    borderwidth=1
                )
            ]
        )

        # Boxplot pro arousal - elegantní fialový design 
        fig_hist_ar = go.Figure()
        
        # Přidání boxplotu populace - moderní fialový styl
        fig_hist_ar.add_trace(go.Box(
            y=deltas_all["delta_arousal"],
            name="Všichni účastníci",
            boxpoints=False,
            fillcolor='rgba(139, 92, 246, 0.15)',  # Violet s transparentností
            line=dict(color='#8B5CF6', width=2.5),
            marker=dict(color='#8B5CF6', size=6),
            whiskerwidth=0.8,
            boxmean=True  # Zobrazí průměr
        ))
        
        # Přidání tvé hodnoty - sladění s amber barvou
        fig_hist_ar.add_trace(go.Scatter(
            x=["Všichni účastníci"],
            y=[user_ar],
            mode="markers",
            name="Tvá hodnota",
            marker=dict(
                color='#F59E0B',  # Stejná amber jako u valence
                size=16,
                symbol="diamond",
                line=dict(color='#D97706', width=2.5),
                opacity=0.9
            )
        ))
        
        # Výpočet percentilu pro interpretaci
        ar_percentile = (deltas_all["delta_arousal"] < user_ar).mean() * 100
        ar_interpretation = f"Tvé reakce byly intenzivnější než u {ar_percentile:.0f}% účastníků" if user_ar > 0 else f"Tvé reakce byly klidnější než u {100-ar_percentile:.0f}% účastníků"
        
        fig_hist_ar.update_layout(
            title=dict(
                text=f"<b>Jak intenzivně reaguješ na slova oproti ostatním</b><br><span style='color:#6B7280; font-size:13px'>{ar_interpretation}</span>",
                font=dict(size=16, color='#111827', family="Inter, system-ui, sans-serif"),
                x=0.5,
                pad=dict(t=20, b=20)
            ),
            yaxis_title="<b>Δ arousal</b> (klidnější ← 0 → intenzivnější)",
            yaxis=dict(
                title_font=dict(size=13, color='#374151', family="Inter, system-ui, sans-serif"),
                tickfont=dict(size=11, color='#6B7280'),
                gridcolor='rgba(156, 163, 175, 0.3)',
                zerolinecolor='#9CA3AF',
                zerolinewidth=1.5
            ),
            xaxis_title="",
            xaxis=dict(
                tickfont=dict(size=12, color='#374151', family="Inter, system-ui, sans-serif"),
                showgrid=False
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                font=dict(size=11, color='#374151')
            ),
            plot_bgcolor='rgba(249, 250, 251, 1)',
            paper_bgcolor='white',
            font=dict(color='#111827', family="Inter, system-ui, sans-serif"),
            margin=dict(l=60, r=20, t=120, b=40),
            height=450,
            annotations=[
                dict(
                    x=0, y=user_ar,
                    text=f"<b>Ty: {user_ar:.2f}</b>",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#F59E0B",
                    arrowwidth=2,
                    ax=70, ay=-10,
                    font=dict(color='#D97706', size=12, family="Inter, system-ui, sans-serif"),
                    bgcolor="rgba(255, 255, 255, 0.9)",
                    bordercolor="#F59E0B",
                    borderwidth=1
                )
            ]
        )

        # Scatter (bubliny) - elegantní moderní design
        fig_scatter = px.scatter(
            sub, x="delta_arousal", y="delta_valence",
            size="First reaction time",
            hover_data={"Term":True,"delta_arousal":":.2f","delta_valence":":.2f","First reaction time":":.2f"},
            labels={"delta_arousal":"Δ arousal (intenzita)","delta_valence":"Δ valence (příjemnost)","First reaction time":"Reakční doba (s)"},
            title="<b>Tvá slova v emočním prostoru</b>",
            color_discrete_sequence=["#10B981"]  # Moderní emerald zelená
        )
        
        # Přidání gradientního pozadí a vylepšení stylu
        fig_scatter.update_traces(
            marker=dict(
                line=dict(width=1.5, color='white'),
                opacity=0.8,
                sizemin=8,
                sizeref=0.3
            ),
            hovertemplate="<b>%{customdata[0]}</b><br>" +
                        "Δ arousal: %{x:.2f}<br>" +
                        "Δ valence: %{y:.2f}<br>" +
                        "Reakční doba: %{customdata[3]:.2f}s<extra></extra>"
        )
        
        fig_scatter.update_layout(
            title=dict(
                font=dict(size=18, color='#111827', family="Inter, system-ui, sans-serif"),
                x=0.5,
                pad=dict(t=20, b=20)
            ),
            xaxis_title="<b>Δ arousal</b> (klidnější ← → intenzivnější)",
            yaxis_title="<b>Δ valence</b> (negativnější ← → pozitivnější)",
            xaxis=dict(
                title_font=dict(size=13, color='#374151', family="Inter, system-ui, sans-serif"),
                tickfont=dict(size=11, color='#6B7280'),
                gridcolor='rgba(156, 163, 175, 0.3)',
                zerolinecolor='#9CA3AF',
                zerolinewidth=2,
                showline=True,
                linecolor='#E5E7EB'
            ),
            yaxis=dict(
                title_font=dict(size=13, color='#374151', family="Inter, system-ui, sans-serif"),
                tickfont=dict(size=11, color='#6B7280'),
                gridcolor='rgba(156, 163, 175, 0.3)',
                zerolinecolor='#9CA3AF',
                zerolinewidth=2,
                showline=True,
                linecolor='#E5E7EB'
            ),
            plot_bgcolor='rgba(249, 250, 251, 1)',
            paper_bgcolor='white',
            font=dict(color='#111827', family="Inter, system-ui, sans-serif"),
            margin=dict(l=60, r=40, t=80, b=60),
            height=500,
            # Přidání subtilního gradientu do pozadí
            shapes=[
                dict(
                    type="rect",
                    xref="paper", yref="paper",
                    x0=0, y0=0, x1=1, y1=1,
                    fillcolor="rgba(249, 250, 251, 0.8)",
                    layer="below",
                    line_width=0,
                )
            ]
        )

        # Kontury - elegantní heatmapa s moderním designem
        fig_contour = px.density_contour(
            deltas_all, x="delta_arousal", y="delta_valence",
            labels={"delta_arousal":"Δ arousal (intenzita)","delta_valence":"Δ valence (příjemnost)"},
            title="<b>Emoční mapa skupiny + tvá slova</b>",
        )
        
        # Moderní color scheme - použijeme elegantní blue-purple gradient
        fig_contour.update_traces(
            contours_coloring="fill", 
            contours_showlabels=False,  # Skryjeme labely pro čistší vzhled
            colorscale=[
                [0.0, "rgba(99, 102, 241, 0.1)"],      # Velmi světlý indigo
                [0.2, "rgba(99, 102, 241, 0.3)"],      # Světlý indigo
                [0.4, "rgba(139, 92, 246, 0.5)"],      # Středně fialová
                [0.6, "rgba(168, 85, 247, 0.7)"],      # Tmavší fialová
                [0.8, "rgba(147, 51, 234, 0.8)"],      # Fialová
                [1.0, "rgba(126, 34, 206, 0.9)"]       # Nejintenzivnější fialová
            ],
            showscale=True,
            colorbar=dict(
                title=dict(
                    text="<b>Hustota účastníků</b><br><span style='font-size:11px'>nízká → vysoká</span>",
                    font=dict(color='#374151', size=12, family="Inter, system-ui, sans-serif")
                ),
                tickfont=dict(color='#6B7280', size=10),
                thickness=12,
                len=0.7,
                x=1.02
            ),
            line=dict(width=0.5, color='rgba(255, 255, 255, 0.3)')  # Jemné bílé okraje
        )
        
        fig_contour.update_layout(
            title=dict(
                font=dict(size=18, color='#111827', family="Inter, system-ui, sans-serif"),
                x=0.5,
                pad=dict(t=20, b=20)
            ),
            xaxis_title="<b>Δ arousal</b> (klidnější ← → intenzivnější)",
            yaxis_title="<b>Δ valence</b> (negativnější ← → pozitivnější)",
            xaxis=dict(
                title_font=dict(size=13, color='#374151', family="Inter, system-ui, sans-serif"),
                tickfont=dict(size=11, color='#6B7280'),
                gridcolor='rgba(156, 163, 175, 0.2)',
                zerolinecolor='#9CA3AF',
                zerolinewidth=2,
                showline=True,
                linecolor='#E5E7EB'
            ),
            yaxis=dict(
                title_font=dict(size=13, color='#374151', family="Inter, system-ui, sans-serif"),
                tickfont=dict(size=11, color='#6B7280'),
                gridcolor='rgba(156, 163, 175, 0.2)',
                zerolinecolor='#9CA3AF',
                zerolinewidth=2,
                showline=True,
                linecolor='#E5E7EB'
            ),
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(color='#111827', family="Inter, system-ui, sans-serif"),
            margin=dict(l=60, r=100, t=80, b=60),
            height=550
        )
        
        # Přidání tvých slov jako elegantní body
        fig_contour.add_scatter(
            x=sub["delta_arousal"], y=sub["delta_valence"], 
            mode="markers+text",
            text=sub["Term"], 
            textposition="top center",
            marker=dict(
                color="white",  # Bílé body pro maximální kontrast
                size=12, 
                opacity=1,
                symbol="circle",
                line=dict(color="#F59E0B", width=3)  # Amber okraj
            ), 
            name="<b>Tvá slova</b>",
            textfont=dict(
                color='#111827', 
                size=10, 
                family="Inter, system-ui, sans-serif",
                weight="bold"
            ),
            hovertemplate="<b>%{text}</b><br>" +
                        "Δ arousal: %{x:.2f}<br>" +
                        "Δ valence: %{y:.2f}<extra></extra>"
        )

        # Line chart (pokud je Order) - elegantní moderní design
        fig_line = None
        if "Order" in sub.columns:
            srt = sub.sort_values("Order")
            fig_line = px.line(srt, x="Order", y="First reaction time", markers=True,
                            labels={"Order":"Pořadí","First reaction time":"Reakční doba (s)"},
                            title="<b>Jak se měnila tvoje reakční doba během úkolu</b>",
                            color_discrete_sequence=["#10B981"])  # Elegantní emerald
            
            # Aplikace pokročilého moderního stylu
            fig_line.update_traces(
                line=dict(width=3, color="#10B981", smoothing=1.3),
                marker=dict(
                    size=8, 
                    color="#059669", 
                    line=dict(width=2, color="white"),
                    symbol="circle"
                ),
                hovertemplate="<b>Pořadí:</b> %{x}<br><b>Reakční doba:</b> %{y:.2f}s<extra></extra>"
            )
            
            fig_line.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white", 
                font=dict(family="Inter, system-ui, sans-serif", size=12, color="#111827"),
                title=dict(
                    font=dict(size=18, color="#111827", family="Inter, system-ui, sans-serif"), 
                    x=0.5,
                    pad=dict(t=20, b=20)
                ),
                xaxis=dict(
                    title="<b>Pořadí hodnocení</b>",
                    title_font=dict(size=13, color='#374151', family="Inter, system-ui, sans-serif"),
                    tickfont=dict(size=11, color='#6B7280'),
                    showgrid=True, 
                    gridcolor="rgba(156, 163, 175, 0.3)",
                    showline=True,
                    linecolor="#E5E7EB",
                    linewidth=1
                ),
                yaxis=dict(
                    title="<b>Reakční doba (sekundy)</b>",
                    title_font=dict(size=13, color='#374151', family="Inter, system-ui, sans-serif"),
                    tickfont=dict(size=11, color='#6B7280'),
                    showgrid=True, 
                    gridcolor="rgba(156, 163, 175, 0.3)",
                    showline=True,
                    linecolor="#E5E7EB",
                    linewidth=1
                ),
                hovermode="x unified",
                margin=dict(l=60, r=20, t=80, b=60),
                height=400,
                # Přidání jemného gradientního pozadí
                shapes=[
                    dict(
                        type="rect",
                        xref="paper", yref="paper",
                        x0=0, y0=0, x1=1, y1=1,
                        fillcolor="rgba(249, 250, 251, 0.5)",
                        layer="below",
                        line_width=0,
                    )
                ]
            )

        log_user_activity(selected_id, "charts_created", "Všechny grafy úspěšně vytvořeny")
        
    except Exception as e:
        logger.error(f"Chyba při vytváření grafů pro {selected_id}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        st.error("🚫 **Chyba při vytváření vizualizací**")
        st.error("Někde nastal problém při generování grafů. Zkuste:")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **🔄 Okamžitě:**
            - Obnovte stránku (F5)
            - Zkontrolujte internetové připojení
            - Zkuste jiný prohlížeč
            """)
        
        with col2:
            st.markdown("""
            **📞 Pokud problém přetrvává:**
            - Kontaktujte podporu
            - Uveďte své ID a čas chyby
            - Popište, co jste dělali před chybou
            """)
        
        if st.checkbox("🔧 Zobrazit technické detaily"):
            st.code(f"ID: {selected_id}")
            st.code(f"Chyba: {type(e).__name__}: {e}")
            st.code(f"Čas: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            
        # Přidáme tlačítko pro restart
        if st.button("🔄 Zkusit znovu"):
            st.rerun()
            
        st.stop()

    # -----------------------------
    # Insight engine
    # -----------------------------
    try:
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

        # Dominance
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
        
        log_user_activity(selected_id, "insights_generated", f"Generováno {len(insights)} insightů")
        
    except Exception as e:
        logger.error(f"Chyba při generování insightů pro {selected_id}: {e}")
        insight_text = "• Nepodařilo se vygenerovat osobní insighty."

    # -----------------------------
    # Připrav PDF
    # -----------------------------
    try:
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
            "Shrnutí tvých výsledků v emočním mapování:\n\n"
            f"Hodnotil(a) jsi {words_n} slov na třech dimenzích:\n"
            "• Valence (X-osa): jak příjemné/nepříjemné slovo vnímáš\n"
            "• Arousal (Z-osa): jak aktivující/uklidňující slovo na tebe působí\n" 
            "• Dominance (Y-osa): jakou míru kontroly u slova cítíš\n\n"
            f"Tvoje průměrná reakční doba: {user_rt:.2f} sekund\n"
            f"Celkový počet hodnocených slov: {words_n}\n\n"
            "Delta metriky (Δ) ukazují, o kolik se tvoje hodnocení lišila od průměru populace. "
            "Pozitivní hodnoty = vyšší hodnocení než průměr, negativní = nižší než průměr."
        )
        
        # Přidej kvalitativní analýzu pro PDF
        qualitative_pdf_text = ""
        try:
            thematic_df = load_thematic_data()
            if not thematic_df.empty:
                user_analysis = analyze_user_strategy(sub, deltas_all)
                qualitative_pdf_text = generate_qualitative_insights(user_analysis, [])
        except:
            qualitative_pdf_text = ""
        
        pdf_bytes = build_pdf_report(selected_id, summary_text, insight_text, figs, qualitative_pdf_text)
        log_user_activity(selected_id, "pdf_generated", "PDF report úspěšně vygenerován")
        
    except Exception as e:
        logger.error(f"Chyba při generování PDF pro {selected_id}: {e}")
        st.error("⚠️ **Varování:** Nepodařilo se vygenerovat PDF report.")
        pdf_bytes = None

    # -----------------------------
    # PDF tlačítko
    # -----------------------------
    if pdf_bytes:
        st.download_button("📄 Stáhnout osobní PDF report", data=pdf_bytes,
                        file_name=f"{selected_id}_emocni_profil.pdf", mime="application/pdf")
    
    st.divider()

    # -----------------------------
    # Vizualizace s vylepšenými popisy
    # -----------------------------
    st.subheader("📊 Srovnání s ostatními účastníky (radar graf)")
    st.caption("**Co ukazuje:** Tvé průměrné hodnoty (modré) vs. průměr všech účastníků (oranžové).  \n**Jak číst:** Větší překryv = podobnější jsi většině; větší rozdíly = unikátnější přístup.")
    st.plotly_chart(fig_radar, use_container_width=True)

    left,right = st.columns(2)
    with left:
        st.subheader("Jak vnímáš příjemnost slov")
        st.caption("**Co ukazuje:** Krabička = rozsah, ve kterém se nacházela většina účastníků. Červený diamant = tvá pozice.  \n**Jak číst:** Jsi-li uvnitř krabičky = typický. Mimo krabičku = máš výrazně odlišný styl hodnocení příjemnosti slov!")
        st.plotly_chart(fig_hist_val, use_container_width=True)
    with right:
        st.subheader("Jak vnímáš intenzitu emocí") 
        st.caption("**Co ukazuje:** Krabička = rozsah většiny účastníků. Červený diamant = ty.  \n**Jak číst:** Nad krabičkou = reaguješ intenzivněji než většina. Pod krabičkou = reaguješ klidněji. V krabičce = jsi typický!")
        st.plotly_chart(fig_hist_ar, use_container_width=True)

    st.subheader("Mapa tvých slov")
    st.caption("**Co ukazuje:** Každý bod = jedno slovo, které jsi hodnotil. Větší bublina = delší čas rozhodování.  \n**Jak číst:** Pozice ukazuje, jak jsi slovo posunul oproti očekávání. Najetím myší uvidíš detaily.")
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("Emoční ‚heatmapa' skupiny + tvá slova")
    st.caption("**Co ukazuje:** Teplá místa (žlutá/bílá) = tam hodnotila většina účastníků, studená (červená/černá) = méně časté. Červené body = tvá slova.  \n**Jak číst:** Pokud jsou tvá slova v teplých oblastech, hodnotíš podobně jako většina. V chladných oblastech = máš unikátní přístup!")
    st.plotly_chart(fig_contour, use_container_width=True)

    if fig_line is not None:
        st.subheader("Vývoj reakční doby")
        st.caption("**Co to je:** Jak se měnila tvoje rychlost během úkolu.  \n**Jak číst:** Trend dolů = zrychlování; trend nahoru = zpomalování.")
        st.plotly_chart(fig_line, use_container_width=True)

    # -----------------------------
    # Osobní insighty a druhé PDF tlačítko
    # -----------------------------
    st.divider()
    st.subheader("🔍 Tvé osobní insighty")
    st.markdown(insight_text)
    
    # -----------------------------
    # Kvalitativní analýza - porovnání s rozhovory
    # -----------------------------
    st.divider()
    st.subheader("💬 Co říkali ostatní účastníci s podobným stylem")
    st.caption("**Na základě rozhovorů:** Porovnání tvé strategie s tím, jak o úkolu mluvili ostatní účastníci.")
    
    try:
        # Načti tématická data
        thematic_df = load_thematic_data()
        
        if not thematic_df.empty:
            # Analyzuj uživatelovu strategii
            user_analysis = analyze_user_strategy(sub, deltas_all)
            
            # Najdi relevantní citáty
            matching_quotes = get_matching_quotes(user_analysis, thematic_df)
            
            # Generuj qualitativní insights
            qualitative_insights = generate_qualitative_insights(user_analysis, matching_quotes)
            
            # Zobraz analýzu
            st.markdown("**🎯 Tvá strategie hodnocení:**")
            st.markdown(qualitative_insights)
            
            if matching_quotes:
                st.markdown("**💭 Podobné přístupy jiných účastníků:**")
                
                for i, quote_data in enumerate(matching_quotes, 1):
                    with st.expander(f"📝 {quote_data['theme']}", expanded=(i==1)):
                        st.markdown(f"**Co to znamená:** {quote_data['definition']}")
                        st.markdown(f"**Citát od účastníka:** _{quote_data['quote']}_")
                        
                log_user_activity(selected_id, "qualitative_analysis", f"Zobrazeno {len(matching_quotes)} citátů")
            else:
                st.info("🔍 Tvůj styl je unikátní - nenašli jsme přesně odpovídající citáty z rozhovorů.")
                
        else:
            st.warning("⚠️ Tématická data nejsou k dispozici.")
            
    except Exception as e:
        logger.error(f"Chyba při kvalitativní analýze pro {selected_id}: {e}")
        st.error("⚠️ Nepodařilo se načíst kvalitativní srovnání.")

    if pdf_bytes:
        st.download_button("📄 Stáhnout PDF report (znovu)", data=pdf_bytes,
                        file_name=f"{selected_id}_emocni_profil.pdf", mime="application/pdf")

    st.divider()
    st.markdown("---")
    st.markdown("**🔒 Ochrana soukromí:** Tento report je určen pouze pro tebe. Obsahuje pouze tvá data a anonymizované skupinové průměry pro srovnání.")
    st.markdown("**❓ Máš dotazy?** Kontaktuj organizátory studie.")
    
    log_user_activity(selected_id, "report_completed", "Uživatel dokončil prohlížení reportu")

# Spuštění aplikace
if __name__ == "__main__":
    main()
