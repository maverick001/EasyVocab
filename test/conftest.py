"""
Shared pytest setup.

SKIP_DB=true also switches off Sentry and Langfuse (see Config.MONITORING_ENABLED),
so no test, current or future, can send monitoring data even if .env has real keys.
Set here so it applies before any test module imports the app.
"""

import os

os.environ.setdefault('SKIP_DB', 'true')
