"""Build the one webarchiver client from settings.

The connector reads the public web and holds no credentials. Its policy knobs
come from settings; loopback and private hosts are refused unless explicitly
allowed for a test or an authorized internal deployment.
"""

from agent_connector_sdk.config import load_config, setting

from .api import ApiClientSystem, FetchPolicy

_client: ApiClientSystem | None = None


def _policy() -> FetchPolicy:
    default = FetchPolicy()
    return FetchPolicy(
        user_agent=str(setting("WEBARCHIVER_USER_AGENT", default.user_agent)),
        max_bytes=int(setting("WEBARCHIVER_MAX_BYTES", default.max_bytes)),
        min_interval_s=float(
            setting("WEBARCHIVER_MIN_INTERVAL_S", default.min_interval_s)
        ),
        timeout_s=float(setting("WEBARCHIVER_TIMEOUT_S", default.timeout_s)),
        obey_robots=bool(setting("WEBARCHIVER_OBEY_ROBOTS", True)),
    )


def get_client() -> ApiClientSystem:
    """The process-wide client; robots and rate state are shared across calls."""
    global _client
    if _client is None:
        load_config()
        private = str(setting("WEBARCHIVER_ALLOWED_PRIVATE_HOSTS", "") or "")
        _client = ApiClientSystem(
            _policy(),
            allow_loopback=bool(setting("WEBARCHIVER_ALLOW_LOOPBACK", False)),
            allowed_private_hosts=tuple(
                h.strip() for h in private.split(",") if h.strip()
            ),
        )
    return _client


def close_client() -> None:
    """Drop the cached client so the next call rebuilds it from settings."""
    global _client
    _client = None
