import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from openai import OpenAI

# Configuration via environment variables (set in GitHub Secrets/Vars or .env)
SITE_TITLE = os.getenv("SITE_TITLE", "AutoPulse AI")
SITE_TAGLINE = os.getenv(
    "SITE_TAGLINE", "Daily automated insights on AI, tech, and digital workflows."
)
SITE_NICHE = os.getenv(
    "SITE_NICHE", "AI tools, automation workflows, and practical tech guides"
)
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
BASE_URL = os.getenv("OPENAI_BASE_URL")  # Optional: for Gemini/Groq/OpenRouter compatibility

DATA_FILE = Path("data/posts.json")
DIST_DIR = Path("dist")
POSTS_DIR = DIST_DIR / "posts"

CSS = """
:root {
  --bg: #0f172a;
  --surface: #1e293b;
  --text: #f8fafc;
  --muted: #94a3b8;
  --accent: #38bdf8;
  --border: #334155;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.65;
}
.container {
  max-width: 820px;
  margin: 0 auto;
  padding: 2rem 1.25rem 4rem;
}
header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 1.5rem;
  margin-bottom: 2rem;
}
header h1 {
  margin: 0;
  font-size: 2rem;
  letter-spacing: -0.02em;
}
header h1 a {
  color: var(--text);
  text-decoration: none;
}
header p {
  margin: 0.4rem 0 0;
  color: var(--muted);
}
.grid {
  display: grid;
  gap: 1.25rem;
}
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 1.35rem;
  transition: border-color 0.2s ease;
}
.card:hover {
  border-color: var(--accent);
}
.meta {
  font-size: 0.85rem;
  color: var(--accent);
  margin-bottom: 0.4rem;
}
.card h2 {
  margin: 0 0 0.5rem;
  font-size: 1.3rem;
}
.card h2 a {
  color: var(--text);
  text-decoration: none;
}
.card p {
  margin: 0;
  color: var(--muted);
}
article h1 {
  font-size: 2rem;
  line-height: 1.25;
  margin-bottom: 0.5rem;
}
article h2 {
  margin-top: 2rem;
  font-size: 1.35rem;
  color: var(--accent);
}
article p {
  color: #e2e8f0;
  margin: 0.9rem 0;
}
.back-link {
  display: inline-block;
  margin-bottom: 1.5rem;
  color: var(--accent);
  text-decoration: none;
  font-size: 0.95rem;
}
footer {
  margin-top: 3rem;
  padding-top: 1.25rem;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.85rem;
}
""".strip()


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or f"post-{int(datetime.now(timezone.utc).timestamp())}"


def load_posts() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def save_posts(posts: list[dict]) -> None:
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")


def generate_post(existing_titles: list[str]) -> dict:
    client = OpenAI(base_url=BASE_URL) if BASE_URL else OpenAI()
    recent_list = "\n".join(f"- {t}" for t in existing_titles[:25]) or "None yet."

    prompt = f"""
You are an editor for a website about: {SITE_NICHE}.
Write one fresh, practical, well-structured article that does NOT repeat any of these existing titles:
{recent_list}

Return valid JSON only with this exact schema:
{{
  "title": "Clear, engaging article title",
  "category": "One short category tag (e.g. Automation, AI Tools, Guide)",
  "summary": "2-sentence summary for the homepage card.",
  "sections": [
    {{
      "heading": "Section heading",
      "paragraphs": ["Paragraph 1...", "Paragraph 2..."]
    }}
  ]
}}
Include 3 to 4 sections with concrete, useful advice.
""".strip()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You output strictly valid JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )

    payload = json.loads(response.choices[0].message.content)
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    slug = f"{date_str}-{slugify(payload['title'])}"

    return {
        "title": payload["title"],
        "slug": slug,
        "category": payload.get("category", "AI"),
        "summary": payload["summary"],
        "date": date_str,
        "sections": payload.get("sections", []),
    }


def render_page(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html.escape(title)} | {html.escape(SITE_TITLE)}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="container">
    <header>
      <h1><a href="/">{html.escape(SITE_TITLE)}</a></h1>
      <p>{html.escape(SITE_TAGLINE)}</p>
    </header>
    {body_html}
    <footer>
      Automated AI Publishing Pipeline &bull; Updated {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    </footer>
  </div>
</body>
</html>
"""


def build_site(posts: list[dict]) -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    cards_html = []
    for post in posts:
        post_url = f"/posts/{html.escape(post['slug'])}.html"
        cards_html.append(
            f"""
            <div class="card">
              <div class="meta">{html.escape(post['date'])} &bull; {html.escape(post['category'])}</div>
              <h2><a href="{post_url}">{html.escape(post['title'])}</a></h2>
              <p>{html.escape(post['summary'])}</p>
            </div>
            """
        )

        sections_html = []
        for sec in post.get("sections", []):
            paras = "".join(f"<p>{html.escape(p)}</p>" for p in sec.get("paragraphs", []))
            sections_html.append(f"<h2>{html.escape(sec.get('heading', ''))}</h2>{paras}")

        article_html = f"""
        <a class="back-link" href="/">&larr; Back to all articles</a>
        <article>
          <div class="meta">{html.escape(post['date'])} &bull; {html.escape(post['category'])}</div>
          <h1>{html.escape(post['title'])}</h1>
          <p><em>{html.escape(post['summary'])}</em></p>
          {''.join(sections_html)}
        </article>
        """
        (POSTS_DIR / f"{post['slug']}.html").write_text(
            render_page(post["title"], article_html), encoding="utf-8"
        )

    index_body = f'<div class="grid">{"".join(cards_html)}</div>'
    (DIST_DIR / "index.html").write_text(
        render_page("Home", index_body), encoding="utf-8"
    )


def main() -> None:
    posts = load_posts()
    new_post = generate_post([p["title"] for p in posts])
    posts.insert(0, new_post)
    save_posts(posts)
    build_site(posts)
    print(f"Published: {new_post['title']} ({new_post['slug']}.html)")


if __name__ == "__main__":
    main()
