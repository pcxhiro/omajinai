#!/usr/bin/env python3
"""Google Sheets を「データ置き場」にする。

タブ構成（初回実行時に自動作成される）:
  ログ  : 日付, カード1, カード2, 動画ID, URL, 公開状態,
          再生数, 高評価, コメント数, 平均視聴秒, 統計更新日時, 分類
          ※分類は PDCA の分類別集計用に末尾（L列）へ追加。
            統計の書き戻し範囲（G:K列）は元のシステムと同じ位置のまま。
  ルール: 日付, 改善ルール   ← PDCAで Gemini が読み書きする

認証は Sheets 専用の合鍵（リフレッシュトークン）を使う。
投稿先チャンネルがブランドアカウントで Sheets のスコープを持てないため、
投稿用（YouTube）とは合鍵を分けている（SETUP_GUIDE 1-6 参照）。
"""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def make_sheets_credentials(client_id, client_secret):
    """Sheets専用の認証情報を作る。

    合鍵は SHEETS_REFRESH_TOKEN を優先し、未設定なら YT_REFRESH_TOKEN に
    フォールバックする（元の単一合鍵方式のまま動かす場合のため）。
    クライアントID／シークレットは YouTube 用と共通。
    """
    refresh_token = (os.environ.get("SHEETS_REFRESH_TOKEN", "").strip()
                     or os.environ.get("YT_REFRESH_TOKEN", "").strip())
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SHEETS_SCOPES,
    )

LOG_TAB = "ログ"
RULE_TAB = "ルール"
LOG_HEADER = ["日付", "カード1", "カード2", "動画ID", "URL", "公開状態",
              "再生数", "高評価", "コメント数", "平均視聴秒", "統計更新日時",
              "分類"]
RULE_HEADER = ["日付", "改善ルール"]


class Sheets:
    def __init__(self, creds, spreadsheet_id):
        self.svc = build("sheets", "v4", credentials=creds)
        self.id = spreadsheet_id

    # --- 基本操作 -----------------------------------------------------
    def _get(self, rng):
        return (self.svc.spreadsheets().values()
                .get(spreadsheetId=self.id, range=rng).execute()
                .get("values", []))

    def _append(self, rng, row):
        self.svc.spreadsheets().values().append(
            spreadsheetId=self.id, range=rng, valueInputOption="RAW",
            body={"values": [row]}).execute()

    def _update(self, rng, values):
        self.svc.spreadsheets().values().update(
            spreadsheetId=self.id, range=rng, valueInputOption="RAW",
            body={"values": values}).execute()

    # --- 初期化 -------------------------------------------------------
    def ensure_tabs(self):
        meta = self.svc.spreadsheets().get(spreadsheetId=self.id).execute()
        titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
        requests = []
        for tab in (LOG_TAB, RULE_TAB):
            if tab not in titles:
                requests.append({"addSheet": {"properties": {"title": tab}}})
        if requests:
            self.svc.spreadsheets().batchUpdate(
                spreadsheetId=self.id, body={"requests": requests}).execute()
        if not self._get(f"{LOG_TAB}!A1:L1"):
            self._update(f"{LOG_TAB}!A1:L1", [LOG_HEADER])
        if not self._get(f"{RULE_TAB}!A1:B1"):
            self._update(f"{RULE_TAB}!A1:B1", [RULE_HEADER])

    # --- ログ ---------------------------------------------------------
    def read_log(self):
        """ヘッダを除いた全行を dict のリストで返す（行番号つき）。"""
        rows = self._get(f"{LOG_TAB}!A2:L1000")
        out = []
        for i, r in enumerate(rows):
            r = (r + [""] * len(LOG_HEADER))[:len(LOG_HEADER)]
            d = dict(zip(LOG_HEADER, r))
            d["_row"] = i + 2  # シート上の行番号
            out.append(d)
        return out

    def append_log(self, row):
        self._append(f"{LOG_TAB}!A:L", row)

    def update_stats(self, row_no, views, likes, comments, avg_sec, when):
        self._update(f"{LOG_TAB}!G{row_no}:K{row_no}",
                     [[views, likes, comments,
                       "" if avg_sec is None else round(avg_sec, 1), when]])

    # --- ルール -------------------------------------------------------
    def read_rules(self, limit=30):
        rows = self._get(f"{RULE_TAB}!A2:B1000")
        rules = [r[1] for r in rows if len(r) > 1 and r[1].strip()]
        return rules[-limit:]

    def append_rule(self, date_str, rule):
        self._append(f"{RULE_TAB}!A:B", [date_str, rule])
