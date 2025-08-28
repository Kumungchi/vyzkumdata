# performance_monitor.py
import time
import psutil
import streamlit as st
import logging
from functools import wraps
import pandas as pd
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class PerformanceMonitor:
    """Monitor výkonu aplikace"""
    
    def __init__(self):
        self.metrics = []
        self.session_start = time.time()
    
    def log_metric(self, name, value, unit="ms"):
        """Loguje metriku výkonu"""
        metric = {
            'timestamp': datetime.now().isoformat(),
            'name': name,
            'value': value,
            'unit': unit,
            'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024,
            'cpu_percent': psutil.cpu_percent()
        }
        self.metrics.append(metric)
        logger.info(f"PERFORMANCE - {name}: {value}{unit}, Memory: {metric['memory_usage_mb']:.1f}MB")
    
    def time_function(self, func_name):
        """Dekorátor pro měření času funkcí"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000
                    self.log_metric(f"{func_name}_success", execution_time)
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000
                    self.log_metric(f"{func_name}_error", execution_time)
                    raise e
            return wrapper
        return decorator
    
    def get_system_info(self):
        """Získá informace o systému"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            return {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024**3),
            }
        except Exception as e:
            logger.error(f"Chyba při získávání system info: {e}")
            return {}
    
    def show_performance_dashboard(self):
        """Zobrazí performance dashboard v Streamlitu"""
        if st.checkbox("📊 Zobrazit performance dashboard"):
            st.subheader("Performance Monitoring")
            
            # Systémové informace
            sys_info = self.get_system_info()
            if sys_info:
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("CPU", f"{sys_info.get('cpu_percent', 0):.1f}%")
                col2.metric("Paměť", f"{sys_info.get('memory_percent', 0):.1f}%")
                col3.metric("Dostupná RAM", f"{sys_info.get('memory_available_gb', 0):.1f} GB")
                col4.metric("Volné místo", f"{sys_info.get('disk_free_gb', 0):.1f} GB")
            
            # Metriky aplikace
            if self.metrics:
                df_metrics = pd.DataFrame(self.metrics)
                
                # Poslední metriky
                st.subheader("Poslední performance metriky:")
                recent_metrics = df_metrics.tail(10)
                st.dataframe(recent_metrics[['timestamp', 'name', 'value', 'unit', 'memory_usage_mb']])
                
                # Graf času odezvy
                if len(df_metrics) > 1:
                    import plotly.express as px
                    fig = px.line(df_metrics, x='timestamp', y='value', color='name',
                                title="Časy odezvy v čase")
                    st.plotly_chart(fig, use_container_width=True)
    
    def save_metrics_to_file(self, filename="performance_metrics.csv"):
        """Uloží metriky do souboru"""
        if self.metrics:
            try:
                df = pd.DataFrame(self.metrics)
                df.to_csv(filename, index=False)
                logger.info(f"Performance metriky uloženy do {filename}")
            except Exception as e:
                logger.error(f"Chyba při ukládání metrik: {e}")

# Globální instance monitoru
perf_monitor = PerformanceMonitor()

def monitor_memory_usage():
    """Monitoruje paměťové nároky"""
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    
    # Varování při vysokém využití paměti
    if memory_mb > 500:  # 500MB threshold
        logger.warning(f"Vysoké využití paměti: {memory_mb:.1f}MB")
        st.warning(f"⚠️ Vysoké využití paměti: {memory_mb:.1f}MB")
    
    perf_monitor.log_metric("memory_usage", memory_mb, "MB")
    return memory_mb

@st.cache_data
def get_cached_performance_tips():
    """Cached tipy pro optimalizaci výkonu"""
    return {
        'data_loading': 'Používejte @st.cache_data pro cachování dat',
        'large_datasets': 'Pro velké datasety zvažte pagination nebo filtering',
        'plotting': 'Používejte sampling pro velké grafy',
        'memory': 'Pravidelně kontrolujte paměťové nároky',
        'caching': 'Nastavte TTL pro cache aby se data aktualizovala'
    }

def show_performance_tips():
    """Zobrazí tipy pro optimalizaci výkonu"""
    with st.expander("💡 Tipy pro optimalizaci výkonu"):
        tips = get_cached_performance_tips()
        for tip_key, tip_text in tips.items():
            st.markdown(f"- **{tip_key.replace('_', ' ').title()}:** {tip_text}")

def benchmark_data_processing(data_size=1000):
    """Benchmark zpracování dat"""
    start_time = time.time()
    
    # Simulace zpracování dat
    import numpy as np
    data = pd.DataFrame({
        'ID': range(data_size),
        'values': np.random.normal(0, 1, data_size)
    })
    
    # Nějaké zpracování
    data['processed'] = data['values'].rolling(10).mean()
    data_mean = data['processed'].mean()
    
    processing_time = (time.time() - start_time) * 1000
    perf_monitor.log_metric("benchmark_data_processing", processing_time)
    
    return processing_time, len(data)

# Automatické monitorování při importu
if __name__ != "__main__":
    monitor_memory_usage()
