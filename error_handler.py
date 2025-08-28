# error_handler.py
import streamlit as st
import pandas as pd
import logging
from typing import Optional, Tuple, Any
import traceback

# Nastavení loggingu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DataValidationError(Exception):
    """Vlastní výjimka pro chyby validace dat"""
    pass

class UserNotFoundError(Exception):
    """Vlastní výjimka pro nenalezení uživatele"""
    pass

def safe_read_csv(file_path: str, sep: str = ",", **kwargs) -> Optional[pd.DataFrame]:
    """Bezpečné načítání CSV souborů s error handlingem"""
    try:
        df = pd.read_csv(file_path, sep=sep, **kwargs)
        logger.info(f"Úspěšně načten soubor: {file_path}, tvar: {df.shape}")
        return df
    except FileNotFoundError:
        logger.error(f"Soubor nenalezen: {file_path}")
        st.error(f"🚫 **Soubor nenalezen:** `{file_path}`")
        return None
    except pd.errors.EmptyDataError:
        logger.error(f"Prázdný soubor: {file_path}")
        st.error(f"🚫 **Prázdný soubor:** `{file_path}`")
        return None
    except pd.errors.ParserError as e:
        logger.error(f"Chyba parsování souboru {file_path}: {e}")
        st.error(f"🚫 **Chyba formátu souboru:** `{file_path}`\nDetaily: {e}")
        return None
    except Exception as e:
        logger.error(f"Neočekávaná chyba při načítání {file_path}: {e}")
        st.error(f"🚫 **Neočekávaná chyba:** {e}")
        return None

def validate_data_structure(df: pd.DataFrame, required_columns: list, data_name: str) -> bool:
    """Validuje strukturu DataFrame"""
    try:
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            logger.error(f"Chybí sloupce v {data_name}: {missing_cols}")
            st.error(f"🚫 **Chybí sloupce v {data_name}:** {missing_cols}")
            st.info(f"**Dostupné sloupce:** {list(df.columns)}")
            return False
        
        # Kontrola prázdnosti
        if df.empty:
            logger.error(f"Prázdný dataset: {data_name}")
            st.error(f"🚫 **Prázdný dataset:** {data_name}")
            return False
            
        logger.info(f"Validace {data_name} úspěšná")
        return True
    except Exception as e:
        logger.error(f"Chyba validace {data_name}: {e}")
        st.error(f"🚫 **Chyba validace {data_name}:** {e}")
        return False

def safe_numeric_conversion(df: pd.DataFrame, numeric_columns: list) -> pd.DataFrame:
    """Bezpečná konverze sloupců na numerické hodnoty"""
    try:
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                nan_count = df[col].isna().sum()
                if nan_count > 0:
                    logger.warning(f"Konverze {col}: {nan_count} hodnot převedeno na NaN")
        return df
    except Exception as e:
        logger.error(f"Chyba při konverzi numerických hodnot: {e}")
        st.warning(f"⚠️ **Varování:** Některé numerické hodnoty se nepodařilo převést: {e}")
        return df

def validate_user_id(user_id: str, available_ids: list) -> bool:
    """Validace uživatelského ID"""
    try:
        if not user_id:
            logger.error("ID uživatele je prázdné")
            st.error("🚫 **Chyba přístupu:** ID uživatele není zadáno")
            st.info("**Jak získat přístup k vašemu reportu:**")
            st.markdown("""
            - Použijte osobní odkaz, který jste obdrželi od organizátorů studie
            - Správný formát URL: `?ID=vase_id`
            - Každý účastník má unikátní ID pro přístup pouze ke svým výsledkům
            """)
            st.markdown("**🔒 Bezpečnost:** Výsledky jiných účastníků nejsou přístupné.")
            st.markdown("**❓ Nemáte svůj odkaz?** Kontaktujte organizátory studie.")
            return False
            
        if str(user_id) not in [str(id) for id in available_ids]:
            logger.error(f"Neplatné ID uživatele: {user_id}")
            st.error(f"🚫 **ID '{user_id}' nebylo nalezeno**")
            st.error("**Možné příčiny:**")
            st.markdown("""
            - ID bylo zadáno nesprávně (zkontrolujte překlepy)
            - Používáte zastaralý nebo neplatný odkaz
            - Vaše data ještě nebyla zpracována
            """)
            st.markdown("**🔧 Co dělat:**")
            st.markdown("""
            - Zkontrolujte správnost vašeho osobního odkazu
            - Kontaktujte organizátory studie s vaším ID
            - Ověřte, že používáte nejnovější odkaz
            """)
            return False
            
        logger.info(f"Validace ID {user_id} úspěšná")
        return True
    except Exception as e:
        logger.error(f"Chyba při validaci ID {user_id}: {e}")
        st.error(f"🚫 **Chyba validace ID:** {e}")
        return False

def handle_exception(func):
    """Dekorátor pro globální error handling"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except UserNotFoundError as e:
            logger.error(f"Uživatel nenalezen: {e}")
            st.error(f"🚫 **Uživatel nenalezen:** {e}")
            st.stop()
        except DataValidationError as e:
            logger.error(f"Chyba validace dat: {e}")
            st.error(f"🚫 **Chyba dat:** {e}")
            st.stop()
        except Exception as e:
            logger.error(f"Neočekávaná chyba v {func.__name__}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            st.error("🚫 **Nastala neočekávaná chyba**")
            st.error("Kontaktujte prosím podporu s následujícími detaily:")
            st.code(f"Chyba: {type(e).__name__}: {e}")
            if st.checkbox("Zobrazit technické detaily"):
                st.code(traceback.format_exc())
            st.stop()
    return wrapper

def log_user_activity(user_id: str, action: str, details: str = ""):
    """Logování aktivit uživatelů"""
    try:
        logger.info(f"USER_ACTIVITY - ID: {user_id}, Action: {action}, Details: {details}")
    except Exception as e:
        logger.error(f"Chyba při logování aktivity: {e}")
