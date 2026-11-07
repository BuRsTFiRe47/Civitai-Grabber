from civitai_grabber.core.links import extract_links, parse_link


def test_model_page_link():
    p = parse_link("https://civitai.com/models/12345/some-slug")
    assert (p.kind, p.model_id, p.version_id) == ("model", 12345, None)


def test_model_page_with_version():
    p = parse_link("https://civitai.com/models/12345/x?modelVersionId=777")
    assert (p.kind, p.model_id, p.version_id) == ("model", 12345, 777)
    assert p.key == "v777"


def test_api_download_link_with_query_and_token():
    p = parse_link("https://civitai.com/api/download/models/9?type=Model&format=SafeTensor&token=abc")
    assert (p.kind, p.version_id) == ("version", 9)


def test_model_versions_link():
    assert parse_link("https://civitai.com/model-versions/42").version_id == 42


def test_other_domains_and_www():
    assert parse_link("https://www.civitai.com/models/1").host == "civitai.com"
    assert parse_link("https://civitai.red/models/2").host == "civitai.red"


def test_rejects_other_sites_and_pages():
    assert parse_link("https://example.com/models/1") is None
    assert parse_link("https://evilcivitai.com/models/1") is None
    assert parse_link("https://civitai.com/user/foo") is None
    assert parse_link("https://civitai.com/images/123") is None


def test_extract_from_messy_clipboard_text():
    text = """
    bak şunlar: https://civitai.com/models/1/a, (https://civitai.com/models/2?modelVersionId=5)
    https://civitai.com/models/1/a
    https://civitai.com/api/download/models/9."
    https://google.com
    """
    links = extract_links(text)
    assert [l.key for l in links] == ["m1", "v5", "v9"]
