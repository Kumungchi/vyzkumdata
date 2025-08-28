# utils.py
import pandas as pd

# Převod baseline štítků → čísla
MAP_AROUSAL = {"nízký": 1, "střední": 2, "vysoký": 3,
               "Nízký": 1, "Střední": 2, "Vysoký": 3}
MAP_VALENCE = {"negativní": -1, "neutrální": 0, "pozitivní": 1,
               "Negativní": -1, "Neutrální": 0, "Pozitivní": 1}

def standardize_hand_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Sjednotí názvy sloupců v hand_dataset na:
       ID, Term, Pos X(Valence), Pos Y(Dominance), Pos Z(Arousal), First reaction time, Total reaction time, Order."""
    rename_map = {}
    for c in df.columns:
        lc = c.lower()
        if lc in ["id","respondent","participant"]:
            rename_map[c] = "ID"
        elif lc in ["term","slovo","pojem","word"]:
            rename_map[c] = "Term"
        elif "pos x" in lc or lc in ["x","pos_x","xpos"]:
            rename_map[c] = "Pos X"      # Valence (X)
        elif "pos y" in lc or lc in ["y","pos_y","ypos"]:
            rename_map[c] = "Pos Y"      # Dominance (Y)
        elif "pos z" in lc or lc in ["z","pos_z","zpos"]:
            rename_map[c] = "Pos Z"      # Arousal (Z)
        elif "first reaction time" in lc or "první" in lc:
            rename_map[c] = "First reaction time"
        elif "total reaction time" in lc or "celkov" in lc:
            rename_map[c] = "Total reaction time"
        elif "pořadí" in lc or "order" in lc or "trial" in lc:
            rename_map[c] = "Order"
    df = df.rename(columns=rename_map)

    # Numerické sloupce
    for col in ["Pos X","Pos Y","Pos Z","First reaction time","Total reaction time"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def _detect_word_col(vybrana: pd.DataFrame) -> str:
    for c in vybrana.columns:
        if any(k in c.lower() for k in ["přídav", "adjekt", "slovo", "word"]):
            return c
    return vybrana.columns[0]

def compute_deltas(hand_df: pd.DataFrame, vybrana: pd.DataFrame) -> pd.DataFrame:
    """Výpočet delt dle konvence: X=Valence, Z=Arousal, Y=Dominance (bez baseline)."""
    word_col = _detect_word_col(vybrana)
    v = vybrana.rename(columns={word_col: "Word"})

    merged = hand_df.merge(v, left_on="Term", right_on="Word", how="left")
    merged["baseline_arousal"] = merged["Arousal"].map(MAP_AROUSAL)
    merged["baseline_valence"] = merged["Valence"].map(MAP_VALENCE)

    merged["delta_valence"] = merged["Pos X"] - merged["baseline_valence"]
    merged["delta_arousal"]  = merged["Pos Z"] - merged["baseline_arousal"]
    # dominance (Pos Y) porovnáváme jen vůči skupině → žádné delta_dominance
    return merged
