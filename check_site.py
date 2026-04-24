import os
import hashlib
import requests
import sys
import logging

# ログの設定（実行時に何が起きたか分かりやすくするため、標準出力に日時とログレベルを出力します）
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

URL = "http://www.tokyo-hsbad.com/"
HASH_FILE = "last_hash.txt"

# GitHub ActionsのSecrets（環境変数）から取得
# os.environ.get() は環境変数が設定されていない場合 None を返します
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL_ID = os.environ.get("SLACK_CHANNEL_ID")

def get_page_hash():
    """URLからHTMLを取得し、SHA-256（暗号学的ハッシュ関数）ハッシュ値を返す。
    ハッシュ値とは、データから生成される固定長の適当な文字列のこと。
    データが1文字でも変われば全く違う文字列になるため、変更検知に便利です。
    """
    try:
        # サイトに負荷をかけないようタイムアウトを10秒に設定
        # 万が一サイトが重くても、10秒で諦めるようにします
        response = requests.get(URL, timeout=10)
        # ステータスコードが200番台（成功）以外の場合は例外を発生させます
        response.raise_for_status()
        
        # HTMLの中身（バイナリデータ）をハッシュ化して返します
        return hashlib.sha256(response.content).hexdigest()
    
    except requests.exceptions.RequestException as e:
        # ネットワークエラーやタイムアウトが発生した場合の処理
        logging.error(f"ページの取得に失敗しました: {e}")
        return None

def send_slack_notification():
    """Slack APIを使ってプライベートチャンネルに通知を送る"""
    # Slackのメッセージ送信APIのエンドポイント
    slack_api_url = "https://slack.com/api/chat.postMessage"
    
    # APIのリクエストヘッダー（認証情報などを設定）
    headers = {
        "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Slackに送るメッセージの内容
    data = {
        "channel": SLACK_CHANNEL_ID,
        "text": f"👀 Webサイトが更新されました！\n{URL}"
    }
    
    try:
        # Slack APIへPOSTリクエストを送信
        response = requests.post(slack_api_url, headers=headers, json=data, timeout=10)
        response.raise_for_status()
        
        # Slack APIのレスポンス確認（JSON形式で返ってきます）
        result = response.json()
        if not result.get("ok"):
            # Slack API特有のエラー（Tokenが無効、チャンネルが無いなど）の場合
            logging.error(f"Slack通知エラー詳細: {result.get('error')}")
            return False
            
        return True
        
    except requests.exceptions.RequestException as e:
        # 通信エラーが発生した場合
        logging.error(f"Slack APIへのリクエストに失敗しました: {e}")
        return False

def main():
    # 1. 環境変数のチェック（設定忘れを防ぐため）
    if not SLACK_BOT_TOKEN or not SLACK_CHANNEL_ID:
        logging.error("環境変数 SLACK_BOT_TOKEN または SLACK_CHANNEL_ID が設定されていません。")
        sys.exit(1) # エラー終了
        
    logging.info("サイトの確認を開始します。")
    
    # 2. 現在のページのハッシュ値を取得
    current_hash = get_page_hash()
    
    # 取得に失敗した場合は処理を中断（前回の状態を保持するため）
    if current_hash is None:
        logging.warning("ハッシュ値が取得できなかったため、処理を終了します。")
        sys.exit(1)
    
    # 3. 前回のハッシュ値をファイルから読み込む
    last_hash = ""
    # os.path.exists でファイルが存在するか確認
    if os.path.exists(HASH_FILE):
        # ファイルを開いて中身を読み込む（文字化け防止・環境非依存のため utf-8 を指定）
        with open(HASH_FILE, "r", encoding="utf-8") as f:
            last_hash = f.read().strip() # strip() で前後の空白や改行を削除
            
    # 4. ハッシュ値の比較（前回と今回で変化があったか？）
    if current_hash != last_hash:
        logging.info("変更を検知しました。")
        
        # 初回実行時（last_hashが空）は通知をスキップし、基準となるハッシュの保存のみ行う
        if True:  # テスト用：強制通知
            # 通知を送信
            success = send_slack_notification()
            if success:
                logging.info("Slackへ通知を送信しました。")
            else:
                logging.error("Slackへの通知に失敗しました。")
        else:
            logging.info("初回実行のため、通知はスキップします。")
            
        # 5. 新しいハッシュ値を保存（次回以降の比較のため）
        # 書き込みモード("w")でファイルを開く（同じく utf-8 を指定）
        with open(HASH_FILE, "w", encoding="utf-8") as f:
            f.write(current_hash)
            
    else:
        logging.info("変更はありませんでした。")

if __name__ == "__main__":
    main()
