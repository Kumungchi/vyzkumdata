# test_app.py
import unittest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
import sys
import os

# Přidej current directory do sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import standardize_hand_columns, compute_deltas, MAP_AROUSAL, MAP_VALENCE
from error_handler import validate_data_structure, safe_numeric_conversion, validate_user_id

class TestUtils(unittest.TestCase):
    """Testy pro utils.py funkce"""
    
    def setUp(self):
        """Nastavení test dat"""
        self.sample_hand_data = pd.DataFrame({
            'ID': ['TEST001', 'TEST002'],
            'Term': ['pozitivní', 'negativní'],
            'Pos X': [0.5, -0.3],
            'Pos Y': [0.2, -0.1], 
            'Pos Z': [0.8, 0.4],
            'First reaction time': [2.5, 3.1],
            'Total reaction time': [2.5, 3.1],
            'Order': [1, 2]
        })
        
        self.sample_baseline_data = pd.DataFrame({
            'Word': ['pozitivní', 'negativní'],
            'Valence': ['pozitivní', 'negativní'],
            'Arousal': ['vysoký', 'střední']
        })

    def test_standardize_hand_columns_basic(self):
        """Test základní standardizace sloupců"""
        # Test s již správnými názvy
        result = standardize_hand_columns(self.sample_hand_data.copy())
        expected_cols = ['ID', 'Term', 'Pos X', 'Pos Y', 'Pos Z', 'First reaction time', 'Total reaction time', 'Order']
        for col in expected_cols:
            self.assertIn(col, result.columns)
    
    def test_compute_deltas_basic(self):
        """Test základního výpočtu delt"""
        result = compute_deltas(self.sample_hand_data, self.sample_baseline_data)
        
        # Zkontroluj, že jsou přidány delta sloupce
        self.assertIn('delta_valence', result.columns)
        self.assertIn('delta_arousal', result.columns)
        self.assertIn('baseline_arousal', result.columns) 
        self.assertIn('baseline_valence', result.columns)
    
    def test_compute_deltas_values(self):
        """Test správnosti vypočtených hodnot"""
        result = compute_deltas(self.sample_hand_data, self.sample_baseline_data)
        
        # Pro pozitivní slovo: baseline_valence=1, Pos X=0.5, delta = 0.5-1 = -0.5
        pos_row = result[result['Term'] == 'pozitivní'].iloc[0]
        self.assertEqual(pos_row['baseline_valence'], 1)  # pozitivní = 1
        self.assertAlmostEqual(pos_row['delta_valence'], -0.5, places=2)
        
        # Pro negativní slovo: baseline_valence=-1, Pos X=-0.3, delta = -0.3-(-1) = 0.7
        neg_row = result[result['Term'] == 'negativní'].iloc[0]
        self.assertEqual(neg_row['baseline_valence'], -1)  # negativní = -1
        self.assertAlmostEqual(neg_row['delta_valence'], 0.7, places=2)

class TestErrorHandler(unittest.TestCase):
    """Testy pro error_handler.py funkce"""
    
    def setUp(self):
        self.sample_df = pd.DataFrame({
            'ID': [1, 2, 3],
            'Name': ['A', 'B', 'C'],
            'Value': ['1.5', '2.0', 'invalid']
        })
    
    def test_validate_data_structure_success(self):
        """Test úspěšné validace struktury"""
        result = validate_data_structure(self.sample_df, ['ID', 'Name'], 'test_data')
        self.assertTrue(result)
    
    def test_validate_data_structure_missing_columns(self):
        """Test validace s chybějícími sloupci"""
        with patch('streamlit.error'):  # Mock streamlit.error
            result = validate_data_structure(self.sample_df, ['ID', 'Missing_Col'], 'test_data')
            self.assertFalse(result)
    
    def test_safe_numeric_conversion(self):
        """Test bezpečné konverze numerických hodnot"""
        result = safe_numeric_conversion(self.sample_df.copy(), ['Value'])
        
        # První dvě hodnoty by měly být čísla, třetí NaN
        self.assertEqual(result['Value'].iloc[0], 1.5)
        self.assertEqual(result['Value'].iloc[1], 2.0)
        self.assertTrue(pd.isna(result['Value'].iloc[2]))
    
    def test_validate_user_id_success(self):
        """Test úspěšné validace user ID"""
        with patch('streamlit.error'), patch('streamlit.info'):
            result = validate_user_id('TEST001', ['TEST001', 'TEST002', 'TEST003'])
            self.assertTrue(result)
    
    def test_validate_user_id_failure(self):
        """Test neúspěšné validace user ID"""
        with patch('streamlit.error'), patch('streamlit.info'):
            result = validate_user_id('INVALID', ['TEST001', 'TEST002'])
            self.assertFalse(result)

class TestDataIntegrity(unittest.TestCase):
    """Testy integrity a kvality dat"""
    
    def test_mapping_completeness(self):
        """Test, že jsou všechny mappingy kompletní"""
        # Test arousal mappingu
        expected_arousal = {'nízký', 'střední', 'vysoký', 'Nízký', 'Střední', 'Vysoký'}
        self.assertEqual(set(MAP_AROUSAL.keys()), expected_arousal)
        
        # Test valence mappingu
        expected_valence = {'negativní', 'neutrální', 'pozitivní', 'Negativní', 'Neutrální', 'Pozitivní'}
        self.assertEqual(set(MAP_VALENCE.keys()), expected_valence)
    
    def test_mapping_values(self):
        """Test správnosti mapovacích hodnot"""
        # Arousal hodnoty by měly být 1, 2, 3
        arousal_values = set(MAP_AROUSAL.values())
        self.assertEqual(arousal_values, {1, 2, 3})
        
        # Valence hodnoty by měly být -1, 0, 1
        valence_values = set(MAP_VALENCE.values())
        self.assertEqual(valence_values, {-1, 0, 1})

class TestPerformance(unittest.TestCase):
    """Testy výkonu aplikace"""
    
    def test_large_dataset_performance(self):
        """Test výkonu s velkým datasetem"""
        # Vytvoř velký dataset
        large_data = pd.DataFrame({
            'ID': ['TEST' + str(i).zfill(3) for i in range(1000)],
            'Term': ['slovo'] * 1000,
            'Pos X': np.random.normal(0, 1, 1000),
            'Pos Y': np.random.normal(0, 1, 1000),
            'Pos Z': np.random.normal(0, 1, 1000),
            'First reaction time': np.random.exponential(2, 1000)
        })
        
        baseline_data = pd.DataFrame({
            'Word': ['slovo'],
            'Valence': ['neutrální'],
            'Arousal': ['střední']
        })
        
        # Měř čas zpracování
        import time
        start_time = time.time()
        result = compute_deltas(large_data, baseline_data)
        processing_time = time.time() - start_time
        
        # Processing by měl být rychlý (< 1 sekunda pro 1000 řádků)
        self.assertLess(processing_time, 1.0)
        self.assertEqual(len(result), 1000)

def run_tests():
    """Spuštění všech testů"""
    # Vytvoření test suite
    test_classes = [TestUtils, TestErrorHandler, TestDataIntegrity, TestPerformance]
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # Spuštění testů
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result

if __name__ == '__main__':
    # Mock streamlit pro testy
    sys.modules['streamlit'] = MagicMock()
    
    print("🧪 Spouštím unit testy...")
    result = run_tests()
    
    if result.wasSuccessful():
        print("\n✅ Všechny testy prošly úspěšně!")
    else:
        print(f"\n❌ {len(result.failures)} testů selhalo, {len(result.errors)} chyb")
        for failure in result.failures:
            print(f"FAILURE: {failure[0]}")
            print(failure[1])
        for error in result.errors:
            print(f"ERROR: {error[0]}")
            print(error[1])
