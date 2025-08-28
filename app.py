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
            st.stop()
            
        # Radar chart - moderní gradient design
        radar_categories = ["Δ valence (X)","Δ arousal (Z)","Reakční doba"]
        fig_radar = go.Figure()
        
        fig_radar.add_trace(go.Scatterpolar(
            r=[user_val,user_ar,user_rt], 
            theta=radar_categories, 
            fill='toself', 
            name='Tvůj profil',
            line=dict(color='#FF6B6B', width=3),  # Moderní růžová
            fillcolor='rgba(255, 107, 107, 0.3)'  
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=[overall["delta_valence"],overall["delta_arousal"],overall["First reaction time"]],
            theta=radar_categories, 
            fill='toself', 
            name='Průměr skupiny',
            line=dict(color='#4ECDC4', width=2, dash='dot'),  # Moderní tyrkysová
            fillcolor='rgba(78, 205, 196, 0.2)'
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    gridcolor='rgba(255,255,255,0.3)',
                    linecolor='rgba(255,255,255,0.3)'
                ),
                angularaxis=dict(
                    gridcolor='rgba(255,255,255,0.3)',
                    linecolor='rgba(255,255,255,0.3)'
                ),
                bgcolor='rgba(0,0,0,0)'
            ), 
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2C3E50', size=12),
            title=dict(
                text="Tvůj emoční radar",
                font=dict(size=16, color='#2C3E50'),
                x=0.5
            )
        )

        # Boxploty - moderní design s gradientem
        import numpy as np
        
        # Boxplot pro valenci - moderní design
        fig_hist_val = go.Figure()
        
        # Přidání boxplotu populace - moderní styl
        fig_hist_val.add_trace(go.Box(
            y=deltas_all["delta_valence"],
            name="Všichni účastníci",
            boxpoints=False,
            fillcolor='rgba(78, 205, 196, 0.7)',  # Moderní tyrkysová
            line=dict(color='#4ECDC4', width=2),
            marker=dict(color='#4ECDC4', size=8)
        ))
        
        # Přidání tvé hodnoty jako výrazný bod
        fig_hist_val.add_trace(go.Scatter(
            x=["Všichni účastníci"],
            y=[user_val],
            mode="markers",
            name="Tvá hodnota",
            marker=dict(
                color='#FF6B6B',  # Moderní růžová
                size=20,
                symbol="diamond",
                line=dict(color='#E85A4F', width=3)
            )
        ))
        
        # Výpočet percentilu pro interpretaci
        val_percentile = (deltas_all["delta_valence"] < user_val).mean() * 100
        val_interpretation = f"Tvoje hodnocení bylo pozitivnější než u {val_percentile:.0f}% účastníků" if user_val > 0 else f"Tvoje hodnocení bylo negativnější než u {100-val_percentile:.0f}% účastníků"
        
        fig_hist_val.update_layout(
            title=dict(
                text=f"Jak vnímáš příjemnost slov oproti ostatním<br><sub style='color:#7F8C8D'>{val_interpretation}</sub>",
                font=dict(size=14, color='#2C3E50'),
                x=0.5
            ),
            yaxis_title="Δ valence (negativnější ← 0 → pozitivnější)",
            xaxis_title="",
            showlegend=True,
            plot_bgcolor='rgba(248, 249, 250, 0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2C3E50'),
            annotations=[
                dict(
                    x=0, y=user_val,
                    text=f"Ty: {user_val:.2f}",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#FF6B6B",
                    ax=60, ay=0,
                    font=dict(color='#E85A4F', weight='bold')
                )
            ]
        )

        # Boxplot pro arousal - moderní design 
        fig_hist_ar = go.Figure()
        
        # Přidání boxplotu populace
        fig_hist_ar.add_trace(go.Box(
            y=deltas_all["delta_arousal"],
            name="Všichni účastníci",
            boxpoints=False,
            fillcolor='rgba(155, 89, 182, 0.7)',  # Moderní fialová
            line=dict(color='#9B59B6', width=2),
            marker=dict(color='#9B59B6', size=8)
        ))
        
        # Přidání tvé hodnoty
        fig_hist_ar.add_trace(go.Scatter(
            x=["Všichni účastníci"],
            y=[user_ar],
            mode="markers",
            name="Tvá hodnota",
            marker=dict(
                color='#FF6B6B',  # Stejná barva jako u valence
                size=20,
                symbol="diamond",
                line=dict(color='#E85A4F', width=3)
            )
        ))
        
        # Výpočet percentilu pro interpretaci
        ar_percentile = (deltas_all["delta_arousal"] < user_ar).mean() * 100
        ar_interpretation = f"Tvé reakce byly intenzivnější než u {ar_percentile:.0f}% účastníků" if user_ar > 0 else f"Tvé reakce byly klidnější než u {100-ar_percentile:.0f}% účastníků"
        
        fig_hist_ar.update_layout(
            title=dict(
                text=f"Jak intenzivně reaguješ na slova oproti ostatním<br><sub style='color:#7F8C8D'>{ar_interpretation}</sub>",
                font=dict(size=14, color='#2C3E50'),
                x=0.5
            ),
            yaxis_title="Δ arousal (klidnější ← 0 → intenzivnější)",
            xaxis_title="",
            showlegend=True,
            plot_bgcolor='rgba(248, 249, 250, 0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2C3E50'),
            annotations=[
                dict(
                    x=0, y=user_ar,
                    text=f"Ty: {user_ar:.2f}",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor="#FF6B6B",
                    ax=60, ay=0,
                    font=dict(color='#E85A4F', weight='bold')
                )
            ]
        )

        # Scatter (bubliny) - moderní design
        fig_scatter = px.scatter(
            sub, x="delta_arousal", y="delta_valence",
            size="First reaction time",
            hover_data={"Term":True,"delta_arousal":":.2f","delta_valence":":.2f","First reaction time":":.2f"},
            labels={"delta_arousal":"Δ arousal (intenzita)","delta_valence":"Δ valence (příjemnost)","First reaction time":"Reakční doba (s)"},
            title="Tvá slova v emočním prostoru",
            color_discrete_sequence=["#FF6B6B"]  # Moderní růžová
        )
        fig_scatter.update_layout(
            xaxis_title="Δ arousal (klidnější ← → intenzivnější)",
            yaxis_title="Δ valence (negativnější ← → pozitivnější)",
            plot_bgcolor='rgba(248, 249, 250, 0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2C3E50'),
            title=dict(
                font=dict(size=16, color='#2C3E50'),
                x=0.5
            )
        )

        # Kontury - INFRAČERVENÁ HEATMAPA (modrá → červená) - CLOUD SAFE
        fig_contour = px.density_contour(
            deltas_all, x="delta_arousal", y="delta_valence",
            labels={"delta_arousal":"Δ arousal (intenzita)","delta_valence":"Δ valence (příjemnost)"},
            title="Emoční mapa skupiny + tvá slova",
        )
        # Bezpečná infrared paleta - používáme přednastavený colorscale
        fig_contour.update_traces(
            contours_coloring="fill", 
            contours_showlabels=True,
            colorscale="RdYlBu_r",  # Red-Yellow-Blue reversed = infrared efekt
            showscale=True,
            colorbar=dict(
                title="Hustota<br>(studená → teplá)",
                titlefont=dict(color='#2C3E50')
            )
        )
        fig_contour.update_layout(
            xaxis_title="Δ arousal (klidnější ← → intenzivnější)",
            yaxis_title="Δ valence (negativnější ← → pozitivnější)",
            plot_bgcolor='rgba(248, 249, 250, 0.8)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#2C3E50'),
            title=dict(
                font=dict(size=16, color='#2C3E50'),
                x=0.5
            )
        )
        fig_contour.add_scatter(
            x=sub["delta_arousal"], y=sub["delta_valence"], 
            mode="markers+text",
            text=sub["Term"], 
            textposition="top center",
            marker=dict(
                color="#FFFFFF",  # Bílé body pro kontrast
                size=10, 
                opacity=1,
                symbol="circle",
                line=dict(color="#2C3E50", width=2)  # Tmavý okraj
            ), 
            name="Tvá slova",
            textfont=dict(color='#2C3E50', size=10)
        )

        # Line chart (pokud je Order) - moderní design
        fig_line = None
        if "Order" in sub.columns:
            srt = sub.sort_values("Order")
            fig_line = px.line(srt, x="Order", y="First reaction time", markers=True,
                              labels={"Order":"Pořadí","First reaction time":"Reakční doba (s)"},
                              title="Jak se měnila tvoje reakční doba během úkolu",
                              color_discrete_sequence=["#FF6B6B"])
            
            # Aplikace moderního stylu na časový graf
            fig_line.update_traces(
                line=dict(width=3, color="#FF6B6B"),
                marker=dict(size=8, color="#FF6B6B", line=dict(width=2, color="white")),
                hovertemplate="<b>Pořadí:</b> %{x}<br><b>Reakční doba:</b> %{y:.2f}s<extra></extra>"
            )
            
            fig_line.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)", 
                font=dict(family="Arial, sans-serif", size=14, color="#2C3E50"),
                title=dict(font=dict(size=18, color="#2C3E50"), x=0.5),
                xaxis=dict(
                    showgrid=True, 
                    gridcolor="rgba(200,200,200,0.3)",
                    showline=True,
                    linecolor="rgba(200,200,200,0.8)"
                ),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor="rgba(200,200,200,0.3)",
                    showline=True,
                    linecolor="rgba(200,200,200,0.8)"
                ),
                hovermode="x unified",
                margin=dict(l=10, r=10, t=60, b=10)
            )

        log_user_activity(selected_id, "charts_created", "Všechny grafy úspěšně vytvořeny")
        
    except Exception as e:
        logger.error(f"Chyba při vytváření grafů pro {selected_id}: {e}")
        st.error("🚫 **Chyba při vytváření vizualizací.** Kontaktujte podporu.")
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
        st.subheader("� Jak vnímáš příjemnost slov")
        st.caption("**Co ukazuje:** Krabička = rozsah, ve kterém se nacházela většina účastníků. Červený diamant = tvá pozice.  \n**Jak číst:** Jsi-li uvnitř krabičky = typický. Mimo krabičku = máš výrazně odlišný styl hodnocení příjemnosti slov!")
        st.plotly_chart(fig_hist_val, use_container_width=True)
    with right:
        st.subheader("� Jak vnímáš intenzitu emocí") 
        st.caption("**Co ukazuje:** Krabička = rozsah většiny účastníků. Červený diamant = ty.  \n**Jak číst:** Nad krabičkou = reaguješ intenzivněji než většina. Pod krabičkou = reaguješ klidněji. V krabičce = jsi typický!")
        st.plotly_chart(fig_hist_ar, use_container_width=True)

    st.subheader("🎯 Mapa tvých slov")
    st.caption("**Co ukazuje:** Každý bod = jedno slovo, které jsi hodnotil. Větší bublina = delší čas rozhodování.  \n**Jak číst:** Pozice ukazuje, jak jsi slovo posunul oproti očekávání. Najetím myší uvidíš detaily.")
    st.plotly_chart(fig_scatter, use_container_width=True)

    st.subheader("🔥 Emoční ‚heatmapa' skupiny + tvá slova")
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
