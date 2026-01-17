from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# ★ここが修正ポイント：裏口（_api）から直接クラスを輸入する
try:
    from youtube_transcript_api._api import YouTubeTranscriptApi
except ImportError:
    from youtube_transcript_api import YouTubeTranscriptApi

from youtube_transcript_api import TranscriptsDisabled, NoTranscriptFound
from openai import OpenAI
import os

app = FastAPI()

api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

class VideoRequest(BaseModel):
    video_id: str

@app.get("/")
def read_root():
    return {"status": "Server is running!"}

@app.post("/generate_timestamps")
def generate_timestamps(req: VideoRequest):
    if not api_key:
        raise HTTPException(status_code=500, detail="API Key not configured")

    try:
        # 字幕リストを取得
        transcript_list = YouTubeTranscriptApi.list_transcripts(req.video_id)
        
        # 日本語または英語を取得
        transcript = transcript_list.find_transcript(['ja', 'en'])
        transcript_data = transcript.fetch()
        
        # テキスト結合
        full_text = " ".join([t['text'] for t in transcript_data])
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "..."

        # AIへ命令
        prompt = f"""
        以下の動画字幕から、料理の重要な手順（材料を切る、炒める、煮込むなど）を抽出し、
        JSON形式で出力してください。雑談は無視し、手順は5〜8個に絞ってください。
        フォーマット: {{ "steps": [ {{ "time": 秒数(int), "text": "短い手順名" }} ] }}
        
        字幕データ:
        {full_text}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content

    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"No transcript found for {req.video_id}")
        raise HTTPException(status_code=404, detail="この動画には字幕がありません")
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
