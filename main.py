from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os

# 診断用：インポートをトライする
try:
    import youtube_transcript_api
    from youtube_transcript_api import YouTubeTranscriptApi
    lib_status = "Success"
    lib_file = getattr(youtube_transcript_api, '__file__', 'unknown')
    lib_dir = dir(YouTubeTranscriptApi)
except Exception as e:
    lib_status = f"Import Error: {e}"
    lib_file = "N/A"
    lib_dir = []

from openai import OpenAI

app = FastAPI()
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

class VideoRequest(BaseModel):
    video_id: str

@app.post("/generate_timestamps")
def generate_timestamps(req: VideoRequest):
    # ★ここでサーバーの内部事情を暴露させる
    try:
        # わざとエラーになるかもしれない箇所を実行
        if "list_transcripts" not in dir(YouTubeTranscriptApi):
            # メソッドがない場合、デバッグ情報を返す
            raise Exception(f"DEBUG_INFO: File={lib_file}, Dir={lib_dir[:5]}...")

        transcript_list = YouTubeTranscriptApi.list_transcripts(req.video_id)
        transcript = transcript_list.find_transcript(['ja', 'en'])
        transcript_data = transcript.fetch()
        
        full_text = " ".join([t['text'] for t in transcript_data])[:2000] # テスト用短縮

        # 成功したら仮のJSONを返す（診断優先のためAIは一旦スキップ）
        return """
        { "steps": [ { "time": 10, "text": "診断成功：正常に動作しました" } ] }
        """

    except Exception as e:
        # エラー内容にデバッグ情報を乗せてiPhoneに返す
        error_msg = f"ERR: {str(e)} | FILE: {lib_file}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)
