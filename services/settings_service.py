import time
from datetime import datetime
from utils.supabase_client import supabase
from utils.logging_helper import logger

class SettingsService:
    def __init__(self, ttl_seconds=30):
        self.cache = {}
        self.ttl = ttl_seconds
        self.default_settings = {
            "active_model": "MobileNetV2",
            "auto_run_ai": "false",
            "verbose_logging": "false",
            "future_flags": "{}"
        }

    def get_setting(self, key: str) -> str:
        """Get a setting by key, checking the cache first."""
        now = time.time()
        if key in self.cache:
            val, expiry = self.cache[key]
            if now < expiry:
                return val
        
        try:
            res = supabase.table("system_settings").select("setting_value").eq("setting_key", key).limit(1).execute()
            if res.data and len(res.data) > 0:
                val = res.data[0].get("setting_value")
            else:
                val = self.default_settings.get(key, "")
                # Auto-seed the database
                supabase.table("system_settings").insert({"setting_key": key, "setting_value": val}).execute()
        except Exception as e:
            logger.error(f"[SettingsService] Error reading setting '{key}': {e}", exc_info=True)
            val = self.default_settings.get(key, "")
            
        self.cache[key] = (val, now + self.ttl)
        return val

    def set_setting(self, key: str, value: str) -> bool:
        """Update a setting value in the database and invalidate the cache."""
        try:
            res = supabase.table("system_settings").select("id").eq("setting_key", key).limit(1).execute()
            now_iso = datetime.utcnow().isoformat() + "Z"
            if res.data and len(res.data) > 0:
                supabase.table("system_settings").update({
                    "setting_value": value,
                    "updated_at": now_iso
                }).eq("setting_key", key).execute()
            else:
                supabase.table("system_settings").insert({
                    "setting_key": key,
                    "setting_value": value,
                    "updated_at": now_iso
                }).execute()
            
            # Invalidate cache
            if key in self.cache:
                del self.cache[key]
            return True
        except Exception as e:
            logger.error(f"[SettingsService] Error writing setting '{key}': {e}", exc_info=True)
            return False

    def get_all_settings(self) -> dict:
        """Fetch all settings from the database, seeding defaults if missing."""
        try:
            res = supabase.table("system_settings").select("*").execute()
            db_settings = {row["setting_key"]: row["setting_value"] for row in res.data}
            
            # Auto-seed any missing keys
            for key, default_val in self.default_settings.items():
                if key not in db_settings:
                    db_settings[key] = default_val
                    supabase.table("system_settings").insert({
                        "setting_key": key,
                        "setting_value": default_val
                    }).execute()
            
            now = time.time()
            for k, v in db_settings.items():
                self.cache[k] = (v, now + self.ttl)
            return db_settings
        except Exception as e:
            logger.error(f"[SettingsService] Error loading all settings: {e}", exc_info=True)
            return self.default_settings

    def invalidate_cache(self, key: str = None):
        """Invalidate the cache for a specific key, or all keys if none is specified."""
        if key:
            if key in self.cache:
                del self.cache[key]
        else:
            self.cache.clear()

settings_service = SettingsService()

