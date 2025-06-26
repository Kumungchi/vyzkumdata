import pandas as pd
import docx
import re

def load_data():
    """
    Načte data a převede numerické sloupce na float.
    """
    vybrana = pd.read_csv("data/vybrana_slova_30.csv")
    hand    = pd.read_csv("data/hand_dataset.csv", sep=";", engine="python")
    # Převod prostorových a časových sloupců na čísla
    for col in ["Pos X", "Pos Y", "Pos Z", "First reaction time", "Total reaction time"]:
        hand[col] = pd.to_numeric(hand[col], errors="coerce")
    codebook = pd.read_csv("data/Detailed_Thematic_Codebook.csv")
    return vybrana, hand, codebook

def compute_deltas(df, vybrana):
    """
    Spojí 'Term' ↔ 'Přídavné jméno', mapuje kategorie na čísla,
    a vypočítá delta_arousal a delta_valence.
    """
    merged = df.merge(
        vybrana,
        left_on="Term",
        right_on="Přídavné jméno",
        how="left"
    )

    # Mapování kategorií
    mapping_arousal = {"nízký": 1, "střední": 2, "vysoký": 3}
    mapping_valence = {"negativní": -1, "neutrální": 0, "pozitivní": 1}

    merged["default_arousal_num"] = merged["Arousal"].map(mapping_arousal)
    merged["default_valence_num"] = merged["Valence"].map(mapping_valence)

    # Výpočet delt
    merged["delta_arousal"] = merged["Pos Y"] - merged["default_arousal_num"]
    merged["delta_valence"] = merged["Pos Z"] - merged["default_valence_num"]

    return merged

def load_transcripts(participant_id):
    """
    Načte z Přepisy.docx všechny odstavce od prvního výskytu daného ID
    až do dalšího respondentova kódu (PCM/PCZ) nebo konce dokumentu.
    """
    doc = docx.Document("data/Přepisy.docx")
    paras = [p.text for p in doc.paragraphs]
    start = next(i for i, txt in enumerate(paras) if participant_id in txt)
    end = next((i for i, txt in enumerate(paras[start+1:], start+1)
                if re.match(r"^(PCM|PCZ)\d+", txt.strip())), len(paras))
    return "\n".join(paras[start:end])

def thematic_counts(text, codebook):
    """
    Pro každý kód ze codebooku spočítá, kolikrát se objevil v textu,
    a vrátí jeho úryvek kolem prvního výskytu.
    """
    counts, examples = {}, {}
    lc = text.lower()
    for _, row in codebook.iterrows():
        code = row["Code"]
        cnt  = lc.count(code.lower())
        if cnt > 0:
            counts[code] = cnt
            m = re.search(r"([^.]*" + re.escape(code) + r"[^.]*\.)", text, re.IGNORECASE)
            examples[code] = [m.group(1).strip()] if m else []
    return counts, examples
