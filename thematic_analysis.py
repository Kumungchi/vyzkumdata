# thematic_analysis.py
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple

def load_thematic_data():
    """Načte tématický codebook"""
    try:
        df = pd.read_csv("data/Detailed_Thematic_Codebook.csv")
        return df
    except Exception as e:
        print(f"Chyba při načítání tématických dat: {e}")
        return pd.DataFrame()

def analyze_user_strategy(user_data: pd.DataFrame, deltas_all: pd.DataFrame) -> Dict[str, any]:
    """
    Analyzuje uživatelovu strategii na základě jeho dat
    a porovná s kvalitativními zjištěními
    """
    
    if user_data.empty:
        return {}
    
    analysis = {}
    
    # 1. Analýza mapping strategií
    val_range = user_data['delta_valence'].max() - user_data['delta_valence'].min()
    ar_range = user_data['delta_arousal'].max() - user_data['delta_arousal'].min()
    
    # 2. Identifikace dominantní strategie
    if val_range > 1.5:
        analysis['valence_strategy'] = 'DEPTH_VAL'
        analysis['valence_strength'] = 'silné'
    elif val_range > 0.8:
        analysis['valence_strategy'] = 'DEPTH_VAL'  
        analysis['valence_strength'] = 'mírné'
    else:
        analysis['valence_strategy'] = 'neutral'
        analysis['valence_strength'] = 'minimální'
        
    if ar_range > 1.5:
        analysis['arousal_strategy'] = 'VERT_INT'
        analysis['arousal_strength'] = 'silné'
    elif ar_range > 0.8:
        analysis['arousal_strategy'] = 'VERT_INT'
        analysis['arousal_strength'] = 'mírné'
    else:
        analysis['arousal_strategy'] = 'neutral'
        analysis['arousal_strength'] = 'minimální'
    
    # 3. Analýza rychlosti (fatigue/systematic approach)
    if 'Order' in user_data.columns and 'First reaction time' in user_data.columns:
        rt_trend = np.corrcoef(user_data['Order'], user_data['First reaction time'])[0,1]
        if rt_trend > 0.3:
            analysis['speed_pattern'] = 'FATIGUE'
        elif rt_trend < -0.3:
            analysis['speed_pattern'] = 'SYS_DEV'  # zrychlování = systematizace
        else:
            analysis['speed_pattern'] = 'stable'
    
    # 4. Konzistence (memory & consistency)
    val_std = user_data['delta_valence'].std()
    ar_std = user_data['delta_arousal'].std()
    
    if val_std < 0.3 and ar_std < 0.3:
        analysis['consistency'] = 'MEM_REF'  # velmi konzistentní
    elif val_std > 1.0 or ar_std > 1.0:
        analysis['consistency'] = 'IND_DIFF'  # velmi variabilní
    else:
        analysis['consistency'] = 'moderate'
    
    # 5. Porovnání s populací
    user_val_mean = user_data['delta_valence'].mean()
    user_ar_mean = user_data['delta_arousal'].mean()
    
    pop_val_mean = deltas_all['delta_valence'].mean()
    pop_ar_mean = deltas_all['delta_arousal'].mean()
    
    analysis['population_comparison'] = {
        'valence_vs_pop': user_val_mean - pop_val_mean,
        'arousal_vs_pop': user_ar_mean - pop_ar_mean
    }
    
    return analysis

def get_matching_quotes(analysis: Dict, thematic_df: pd.DataFrame) -> List[Dict[str, str]]:
    """Najde relevantní citáty na základě uživatelovy analýzy"""
    
    matching_quotes = []
    
    if thematic_df.empty:
        return matching_quotes
    
    # Mapování strategií na kódy
    relevant_codes = []
    
    if analysis.get('valence_strategy') == 'DEPTH_VAL':
        relevant_codes.append('DEPTH_VAL')
    if analysis.get('arousal_strategy') == 'VERT_INT':  
        relevant_codes.append('VERT_INT')
    if analysis.get('speed_pattern') == 'FATIGUE':
        relevant_codes.append('FATIGUE')
    elif analysis.get('speed_pattern') == 'SYS_DEV':
        relevant_codes.append('SYS_DEV')
    if analysis.get('consistency') == 'MEM_REF':
        relevant_codes.append('MEM_REF')
    elif analysis.get('consistency') == 'IND_DIFF':
        relevant_codes.append('IND_DIFF')
    
    # Najdi citáty pro relevantní kódy
    for code in relevant_codes:
        matches = thematic_df[thematic_df['Code'] == code]
        for _, row in matches.iterrows():
            matching_quotes.append({
                'theme': row['Subtheme'],
                'definition': row['Definition'], 
                'quote': row['Example quotes'],
                'code': code
            })
    
    # Pokud nemáme specifické matches, vezmi reprezentativní ukázky
    if not matching_quotes:
        # Základní strategie mapping
        for code in ['DEPTH_VAL', 'VERT_INT', 'HORIZ_DOM']:
            matches = thematic_df[thematic_df['Code'] == code]
            if not matches.empty:
                row = matches.iloc[0]
                matching_quotes.append({
                    'theme': row['Subtheme'],
                    'definition': row['Definition'],
                    'quote': row['Example quotes'],
                    'code': code
                })
    
    return matching_quotes[:3]  # Max 3 citáty

def generate_qualitative_insights(analysis: Dict, quotes: List[Dict]) -> str:
    """Generuje textový popis kvalitativních pozorování"""
    
    insights = []
    
    # Hlavní strategie
    if analysis.get('valence_strategy') == 'DEPTH_VAL':
        strength = analysis.get('valence_strength', 'mírné')
        insights.append(f"**Valence mapping**: Máš {strength} využívání prostorové hloubky pro příjemnost/nepříjemnost slov.")
    
    if analysis.get('arousal_strategy') == 'VERT_INT':
        strength = analysis.get('arousal_strength', 'mírné')  
        insights.append(f"**Vertikální intenzita**: {strength.capitalize()} mapování emoční síly na vertikální osu.")
    
    # Vzorce chování  
    if analysis.get('speed_pattern') == 'FATIGUE':
        insights.append("**Únava během testování**: Postupně ses zpomaloval, což je normální při této délce úkolu.")
    elif analysis.get('speed_pattern') == 'SYS_DEV':
        insights.append("**Systematický přístup**: Postupně ses zrychloval - vyvinul sis efektivní strategii.")
    
    if analysis.get('consistency') == 'MEM_REF':
        insights.append("**Vysoká konzistence**: Pamatuješ si své předchozí volby a držíš se jednotné logiky.")
    elif analysis.get('consistency') == 'IND_DIFF':
        insights.append("**Kreativní přístup**: Používáš rozmanité, atypické způsoby umísťování slov.")
    
    # Porovnání s populací
    pop_comp = analysis.get('population_comparison', {})
    val_diff = pop_comp.get('valence_vs_pop', 0)
    ar_diff = pop_comp.get('arousal_vs_pop', 0)
    
    if abs(val_diff) > 0.3:
        direction = "pozitivněji" if val_diff > 0 else "negativněji"
        insights.append(f"**Valence odlišnost**: Obecně hodnotíš slova {direction} než průměr skupiny.")
    
    if abs(ar_diff) > 0.3:
        direction = "intenzivněji" if ar_diff > 0 else "klidněji" 
        insights.append(f"**Arousal odlišnost**: Vnímáš emoční intenzitu {direction} než ostatní.")
    
    return " • " + "\n • ".join(insights) if insights else "• Tvůj přístup je velmi blízký průměru skupiny."
