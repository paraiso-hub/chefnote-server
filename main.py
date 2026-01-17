from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI
import os

app = FastAPI()

# Renderの設定画面で入力したAPIキーをここで読み込みます
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
        # 1. 字幕取得
        transcript_list = YouTubeTranscriptApi.get_transcript(req.video_id, languages=['ja', 'en'])

        # テキスト結合（最初の15000文字程度に制限してコスト削減）
        full_text = " ".join([t['text'] for t in transcript_list])
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "..."

        # 2. AIへ命令
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

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
