"""
半導体ニュースを要約してX(旧Twitter)に自動投稿する日次ボット。

処理の流れ:
  1. RSSフィードから最新ニュースを取得する
  2. まだ投稿していない記事を1件選ぶ
  3. Anthropic API (Claude) で短い紹介文を生成する
  4. X API (v2) に投稿する
  5. 投稿済みリンクを state.json に記録する（重複投稿を防ぐため）

このファイルはGitHub Actionsから1日1回実行されることを想定しています。
詳しいセットアップ方法はREADME.mdを参照してください。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anthropic
import feedparser
import tweepy

# ====== 設定（必要に応じて編集してください） ======

# 監視するRSSフィードのURL一覧。
# デフォルトは半導体専門メディア「EE Times Japan」の確認済みフィードです。
# 他のニュースサイトを追加したい場合は、そのサイトで「RSSフィード」の
# ページを探し、URLをこのリストに追加してください。
RSS_FEEDS = [
    "https://rss.itmedia.co.jp/rss/2.0/eetimes.xml",
]

# Claudeに渡すモデル名
CLAUDE_MODEL = "claude-sonnet-4-6"

STATE_FILE = Path(__file__).parent / "state.json"
MAX_HISTORY = 200  # 重複チェック用に保存しておく投稿済みリンクの最大件数

# ====== 環境変数（GitHub Secretsから渡される） ======

X_API_KEY = os.environ["X_API_KEY"]
X_API_SECRET = os.environ["X_API_SECRET"]
X_ACCESS_TOKEN = os.environ["X_ACCESS_TOKEN"]
X_ACCESS_TOKEN_SECRET = os.environ["X_ACCESS_TOKEN_SECRET"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]


def load_posted_links() -> list[str]:
    """過去に投稿したリンクの一覧を読み込む。"""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return []


def save_posted_links(links: list[str]) -> None:
    """投稿済みリンクの一覧を保存する（直近MAX_HISTORY件のみ残す）。"""
    trimmed = links[-MAX_HISTORY:]
    STATE_FILE.write_text(
        json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fetch_unposted_entry(posted_links: list[str]):
    """まだ投稿していない最新の記事を1件返す。見つからなければNoneを返す。"""
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            link = entry.get("link", "")
            if link and link not in posted_links:
                return entry
    return None


def weighted_length(text: str) -> int:
    """Xの文字数カウント方式を簡易的に再現する。

    日本語などの全角文字は2文字分、半角の英数字等は1文字分として
    カウントされる（Xの実際の仕様に基づく簡易版）。
    """
    length = 0
    for ch in text:
        length += 2 if ord(ch) > 0x2FFF else 1
    return length


def summarize_with_claude(title: str, summary_source: str) -> str:
    """Claude APIで短い日本語の紹介文を生成する。"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""以下は半導体業界のニュース記事の情報です。これをもとに、
X(旧Twitter)に投稿するための短い日本語の紹介文を1つ作成してください。

# 制約
- 80文字以内（句読点を含む）
- 誇張せず、記事内容に忠実な紹介文にすること（記事にない情報を加えない）
- 絵文字は使っても使わなくても良いが、使う場合は1つまで
- 文末に半角スペースを挟んでハッシュタグ「#半導体」を1つだけ付ける
- 紹介文の本文だけを出力すること（前置き・説明・引用符は一切含めない）

# 記事タイトル
{title}

# 記事概要
{summary_source}
"""
    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


def build_tweet_text(body: str, link: str) -> str:
    """本文とリンクを結合し、文字数制限を超えないように調整する。"""
    text = f"{body}\n{link}"
    # 想定より長くなった場合の安全策として本文を少しずつ削る
    while weighted_length(text) > 270 and len(body) > 10:
        body = body[:-5].rstrip()
        text = f"{body}\n{link}"
    return text


def post_to_x(text: str) -> None:
    """X API (v2) にテキストを投稿する。"""
    client = tweepy.Client(
        consumer_key=X_API_KEY,
        consumer_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    client.create_tweet(text=text)


def main() -> None:
    posted_links = load_posted_links()
    entry = fetch_unposted_entry(posted_links)

    if entry is None:
        print("新しい未投稿記事が見つかりませんでした。今回は投稿をスキップします。")
        return

    title = entry.get("title", "")
    summary_source = entry.get("summary", title)
    link = entry.get("link", "")

    body = summarize_with_claude(title, summary_source)
    tweet_text = build_tweet_text(body, link)

    post_to_x(tweet_text)
    print("投稿しました:")
    print(tweet_text)

    posted_links.append(link)
    save_posted_links(posted_links)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        print(f"エラーが発生しました: {exc}", file=sys.stderr)
        sys.exit(1)
