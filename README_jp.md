# Growi MCP

Growi MCPは，情報共有やナレッジ管理を効率化するためのオープンソースWikiツールであるGrowiに対応したMCPサーバである．

[![PyPI - Version](https://img.shields.io/pypi/v/growi-mcp)](https://badge.fury.io/py/growi-mcp) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/growi-mcp?style=flat)](https://pypi.org/project/growi-mcp/)
[![PyPI - License](https://img.shields.io/pypi/l/growi-mcp)](https://github.com/ka1222te/growi-mcp/blob/main/README.md)

## 概要

ページリストの取得，ページの読み書き，作成，更新など様々な処理を代理で実行する非公式MCPサーバを提供する．内部ではGrowi REST APIを使用している．

## 機能

  - **Tool一覧**
    - get_page_list(path_or_id*, limit, offset)
      - 指定されたページ(ページid)以下のページリスト取得
    - read_page(path_or_id*)
      - 指定されたページ(ページid)の内容を読み取り
    - create_page(path*, body)
      - 指定されたページの作成
    - update_page(path_or_id*, body*)
      - 指定されたページ(ページid)の内容を更新
    - rename_page(path_or_id*, new_path*)
      - ページ(ページid)の名前を変更
    - remove_page(path_or_id*, recursively)
      - ページ(ページid)の削除
    - search_pages(query*, path, limit, offset)
      - クエリに対応するページを検索
    - get_user_names(query*, limit, offset)
      - クエリに対応するユーザ名取得
    - upload_attachment(page_id_or_path*, file_path*)
      - ページ(ページid)へファイルを添付
    - get_attachment_list(path_or_id*, limit, offset)
      - ページ(ページid)に添付されているファイルリスト取得
    - get_attachment_info(attachment_id*)
      - ページ(ページid)に添付されているファイルの詳細情報取得
    - download_attachment(attachment_id*, save_dir)
      - 添付されている(添付id)ファイルをローカルディレクトリへダウンロード
    - remove_attachment(attachment_id*)
      - 添付されている(添付id)ファイルを削除

- **MCPサーバー対応**
  - Model Context Protocol(MCP)に準拠
  - CursorやClineなどのAIツールから呼び出し可能なエンドポイントを提供
  - JSON-RPC over stdioベースで動作

## インストール

  ここでは，uvの導入手順を説明する．

### uvのインストール

```bash
# uvがインストールされていない場合は先にインストール
# Windowsの場合
Invoke-WebRequest -Uri "https://astral.sh/uv/install.ps1" -UseBasicParsing | Invoke-Expression
# Linuxの場合
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## 使い方

### MCPサーバーの起動

  Cline/Cursorを用いたMCPサーバの起動方法について，2つ紹介する．

#### GitHubリポジトリをクローンしてMCPサーバを起動

  Githubからコードを落としてMCPサーバを起動させる場合，以下のコマンドによって，Growi MCPのリポジトリをクローンする．

```bash
# HTTPSの場合
git clone https://github.com/ka1222te/growi-mcp.git
# SSHの場合
git clone ssh://git@github.com/ka1222te/growi-mcp.git
```

  クローンの完了後， `cd growi-mcp` によってリポジトリディレクトリへ移動し，以下のコマンドを実行することでパッケージの依存関係を解消させる．

```bash
uv sync
```
  
  次に， `.env.sample` を `.env` にコピーし，環境変数の設定を行う．以下は，環境変数の設定例である．

```bash
GROWI_DOMAIN="http://growi.example.com"
GROWI_API_TOKEN="your_access_token_here"
# API version: "1" or "3"
GROWI_API_VERSION="3"

# Optional
# If your Growi server requires a session id, set connect.sid cookie value here
#GROWI_CONNECT_SID="your_connect_sid_here"
```

  - GROWI_DOMAIN
    - Growiサーバが立っているドメインを指定
  - GROWI_API_TOKEN
    - API token．「User Settings → API Settings」からAPI tokenを発行できる
  - GROWI_API_VERSION
    - Growi REST APIの使用するバージョン．現在対応しているバージョンは，"1"と"3"の2つ
  - GROWI_CONNECT_SID
    - 一部機能(download_attachment)で必要となるセッションID．Growiにブラウザからアクセスし，開発者画面から REST APIのヘッダに付与されている `connect.sid` の内容を入力

  そして，Cline/Cursor/Claude CodeなどのAIコーディングツールの設定ファイル(JSONファイル)に以下のような設定を追加する．

```json
{
  "mcpServers": {
    "growi-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/growi-mcp",
        "run",
        "growi-mcp"
      ]
    }
  }
}
```

  `/path/to/growi-mcp` は，Growi MCPのインストールディレクトリに置き換えること．

#### GitHubリポジトリから直接MCPサーバを起動(HTTPS)

  GitHubリポジトリから直接MCPサーバを起動する場合は，Cline/Cursor/Claude CodeなどのAIコーディングツールの設定ファイル(JSONファイル)に以下のような設定を追加する．

```json
{
  "mcpServers": {
    "growi-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ka1222te/growi-mcp",
        "growi-mcp"
      ],
      "env": {
        "GROWI_DOMAIN": "http://growi.example.com",
        "GROWI_API_TOKEN": "your_access_token_here",
        "GROWI_API_VERSION": "3",
        "GROWI_CONNECT_SID": "your_connect_sid_here(Optional)" 
      }
    }
  }
}
```

  "env"の中にそれぞれ対応する環境変数を記述すること．

#### GitHubリポジトリから直接MCPサーバを起動(SSH)

  GitHubリポジトリへSSHでアクセスする場合は代わりに以下のような設定を行う．

```json
{
  "mcpServers": {
    "growi-mcp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+ssh://git@github.com/ka1222te/growi-mcp",
        "growi-mcp"
      ],
      "env": {
        "GROWI_DOMAIN": "http://growi.example.com",
        "GROWI_API_TOKEN": "your_access_token_here",
        "GROWI_API_VERSION": "3",
        "GROWI_CONNECT_SID": "your_connect_sid_here(Optional)" 
      }
    }
  }
}
```

  "env"の中にそれぞれ対応する環境変数を記述すること．

#### PyPIプロジェクトから直接MCPサーバを起動

  `uvx` コマンドを用いてPyPIプロジェクトから直接MCPサーバを起動する．

```json
{
  "mcpServers": {
    "growi-mcp": {
      "command": "uvx",
      "args": [
        "growi-mcp"
      ],
      "env": {
        "GROWI_DOMAIN": "http://growi.example.com",
        "GROWI_API_TOKEN": "your_access_token_here",
        "GROWI_API_VERSION": "3",
        "GROWI_CONNECT_SID": "your_connect_sid_here(Optional)" 
      }
    }
  }
}
```

  "env"の中にそれぞれ対応する環境変数を記述すること．

### MCPツールの使用例

Growi MCPのMCPツールを用いた使用例を以下に示す．

#### ユーザ情報取得

  AIエージェントに以下のプロンプトを入力すると，Growiで作成されているユーザ一覧の情報を取得することができる．

```
wikiに存在している全員のユーザを一覧にして表示して．
```

  `get_user_names` が実行され，全ユーザ一覧を名前順，もしくは別の形で整形して表示することができる．

#### ユーザの書き込み内容の要約

  先程得られたユーザから1人選び，書き込んでいる内容の要約を取得する．以下のようにプロンプトを入力する．

```
ユーザ名: 〇〇 がどのような書き込みをしているか要約して．
```

  `search_pages` と `read_page` などが実行され，該当ユーザが書き込みをした内容を取得，その後，LLMによる要約が出力される．

## 免責事項

  本プログラムの利用に関連して発生したいかなる損害について，プログラムの作者は一切の責任を負いません．

### プライベートな情報に対する取扱い

  Growi MCPはLLMによって生成されたtool/call (Function Call)を実行し，応答を返すため，wikiがプライベート環境で構築されている場合，内部の情報がLLMに伝わる可能性がある．そのため，連携するLLMには注意が必要である．また，機密情報が書かれている場合には，tool機能の `Auto-approve` のチェックを外しておくことを推奨する．これにより，プライベートページへのアクセスがあったときでも実行を拒否することで情報の漏洩を防ぐことができる．

### ページの更新について

  ページの更新機能に `Auto-approve` のチェックを付けておくと，他人が書いたページを改ざんしてしまう可能性がある．回避策を以下に挙げる．

  - 編集するページの範囲に制約を設ける
    - プロンプトもしくは `rules.md` などへ，「自身のユーザディレクトリ以外のページには編集を加えない」ことを記述する．これにより，LLMがページの作成者を確認しながら作業を進めることができ，他人のページへの上書きを防ぐことができる
  - `Auto-approve` のチェックを外しておく
    - ユーザが1つ1つの操作を確認して許可することによって，ページが乱雑になることを防ぐ．場合に応じて，チェックの付け外しを行うことを推奨する

## ライセンス

このプロジェクトはMITライセンスの下で公開されている．詳細は[LICENSE](LICENSE)ファイルを参照すること．
