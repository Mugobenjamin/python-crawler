from app.url_utils import dedupe_key, is_in_scope, normalize_url


def test_normalize_url_removes_fragment_and_tracking_params():
    url = "https://developers.google.com/search/docs/appearance/site?utm_source=foo&x=1#section"
    normalized = normalize_url(url)
    assert normalized == "https://developers.google.com/search/docs/appearance/site?x=1"


def test_is_in_scope_checks_allowed_domains():
    assert is_in_scope("https://developers.google.com/search/docs", ["developers.google.com"])
    assert not is_in_scope("https://example.com", ["developers.google.com"])


def test_dedupe_key_is_stable():
    assert dedupe_key("https://developers.google.com/search/docs?utm_source=a") == dedupe_key("https://developers.google.com/search/docs")
