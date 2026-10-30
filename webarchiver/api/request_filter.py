"""Which requests a rendered page may make: ad hosts and the egress boundary.

CONN-WEBARCHIVER-WEB-SOURCE-R001. :class:`webarchiver.api.browser.Browser`
aborts every request whose host is a known ad or tracker host, or resolves
outside the public egress boundary.
"""

from __future__ import annotations

import socket
from functools import lru_cache

from scion_sdk.http.egress import egress_ip_is_blocked

__all__ = ["AD_HOST_SUFFIXES", "egress_blocked", "is_ad_host"]

#: Ad and tracker hosts aborted at the network layer (suffix match).
AD_HOST_SUFFIXES = (
    "doubleclick.net",
    "googlesyndication.com",
    "googleadservices.com",
    "google-analytics.com",
    "googletagmanager.com",
    "googletagservices.com",
    "adservice.google.com",
    "amazon-adsystem.com",
    "adnxs.com",
    "adsrvr.org",
    "criteo.com",
    "criteo.net",
    "taboola.com",
    "outbrain.com",
    "scorecardresearch.com",
    "quantserve.com",
    "hotjar.com",
    "facebook.net",
    "connect.facebook.net",
    "ads-twitter.com",
    "rubiconproject.com",
    "pubmatic.com",
    "openx.net",
    "moatads.com",
    "chartbeat.com",
    "segment.io",
    "mixpanel.com",
)


#: Removes fixed/sticky overlays and re-enables scrolling.
def is_ad_host(host: str) -> bool:
    host = host.lower().rstrip(".")
    return any(host == s or host.endswith(f".{s}") for s in AD_HOST_SUFFIXES)


@lru_cache(maxsize=1024)
def _resolve(host: str) -> tuple[str, ...]:
    try:
        infos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except OSError:
        return ()
    return tuple(sorted({str(info[4][0]) for info in infos}))


def egress_blocked(host: str, *, allow_loopback: bool) -> bool:
    """True when ``host`` does not resolve or any address is outside egress."""
    addresses = _resolve(host)
    if not addresses:
        return True
    return any(
        egress_ip_is_blocked(ip, allow_loopback=allow_loopback) for ip in addresses
    )
