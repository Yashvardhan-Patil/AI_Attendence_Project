import os
from supabase import create_client, Client

# Try to load env variables from a .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# Fallback to streamlit secrets if running under Streamlit
if not url or not key:
    try:
        import streamlit as st
        url = url or st.secrets.get("SUPABASE_URL") or st.secrets.get("SUPABSE_URL")
        key = key or st.secrets.get("SUPABASE_KEY") or st.secrets.get("SUPABSE_KEY")
    except Exception:
        pass

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be set.")

supabase: Client = create_client(url, key)
