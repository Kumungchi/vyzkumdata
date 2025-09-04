# pdf_utils.py
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# Registrace fontů pro podporu českých znaků
def register_fonts():
    """Registruje fonty s podporou UTF-8"""
    try:
        # Zkusíme DejaVu fonty (běžně dostupné na Linuxu)
        pdfmetrics.registerFont(TTFont('DejaVu', 'DejaVuSans.ttf'))
        pdfmetrics.registerFont(TTFont('DejaVu-Bold', 'DejaVuSans-Bold.ttf'))
        return 'DejaVu'
    except:
        try:
            # Fallback na system fonty Windows
            if os.name == 'nt':  # Windows
                # Najdeme fonts složku
                fonts_dir = os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts')
                arial_path = os.path.join(fonts_dir, 'arial.ttf')
                arial_bold_path = os.path.join(fonts_dir, 'arialbd.ttf')
                
                if os.path.exists(arial_path):
                    pdfmetrics.registerFont(TTFont('Arial-Unicode', arial_path))
                    if os.path.exists(arial_bold_path):
                        pdfmetrics.registerFont(TTFont('Arial-Unicode-Bold', arial_bold_path))
                    return 'Arial-Unicode'
        except:
            pass
        
        try:
            # Zkusíme alternativní fonty
            pdfmetrics.registerFont(TTFont('Ubuntu', 'Ubuntu-R.ttf'))
            pdfmetrics.registerFont(TTFont('Ubuntu-Bold', 'Ubuntu-B.ttf'))
            return 'Ubuntu'
        except:
            pass
    
    # Pokud nic nefunguje, použijeme základní font s UTF-8 supportem
    # Alespoň zkusíme zaregistrovat Times-Roman s UTF-8
    try:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
        return 'HeiseiKakuGo-W5'
    except:
        pass
    
    return 'Helvetica'

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

def draw_wrapped_text(c, text, x, y, max_width=480, leading=14, font="DejaVu", size=10):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    
    # Bezpečné nastavení fontu s fallback
    try:
        c.setFont(font, size)
    except:
        c.setFont("Helvetica", size)
        font = "Helvetica"
    
    # Pokud používáme základní font, zkusíme alespoň enkódovat text
    if font == "Helvetica":
        try:
            # Pokus o enkódování pro základní fonty
            text = text.encode('latin-1', 'replace').decode('latin-1')
        except:
            # Náhrada problematických znaků
            replacements = {
                'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e', 'í': 'i', 
                'ň': 'n', 'ó': 'o', 'ř': 'r', 'š': 's', 'ť': 't', 'ú': 'u', 
                'ů': 'u', 'ý': 'y', 'ž': 'z',
                'Á': 'A', 'Č': 'C', 'Ď': 'D', 'É': 'E', 'Ě': 'E', 'Í': 'I',
                'Ň': 'N', 'Ó': 'O', 'Ř': 'R', 'Š': 'S', 'Ť': 'T', 'Ú': 'U',
                'Ů': 'U', 'Ý': 'Y', 'Ž': 'Z'
            }
            for czech, ascii_char in replacements.items():
                text = text.replace(czech, ascii_char)
    
    lines = []
    for paragraph in text.split("\n"):
        line = ""
        for word in paragraph.split(" "):
            test = (line + " " + word).strip()
            try:
                width = stringWidth(test, font, size)
            except:
                width = len(test) * size * 0.6  # Aproximace šířky
            
            if width <= max_width:
                line = test
            else:
                if line: lines.append(line)
                line = word
        if line: lines.append(line)
    
    for ln in lines:
        try:
            c.drawString(x, y, ln)
        except:
            # Pokud selže kreslení, zkusíme bez diakritiky
            ln_safe = ln.encode('ascii', 'replace').decode('ascii')
            c.drawString(x, y, ln_safe)
        y -= leading
    return y

def build_pdf_report(selected_id, summary_text, insight_text, figs, qualitative_text=""):
    """figs = dict(name->plotly_figure) pro vložení do PDF."""
    
    # Registrujeme fonty pro podporu českých znaků
    font_name = register_fonts()
    font_bold = font_name + '-Bold' if font_name != 'Helvetica' else 'Helvetica-Bold'
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    w, h = A4

    # Strana 1 – titul a shrnutí
    try:
        c.setFont(font_bold, 18)
        c.drawString(50, h-60, "Osobní emoční profil - Výzkumná studie")
    except:
        c.setFont("Helvetica-Bold", 18)
        c.drawString(50, h-60, "Osobni emocni profil - Vyzkumna studie")
    
    try:
        c.setFont(font_bold, 14)
        c.drawString(50, h-90, f"Účastník: {selected_id}")
    except:
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, h-90, f"Ucastnik: {selected_id}")
    
    try:
        c.setFont(font_name, 10)
        c.drawString(50, h-110, "Datum vytvoření: 28. srpna 2025")
    except:
        c.setFont("Helvetica", 10)
        c.drawString(50, h-110, "Datum vytvoreni: 28. srpna 2025")
    
    # Úvod do výzkumu
    research_intro = """Tento report obsahuje váš osobní emoční profil vytvořený na základě výzkumu teorie ztělesněných emocí. 
Vaše hodnocení emocí ve slovech bylo zmapováno do třídimenzionálního prostoru, kde X-osa představuje valenci 
(příjemnost-nepříjemnost), Z-osa arousal (aktivace-deaktivace) a Y-osa dominanci (kontrola-submise)."""
    
    y = draw_wrapped_text(c, research_intro, x=50, y=h-140, max_width=500, size=10, font=font_name)
    y = draw_wrapped_text(c, summary_text, x=50, y=y-20, max_width=500, size=11, font=font_name)
    c.showPage()

    # Strana 2 – radar graf a distribuce
    try:
        c.setFont(font_bold, 14)
    except:
        c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h-60, "1. Tvůj emoční radar - trojdimenzionální profil")
    
    try:
        c.setFont(font_name, 10)
    except:
        c.setFont("Helvetica", 10)
    c.drawString(50, h-80, "Poloha v emočním prostoru: Valence (X), Arousal (Z), Dominance (Y)")
    
    if "radar" in figs:
        png = fig_to_png_bytes(figs["radar"], scale=2)
        c.drawImage(ImageReader(BytesIO(png)), 40, h-360, width=520, height=280, preserveAspectRatio=True, mask='auto')
    
    try:
        c.setFont(font_bold, 12)
    except:
        c.setFont("Helvetica-Bold", 12)
    c.drawString(50, h-390, "2. Jak se lišíš od ostatních účastníků")
    
    try:
        c.setFont(font_name, 10)
    except:
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
    try:
        c.setFont(font_bold, 14)
    except:
        c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h-60, "3. Detailní analýza tvých emočních odpovědí")
    
    try:
        c.setFont(font_name, 10)
    except:
        c.setFont("Helvetica", 10)
    c.drawString(50, h-80, "Pozice jednotlivých slov v emočním prostoru (velikost = reakční doba)")
    
    if "scatter" in figs:
        png = fig_to_png_bytes(figs["scatter"], scale=2)
        c.drawImage(ImageReader(BytesIO(png)), 40, h-360, width=520, height=280, preserveAspectRatio=True, mask='auto')
    
    try:
        c.setFont(font_bold, 12)
    except:
        c.setFont("Helvetica-Bold", 12)
    c.drawString(50, h-390, "4. Hustotní mapa emočního prostoru")
    
    try:
        c.setFont(font_name, 10)
    except:
        c.setFont("Helvetica", 10)
    c.drawString(50, h-405, "Teplé oblasti = vyšší koncentrace tvých hodnocení")
    
    if "contour" in figs:
        png = fig_to_png_bytes(figs["contour"], scale=2)
        c.drawImage(ImageReader(BytesIO(png)), 40, h-680, width=520, height=260, preserveAspectRatio=True, mask='auto')
    c.showPage()

    # Strana 4 – insighty a reakční doba
    try:
        c.setFont(font_bold, 14)
    except:
        c.setFont("Helvetica-Bold", 14)
    c.drawString(50, h-60, "5. Tvoje osobní emoční insighty")
    
    y = draw_wrapped_text(c, insight_text, x=50, y=h-90, max_width=500, size=10, font=font_name)
    
    # Kvalitativní analýza
    if qualitative_text:
        try:
            c.setFont(font_bold, 12)
        except:
            c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y-20, "Porovnání s ostatními účastníky:")
        y = draw_wrapped_text(c, qualitative_text, x=50, y=y-40, max_width=500, size=9, font=font_name)
    
    try:
        c.setFont(font_bold, 12)
    except:
        c.setFont("Helvetica-Bold", 12)
    line_y = y-40 if qualitative_text else h-320
    c.drawString(50, line_y, "6. Vývoj reakční doby během testování")
    
    try:
        c.setFont(font_name, 10)
    except:
        c.setFont("Helvetica", 10)
    c.drawString(50, line_y-15, "Změny rychlosti odpovědí v průběhu hodnocení slov")
    
    if "line_rt" in figs:
        png = fig_to_png_bytes(figs["line_rt"], scale=2)
        chart_y = line_y-300 if qualitative_text else h-620
        c.drawImage(ImageReader(BytesIO(png)), 40, chart_y, width=520, height=260, preserveAspectRatio=True, mask='auto')
        
    # Závěrečné poznámky
    try:
        c.setFont(font_name, 9)
    except:
        c.setFont("Helvetica", 9)
    footer_text = """Tento report byl vygenerován automaticky na základě vašich odpovědí ve výzkumu emoční 
sémantiky. Data byla analyzována pomocí algoritmu trojdimenzionálního mapování emocí. 
Výsledky slouží pouze pro výzkumné účely."""
    draw_wrapped_text(c, footer_text, x=50, y=h-650, max_width=500, size=9, font=font_name)

    c.showPage()
    c.save()
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
