"""
Optional monitoring hooks: Sentry (errors, request timing) and Langfuse (Gemini
call traces).

Everything here is opt-in and fail-safe. A tool stays off unless its keys are
set and Config.MONITORING_ENABLED is true (it is false under SKIP_DB=true, so
tests never send data). A missing package, bad setting or unreachable service
is reported with a [WARN] line and never raises into a request.
"""

import os
import threading

from config import Config

try:
    import sentry_sdk
except ImportError:  # package not installed: monitoring just stays off
    sentry_sdk = None

# Longest a request may wait for traces to be sent before Vercel freezes it
FLUSH_TIMEOUT_SECONDS = 2

_sentry_active = False
_langfuse_active = False


def _traces_sampler(sampling_context):
    """Sample every request except static files."""
    environ = sampling_context.get("wsgi_environ") or {}
    if environ.get("PATH_INFO", "").startswith("/static/"):
        return 0
    try:
        return max(0.0, min(1.0, float(Config.SENTRY_TRACES_SAMPLE_RATE)))
    except (TypeError, ValueError):
        return 1.0


def init_sentry():
    """
    Start Sentry if enabled and a DSN is set. Call before creating the Flask
    app so the Flask integration can hook in.

    Returns:
        True if Sentry is active
    """
    global _sentry_active
    if not (Config.MONITORING_ENABLED and Config.SENTRY_DSN and sentry_sdk):
        return False
    try:
        sentry_sdk.init(
            dsn=Config.SENTRY_DSN,
            environment=Config.MONITORING_ENVIRONMENT,
            release=os.environ.get("VERCEL_GIT_COMMIT_SHA"),
            send_default_pii=False,
            traces_sampler=_traces_sampler,
        )
        _sentry_active = True
    except Exception as err:
        print(f"[WARN] Sentry disabled: {err}")
    return _sentry_active


def get_openai_class():
    """
    Return the OpenAI client class used for Gemini calls. When Langfuse is
    configured, importing langfuse.openai patches the client so each call is
    traced; otherwise this is the plain openai.OpenAI.
    """
    global _langfuse_active
    if (
        Config.MONITORING_ENABLED
        and Config.LANGFUSE_PUBLIC_KEY
        and Config.LANGFUSE_SECRET_KEY
    ):
        try:
            os.environ.setdefault(
                "LANGFUSE_TRACING_ENVIRONMENT", Config.MONITORING_ENVIRONMENT
            )
            from langfuse.openai import OpenAI

            _langfuse_active = True
            return OpenAI
        except Exception as err:
            print(f"[WARN] Langfuse disabled: {err}")
    from openai import OpenAI

    return OpenAI


def langfuse_kwargs(name):
    """
    Extra create() arguments that label a trace in Langfuse. Plain OpenAI
    rejects unknown arguments, so this is empty when Langfuse is off.
    """
    return {"name": name} if _langfuse_active else {}


def capture_exception(exc):
    """Report a handled exception to Sentry. No-op unless Sentry is active."""
    if not _sentry_active:
        return
    try:
        sentry_sdk.capture_exception(exc)
    except Exception:
        pass


def _run_with_timeout(func):
    """Run func in a thread and wait at most FLUSH_TIMEOUT_SECONDS for it."""
    worker = threading.Thread(target=func, daemon=True)
    worker.start()
    worker.join(FLUSH_TIMEOUT_SECONDS)


def flush_sentry():
    """
    Send queued Sentry events before Vercel freezes the function. Only runs on
    Vercel; locally the SDK sends in the background. Never raises.
    """
    if not (_sentry_active and os.environ.get("VERCEL")):
        return
    try:
        sentry_sdk.flush(timeout=FLUSH_TIMEOUT_SECONDS)
    except Exception:
        pass


def flush_langfuse():
    """
    Send queued Langfuse traces before Vercel freezes the function, waiting at
    most FLUSH_TIMEOUT_SECONDS. Only runs on Vercel. Never raises.
    """
    if not (_langfuse_active and os.environ.get("VERCEL")):
        return

    def _flush():
        try:
            from langfuse import get_client

            get_client().flush()
        except Exception:
            pass

    _run_with_timeout(_flush)
