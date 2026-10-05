from __future__ import annotations
import json, os, sys
from pathlib import Path
import anthropic, feedparser, tweepy

RSS_FEEDS = ["https://rss.itmedia.co.jp/rss/2.0/eetimes.xml"]
CLAUDE_MODEL = "claude-sonnet-4-6"
STATE_FILE = Path(__file__).parent / "state.json"
MAX_HISTORY = 200

X_API_KEY             = os.environ["X_API_KEY"]
X_API_SECRET          = os.environ["X_API_SECRET"]
X_ACCESS_TOKEN        = os.environ["X_ACCESS_TOKEN"]
X_ACCESS_TOKEN_SECRET = os.environ["X_ACCESS_TOKEN_SECRET"]
ANTHROPIC_API_KEY     = os.environ["ANTHROPIC_API_KEY"]

def load_posted_links():
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else []

def save_posted_links(links):
    STATE_FILE.write_text(json.dumps(links[-MAX_HISTORY:], ensure_ascii=False, indent=2), encoding="utf-8")

def fetch_unposted_entry(posted_links):
    for feed_url in RSS_FEEDS:
        for entry in feedparser.parse(feed_url).entries:
            link = entry.get("link", "")
            if link and link not in posted_links:
                return entry
    return None

def summarize_with_claude(title, summary_source):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""以下は半導体業界のニュース記事の情報です。X(旧Twitter)に投稿するための短い日本語の紹介文を1つ作成してください。

# 制約
- 80文字以内（句読点を含む）
- 記事内容に忠実な紹介文にすること
- 文末に半角スペースを挟んでハッシュタグ「#半導体」を1つだけ付ける
- 紹介文の本文だけを出力すること

# 記事タイトル
{title}

# 記事概要
{summary_source}
"""
    msg = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY).messages.create(
        model=CLAUDE_MODEL, max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text.strip()

def build_tweet_text(body, link):
    text = f"{body}\n{link}"
    while sum(2 if ord(c) > 0x2FFF else 1 for c in text) > 270 and len(body) > 10:
        body = body[:-5].rstrip()
        text = f"{body}\n{link}"
    return text

def post_to_x(text):
    tweepy.Client(
        consumer_key=X_API_KEY, consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN, access_token_secret=X_ACCESS_TOKEN_SECRET
    ).create_tweet(text=text)

def main():
    posted_links = load_posted_links()
    entry = fetch_unposted_entry(posted_links)
    if entry is None:
        print("新しい未投稿記事が見つかりませんでした。スキップします。")
        return
    title = entry.get("title", "")
    body = summarize_with_claude(title, entry.get("summary", title))
    tweet_text = build_tweet_text(body, entry.get("link", ""))
    post_to_x(tweet_text)
    print("投稿しました:\n" + tweet_text)
    posted_links.append(entry.get("link", ""))
    save_posted_links(posted_links)

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"エラー: {exc}", file=sys.stderr)
        sys.exit(1)
