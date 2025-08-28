# pdf_utils.py
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

def fig_to_png_bytes(fig, scale=2):
    """Bezpečná konverze grafu na PNG - funguje v cloudu"""
    try:
        # Pokus o kaleido
        return fig.to_image(format="png", scale=scale, engine="kaleido")
    except Exception as e:
        try:
            # Fallback na orca
            return fig.to_image(format="png", scale=scale, engine="orca")
        except Exception as e2:
            try:
                # Poslední pokus - základní export
                import io
                import base64
                return fig.to_image(format="png", width=800, height=600)
            except Exception as e3:
                # Pokud všechno selže, vrať prázdný obrázek
                from PIL import Image
                import io
                img = Image.new('RGB', (800, 600), color='white')
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                return buf.getvalue()

def draw_wrapped_text(c, text, x, y, max_width=480, leading=14, font="Helvetica", size=10):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    c.setFont(font, size)
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            test = (line + " " + word).strip()
            if stringWidth(test, font, size) <= max_width:
                line = test
            else:
                if line: lines.append(line)
                line = word
        if line: lines.append(line)
    for ln in lines:
        c.drawString(x, y, ln)
        y -= leading
    return y

def build_pdf_report(selected_id, summary_text, insight_text, figs, qualitative_text=""):
    """figs = dict(name->plotly_figure) pro vložení do PDF."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Strana 1 – titul a shrnutí
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, h-60, "Osobní emoční profil - Výzkumná studie")
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h-90, f"Účastník: {selected_id}")
    c.setFont("Helvetica", 10)
    c.drawString(50, h-110, "Datum vytvoření: 28. srpna 2025")
    
    # Úvod do výzkumu
    research_intro = """Tento report obsahuje váš osobní emoční profil vytvořený na základě výzkumu teorie ztělesněných emocí. 
Vaše hodnocení emocí ve slovech bylo zmapováno do třídimenzionálního prostoru, kde X-osa představuje valenci 
(příjemnost-nepříjemnost), Z-osa arousal (aktivace-deaktivace) a Y-osa dominanci (kontrola-submise)."""
    
    y = draw_wrapped_text(c, research_intro, x=50, y=h-140, max_width=500, size=10)
    y = draw_wrapped_text(c, summary_text, x=50, y=y-20, max_width=500, size=11)
    c.showPage()

    # Strana 2 – radar graf a distribuce
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h-60, "1. Tvůj emoční radar - trojdimenzionální profil")
    c.setFont("Helvetica", 10)
    c.drawString(50, h-80, "Poloha v emočním prostoru: Valence (X), Arousal (Z), Dominance (Y)")
    
    if "radar" in figs:
        png = fig_to_png_bytes(figs["radar"], scale=2)
        c.drawImage(ImageReader(BytesIO(png)), 40, h-360, width=520, height=280, preserveAspectRatio=True, mask='auto')
    
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, h-390, "2. Jak se lišíš od ostatních účastníků")
    c.setFont("Helvetica", 10)
    c.drawString(50, h-405, "Krabička = většina lidí, červený diamant = ty")
    
    if "hist_val" in figs:
        png = fig_to_png_bytes(figs["hist_val"], scale=2)
        c.drawImage(ImageReader(BytesIO(png)), 40, h-680, width=250, height=280, preserveAspectRatio=True, mask='auto')
    if "hist_ar" in figs:
        png = fig_to_png_bytes(figs["hist_ar"], scale=2)
        c.drawImage(ImageReader(BytesIO(png)), 310, h-680, width=250, height=280, preserveAspectRatio=True, mask='auto')
    c.showPage()

    # Strana 3 – detailní analýza
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h-60, "3. Detailní analýza tvých emočních odpovědí")
    c.setFont("Helvetica", 10)
    c.drawString(50, h-80, "Pozice jednotlivých slov v emočním prostoru (velikost = reakční doba)")
    
    if "scatter" in figs:
        png = fig_to_png_bytes(figs["scatter"], scale=2)
        c.drawImage(ImageReader(BytesIO(png)), 40, h-360, width=520, height=280, preserveAspectRatio=True, mask='auto')
    
    c.setFont("Helvetica-Bold", 12)  
    c.drawString(50, h-390, "4. Hustotní mapa emočního prostoru")
    c.setFont("Helvetica", 10)
    c.drawString(50, h-405, "Teplé oblasti = vyšší koncentrace tvých hodnocení")
    
    if "contour" in figs:
        png = fig_to_png_bytes(figs["contour"], scale=2)
        c.drawImage(ImageReader(BytesIO(png)), 40, h-680, width=520, height=260, preserveAspectRatio=True, mask='auto')
    c.showPage()

    # Strana 4 – insighty a reakční doba
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h-60, "5. Tvoje osobní emoční insighty")
    
    y = draw_wrapped_text(c, insight_text, x=50, y=h-90, max_width=500, size=10)
    
    # Kvalitativní analýza
    if qualitative_text:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y-20, "Porovnání s ostatními účastníky:")
        y = draw_wrapped_text(c, qualitative_text, x=50, y=y-40, max_width=500, size=9)
    
    c.setFont("Helvetica-Bold", 12)
    line_y = y-40 if qualitative_text else h-320
    c.drawString(50, line_y, "6. Vývoj reakční doby během testování")
    c.setFont("Helvetica", 10)
    c.drawString(50, line_y-15, "Změny rychlosti odpovědí v průběhu hodnocení slov")
    
    if "line_rt" in figs:
        png = fig_to_png_bytes(figs["line_rt"], scale=2)
        chart_y = line_y-300 if qualitative_text else h-620
        c.drawImage(ImageReader(BytesIO(png)), 40, chart_y, width=520, height=260, preserveAspectRatio=True, mask='auto')
        
    # Závěrečné poznámky
    c.setFont("Helvetica", 9)
    footer_text = """Tento report byl vygenerován automaticky na základě vašich odpovědí ve výzkumu emoční 
sémantiky. Data byla analyzována pomocí algoritmu trojdimenzionálního mapování emocí. 
Výsledky slouží pouze pro výzkumné účely."""
    draw_wrapped_text(c, footer_text, x=50, y=h-650, max_width=500, size=9)

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
