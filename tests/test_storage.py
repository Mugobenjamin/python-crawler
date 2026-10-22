from app.extractor import extract_page


def test_main_content_extraction_keeps_text_only():
    html = """
    <html>
      <head>
        <title>SEO basics</title>
        <meta name="description" content="Learn SEO basics">
        <link rel="canonical" href="https://developers.google.com/search/docs/fundamentals" />
      </head>
      <body>
        <nav>Menu</nav>
        <main>
          <h1>SEO basics</h1>
          <h2>Why it matters</h2>
          <p>SEO helps people find information.</p>
          <ul><li>Use clear titles</li><li>Write useful descriptions</li></ul>
        </main>
      </body>
    </html>
    """
    record = extract_page("https://developers.google.com/search/docs/fundamentals", html, object())
    assert record["title"] == "SEO basics"
    assert record["canonical_url"] == "https://developers.google.com/search/docs/fundamentals"
    assert "SEO helps people find information." in record["main_content"]
    assert "Menu" not in record["main_content"]
