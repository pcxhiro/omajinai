#!/usr/bin/env python3
"""YouTube Data API v3 / YouTube Analytics API ラッパ。

認証はリフレッシュトークン方式。同意画面を「本番（In production）」に
してから取得したトークンなら7日失効はなく、毎日使う限り維持される。
"""
import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# 注意：このチャンネルはブランドアカウントのため、YouTube用の合鍵Aには
# YouTube系スコープしか付いていない。ここに spreadsheets を含めると、
# トークン更新（refresh）のたびに未付与のスコープまで要求してしまい、
# Googleに access_denied (Account Restricted) で拒否される（2026-11-19 実測）。
# スプレッドシート用スコープは sheets_api.py 側（合鍵B）だけが持つ。
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def make_credentials(client_id, client_secret, refresh_token):
    return Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )


class YouTube:
    def __init__(self, creds):
        self.yt = build("youtube", "v3", credentials=creds)
        self.ya = build("youtubeAnalytics", "v2", credentials=creds)
        self._channel_id = None

    def channel_id(self):
        if not self._channel_id:
            res = self.yt.channels().list(part="id", mine=True).execute()
            self._channel_id = res["items"][0]["id"]
        return self._channel_id

    def upload(self, path, title, description, tags, privacy="public"):
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": "22",  # People & Blogs
                "defaultLanguage": "ja",
            },
            "status": {
                "privacyStatus": privacy,
                "selfDeclaredMadeForKids": False,
                # AI合成音声を使うため、合成メディア申告をONにする
                "containsSyntheticMedia": True,
            },
        }
        media = MediaFileUpload(path, mimetype="video/mp4", resumable=True)
        res = (self.yt.videos()
               .insert(part="snippet,status", body=body, media_body=media)
               .execute())
        return res["id"], res.get("status", {}).get("privacyStatus", privacy)

    def post_comment(self, video_id, text):
        body = {
            "snippet": {
                "channelId": self.channel_id(),
                "videoId": video_id,
                "topLevelComment": {"snippet": {"textOriginal": text}},
            }
        }
        res = self.yt.commentThreads().insert(part="snippet", body=body).execute()
        return res["id"]

    def get_stats(self, video_ids):
        """{video_id: {views, likes, comments}} をまとめて取得。"""
        out = {}
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i + 50]
            res = self.yt.videos().list(
                part="statistics", id=",".join(batch)).execute()
            for item in res.get("items", []):
                s = item.get("statistics", {})
                out[item["id"]] = {
                    "views": int(s.get("viewCount", 0)),
                    "likes": int(s.get("likeCount", 0)),
                    "comments": int(s.get("commentCount", 0)),
                }
        return out

    def get_avg_view_duration(self, video_id):
        """YouTube Analytics から平均視聴秒を取得（データが無い場合は None）。"""
        today = datetime.date.today().isoformat()
        try:
            res = self.ya.reports().query(
                ids="channel==MINE",
                startDate="2020-01-01",
                endDate=today,
                metrics="averageViewDuration",
                dimensions="video",
                filters=f"video=={video_id}",
            ).execute()
            rows = res.get("rows", [])
            return float(rows[0][1]) if rows else None
        except Exception as e:
            print(f"[analytics] avg duration failed for {video_id}: {e}")
            return None
