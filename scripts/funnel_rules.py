"""Channel rules and closed-funnel rules.

The channel rules are explicit. They are a simplified grouping, separate from
GA4's Default Channel Group, which also uses Google's paid-ads integrations
and a longer set of rules. `<Other>` and `(data deleted)` become
`(obfuscated)`. That label is a hole in the public sample.
"""

from urllib.parse import urlsplit

# First matching rule wins.
# Match a whole host or source label. "x.com" must not match "box.com",
# and "t.co" must not match an unrelated host that merely contains those letters.
SOCIAL_TOKENS = (
    "facebook.com",
    "facebook",
    "instagram.com",
    "instagram",
    "twitter.com",
    "twitter",
    "t.co",
    "x.com",
    "linkedin.com",
    "linkedin",
    "pinterest.com",
    "pinterest",
    "youtube.com",
    "youtube",
    "youtu.be",
    "reddit.com",
    "reddit",
    "tiktok.com",
    "tiktok",
    "snapchat.com",
    "snapchat",
    "tumblr.com",
    "tumblr",
    "quora.com",
    "quora",
)

SEARCH_TOKENS = (
    "google",
    "bing.com",
    "bing",
    "yahoo.com",
    "yahoo",
    "duckduckgo.com",
    "duckduckgo",
    "baidu.com",
    "baidu",
    "ecosia.org",
    "ecosia",
    "yandex.com",
    "yandex",
    "naver.com",
    "naver",
    "ask.com",
    "aol.com",
    "aol",
)

# Google hosts that are not search-results pages.
NOT_SEARCH_HOSTS = (
    "mail.google.com",
    "accounts.google.com",
    "pay.google.com",
    "payments.google.com",
    "docs.google.com",
    "drive.google.com",
    "calendar.google.com",
)

# Placeholders in Google's obfuscated sample. They are not campaign names.
PLACEHOLDERS = {"<other>", "(data deleted)"}

PAID_MEDIUMS = {"cpc", "ppc", "paidsearch", "paid_search"}
DISPLAY_MEDIUMS = {"display", "cpm", "banner"}
SOCIAL_MEDIUMS = {"social", "social-network", "social-media", "sm"}
PAID_SOCIAL_MEDIUMS = {"paid-social", "paidsocial", "paid_social"}

# Tie-break when two funnel events share a timestamp: a view counts as
# happening before the cart, and the cart before the purchase.
STEP_RANK = {
    "view_item": 0,
    "add_to_cart": 1,
    "begin_checkout": 2,
    "purchase": 3,
}


def _clean(value):
    if value is None:
        return ""
    return str(value).strip()


def _low(value):
    return _clean(value).lower()


def _host_key(text):
    """Lowercase host or source label, without www or a path."""
    raw = _low(text)
    if not raw:
        return ""
    raw = raw.replace("https://", "").replace("http://", "")
    raw = raw.split("/")[0].split("?")[0].split(":")[0]
    if raw.startswith("www."):
        raw = raw[4:]
    return raw


def _matches_token(text, tokens):
    host = _host_key(text)
    if not host:
        return False
    for token in tokens:
        token = token.lower().strip(".")
        if host == token or host.endswith("." + token):
            return True
        # GA often stores a bare source such as "google" or "facebook".
        if "." not in token and (host == token or host.startswith(token + ".")):
            return True
    return False


def channel_group(source, medium):
    """Map one source/medium pair to a simplified channel group.

    Returns "(not set)" when both sides are empty. "Direct" is only returned
    when the source is (direct) and the medium is empty, (none), or (not set).
    """
    source_l = _low(source)
    medium_l = _low(medium)
    blank = {"", "(not set)", "null", "none", "(none)"}
    source_placeholder = source_l in PLACEHOLDERS
    medium_placeholder = medium_l in PLACEHOLDERS

    # Both sides hidden, or the medium hidden, so the usual rules would guess.
    if (source_placeholder and medium_placeholder) or medium_placeholder:
        return "(obfuscated)"
    if source_placeholder and medium_l in blank:
        return "(obfuscated)"

    if source_l in {"", "(not set)", "null"} and medium_l in {"", "(not set)", "null"}:
        return "(not set)"
    if source_l == "(direct)" and medium_l in {"(none)", "(not set)", "", "none"}:
        return "Direct"
    if medium_l == "organic":
        return "Organic Search"
    if medium_l in PAID_SOCIAL_MEDIUMS or (
        medium_l in PAID_MEDIUMS and _matches_token(source_l, SOCIAL_TOKENS)
    ):
        return "Paid Social"
    if medium_l in PAID_MEDIUMS:
        return "Paid Search"
    if medium_l in DISPLAY_MEDIUMS:
        return "Display"
    if medium_l == "email":
        return "Email"
    if medium_l == "affiliate":
        return "Affiliates"
    if medium_l in SOCIAL_MEDIUMS or (
        medium_l == "referral" and _matches_token(source_l, SOCIAL_TOKENS)
    ):
        return "Organic Social"
    if medium_l == "referral":
        return "Referral"
    if source_l in blank and medium_l in blank:
        return "(not set)"
    return "Other"


def referrer_host(url):
    """Hostname of a referrer URL, without a leading www., or ""."""
    text = _clean(url)
    if not text or text.lower() in {"(not set)", "null"}:
        return ""
    if "://" not in text:
        text = "http://" + text
    host = urlsplit(text).hostname or ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def is_internal_host(host):
    host = _low(host)
    return host == "googlemerchandisestore.com" or host.endswith(
        ".googlemerchandisestore.com"
    )


def channel_from_referrer(host):
    """Classify an external referrer when the event has no source/medium."""
    host = _host_key(host)
    if not host or is_internal_host(host):
        return "(not set)"
    if host in NOT_SEARCH_HOSTS or any(host.endswith("." + item) for item in NOT_SEARCH_HOSTS):
        return "Referral"
    if _matches_token(host, SEARCH_TOKENS):
        return "Organic Search"
    if _matches_token(host, SOCIAL_TOKENS):
        return "Organic Social"
    return "Referral"


def page_path(url):
    """Path only, so query strings do not split one page into many rows.

    `?gclid=` and `?utm_` parameters are stripped on purpose. The homepage
    is stored as `/`.
    """
    text = _clean(url)
    if not text or text.lower() in {"(not set)", "null"}:
        return "(not set)"
    if "://" not in text:
        text = "http://" + text
    path = urlsplit(text).path or "/"
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return path or "/"


def closed_step_flags(event_names_in_order):
    """Closed funnel flags for one session.

    `event_names_in_order` must already be sorted by time, with STEP_RANK
    breaking ties. Returns (saw_view, closed_cart, closed_purchase).

    closed_cart is true only when a view_item happens at or before an
    add_to_cart. closed_purchase also requires the purchase at or after
    that cart. A purchase with no earlier product view in the same session
    is an open-funnel purchase, not a closed one.
    """
    saw_view = False
    closed_cart = False
    closed_purchase = False
    for name in event_names_in_order:
        if name == "view_item":
            saw_view = True
        elif name == "add_to_cart" and saw_view:
            closed_cart = True
        elif name == "purchase" and closed_cart:
            closed_purchase = True
    return saw_view, closed_cart, closed_purchase
