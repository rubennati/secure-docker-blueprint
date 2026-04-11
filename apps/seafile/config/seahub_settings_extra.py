# =============================================
# Seahub Extra Settings
# =============================================
# Append these lines to:
#   ./volumes/seafile-data/seafile/conf/seahub_settings.py
#
# This file is a REFERENCE, not auto-applied.
# After first start of Seafile, edit seahub_settings.py
# directly in the volume.
# =============================================

# --- OnlyOffice Integration ---
# Requires core/onlyoffice to be running.
# Replace the host and JWT secret with your values.
#
# ENABLE_ONLYOFFICE = True
# ONLYOFFICE_APIJS_URL = 'https://office.example.com/web-apps/apps/api/documents/api.js'
# ONLYOFFICE_JWT_SECRET = '<content of core/onlyoffice/secrets/jwt_secret.txt>'
# ONLYOFFICE_FILE_EXTENSION = ('doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'odt', 'fodt', 'odp', 'fodp', 'ods', 'fods', 'ppsx', 'pps', 'csv')
# ONLYOFFICE_EDIT_FILE_EXTENSION = ('docx', 'pptx', 'xlsx', 'csv')

# --- Video Thumbnails ---
# Only needed if thumbnail-server.yml is enabled.
#
# ENABLE_VIDEO_THUMBNAIL = True
