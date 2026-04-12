# =============================================
# Custom Seahub Settings (managed by blueprint)
# =============================================
# These settings are appended to seahub_settings.py
# by entrypoint.sh on container start.

# --- Metadata Server ---
ENABLE_METADATA_MANAGEMENT = True
METADATA_SERVER_URL = 'http://seafile-md-server:8084'

# --- Thumbnail Server ---
ENABLE_VIDEO_THUMBNAIL = True
