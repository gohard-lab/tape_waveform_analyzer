import uuid
import requests
import os
import sys
from functools import lru_cache
from datetime import datetime, timezone
from supabase import create_client, Client

# 🛡️ [SMART HYBRID PATCH] Prevent crashes in non-streamlit execution environments
try:
    import streamlit as st
    from streamlit_javascript import st_javascript
except ModuleNotFoundError:
    st = None
    st_javascript = None


# 🚨 [1. DECORATOR FIX] Replaced @st.cache_resource with standard Python @lru_cache.
# Works natively in BOTH Streamlit Web and Colab/CLI without raising AttributeErrors.
@lru_cache(maxsize=1)
def get_supabase_client() -> Client | None:
    """Fetch Supabase client prioritizing os.environ (Colab/Docker) then st.secrets"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        try:
            if st is not None and hasattr(st, "secrets"):
                url = st.secrets["supabase"]["url"]
                key = st.secrets["supabase"]["key"]
        except Exception:
            pass

    if not url or not key:
        print("⚠️ [Tracker] Supabase credentials missing. Usage logging disabled.")
        return None
    
    return create_client(url, key)


def get_real_client_ip() -> str:
    """Safely extract IP without crashing in pure Python environments"""
    if st is None or not hasattr(st, "context"):
        return "Unknown"
    
    if hasattr(st.context, "headers") and st.context.headers:
        xff = st.context.headers.get("X-Forwarded-For")
        if xff:
            return xff.split(",")[0].strip()

    if hasattr(st, "session_state") and "cached_ip" in st.session_state:
        return st.session_state.cached_ip

    try:
        if st_javascript is not None:
            js_code = "await fetch('https://api.ipify.org?format=json').then(r => r.json()).then(d => d.ip)"
            client_ip = st_javascript(js_code, key="ip_tracker_js")
            if client_ip and client_ip != 0:
                st.session_state.cached_ip = client_ip
                return client_ip
    except Exception:
        pass
        
    return "Unknown"


# 🚨 [2. PREEMPTIVE LANDMINE REMOVAL] Prevent session_state crashes in Colab
def get_or_create_session_id() -> str:
    """Safely get session ID for both Streamlit Web and pure Python Colab runners"""
    if st is None or not hasattr(st, "session_state"):
        if "COLAB_SESSION_ID" not in os.environ:
            os.environ["COLAB_SESSION_ID"] = "colab_" + uuid.uuid4().hex[:12]
        return os.environ["COLAB_SESSION_ID"]

    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = "web_" + uuid.uuid4().hex[:12]
    return st.session_state['session_id']


def log_app_usage(app_name="unknown_app", action="page_view", details=None) -> bool:
    """Universal non-blocking database usage logger"""
    user_agent = "Unknown"
    if st is not None and hasattr(st, "context") and hasattr(st.context, "headers"):
        user_agent = st.context.headers.get("User-Agent", "Unknown")

    ua_str = str(user_agent).lower()

    # Gatekeeper 1: Known infrastructure bots
    bot_keywords = ["github", "curl", "wget", "bot", "uptime", "cron", "polymath", "prerender", "headlesschrome"]
    if any(k in ua_str for k in bot_keywords):
        return False

    if "chrome/124.0.0.0" in ua_str:
        return False

    real_ip = get_real_client_ip()

    # Gatekeeper 2: Pure backend scheduler pings
    if (real_ip == "Unknown" or not real_ip) and (user_agent == "Unknown") and action in ['dashboardTab_opened', 'app_opened']:
        return False

    try:
        client = get_supabase_client()
        if not client:
            return False

        current_session = get_or_create_session_id()
        utc_time = datetime.now(timezone.utc).isoformat()
        
        # Check if running strictly inside Google Colab container
        is_colab_env = "google.colab" in sys.modules

        log_data = {
            "session_id": current_session,
            "app_name": app_name,
            "action": action,
            "timestamp": utc_time,
            "country": "South Korea" if is_colab_env else "Unknown",
            "region": "Gyeonggi-do" if is_colab_env else "Unknown",
            "city": "Namyangju" if is_colab_env else "Unknown",
            "lat": 37.6360 if is_colab_env else 0.0,
            "lon": 127.2165 if is_colab_env else 0.0,
            "ip_address": real_ip,
            "details": details if details else {},
            "user_agent": "Google Colab Python Runtime" if is_colab_env else user_agent
        }
        
        client.table('usage_logs').insert(log_data, returning='minimal').execute()
        return True
    except Exception:
        # Silent failure rule: A logging error must NEVER crash the CEO's main application.
        return False