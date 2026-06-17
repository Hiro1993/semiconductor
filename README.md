# 半導体ニュース自動投稿Xボット

半導体関連のRSSニュースをAI(Claude)が要約し、毎日決まった時刻にX(旧Twitter)へ
自動投稿するボットです。GitHub Actionsを使って動かすため、サーバーやPCを
常時起動しておく必要はありません。

## 仕組み

1. GitHub Actionsが毎日決まった時刻にスクリプトを実行する
2. スクリプトがRSSフィード（デフォルトはEE Times Japan）から最新記事を取得する
3. まだ投稿していない記事をAnthropic API (Claude) に渡し、短い紹介文を生成する
4. 生成した文章を記事リンクと一緒にXへ投稿する
5. 投稿した記事のリンクを `state.json` に記録し、重複投稿を防ぐ

## 必要なもの

- GitHubアカウント（無料）
- X（旧Twitter）の開発者アカウントとAPIキー
- Anthropic APIキー

## セットアップ手順

### 1. このフォルダをGitHubリポジトリにする

1. GitHubで新しいリポジトリを作成する（Public/Privateどちらでも可）
2. このフォルダの中身（`bot.py`、`requirements.txt`、`state.json`、
   `.github/workflows/post.yml`）をそのリポジトリにアップロードする
   （GitHubの「Add file」→「Upload files」からドラッグ&ドロップでもOK）

### 2. X APIキーを取得する

1. [X Developer Portal](https://developer.x.com/) にアクセスし、開発者アカウントを作成する
2. 新しいProject／Appを作成する
3. Appの設定で **User authentication settings** を有効にし、
   権限を「Read and write」にする（投稿のために書き込み権限が必須）
4. 以下の4つの値を取得する
   - API Key（Consumer Key）
   - API Key Secret（Consumer Secret）
   - Access Token
   - Access Token Secret
5. 2026年2月以降、X APIは従量課金制になっています。Developer Portal上で
   最低$5程度のクレジットをチャージしてください（新規アカウントには$10分の
   クレジットが付与されるため、当面はそれだけで動作確認できます）。
   投稿1件あたり約$0.01なので、1日1回の投稿なら月100円もかかりません。

### 3. Anthropic APIキーを取得する

1. [Anthropic Console](https://console.anthropic.com/) にアクセスしてアカウントを作成する
2. 「API Keys」からキーを発行する
3. 利用には別途クレジットの購入が必要です（こちらも少額のチャージで長期間使えます）

### 4. GitHubリポジトリにAPIキーを登録する

リポジトリの **Settings → Secrets and variables → Actions → New repository secret**
から、以下の5つを登録してください（名前は完全に一致させること）。

| Secret名 | 値 |
|---|---|
| `X_API_KEY` | XのAPI Key |
| `X_API_SECRET` | XのAPI Key Secret |
| `X_ACCESS_TOKEN` | XのAccess Token |
| `X_ACCESS_TOKEN_SECRET` | XのAccess Token Secret |
| `ANTHROPIC_API_KEY` | Anthropicで取得したAPIキー |

### 5. 動作確認する

1. リポジトリの **Actions** タブを開く
2. 「Daily Semiconductor News Bot」を選択し、**Run workflow** ボタンで手動実行する
3. 実行ログを確認し、エラーが出ていないか、実際にXに投稿されたかを確認する

うまく投稿できれば、あとは `cron` で指定した時刻に毎日自動で実行されます。

## カスタマイズ方法

- **投稿時刻を変える**: `.github/workflows/post.yml` の `cron` の値を編集する
  （GitHub Actionsの時刻はUTCのため、日本時間から9時間引いた値を指定する）
- **情報源を増やす・変える**: `bot.py` 内の `RSS_FEEDS` リストにURLを追加する。
  各ニュースサイトのフッターなどにある「RSSフィード」のリンクからURLを確認できる
- **文章のトーンや文字数を変える**: `bot.py` の `summarize_with_claude` 関数内の
  プロンプト文を編集する

## 注意点

- AIが生成する文章は誤りを含む可能性があります。特に専門的な内容を扱う場合、
  最初のうちは投稿前に人の目で確認できる仕組み（例: 一旦下書きとして保存し、
  自分で確認してから投稿に切り替える）を検討することをおすすめします
- Xの自動化に関する利用規約・ポリシーを確認してから運用してください
- X APIもAnthropic APIも従量課金です。想定以上に課金されないよう、各サービスの
  管理画面で支出上限（Spending limit）を設定しておくと安心です
