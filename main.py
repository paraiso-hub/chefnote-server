from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import youtube_transcript_api # ★変更：直接インポート
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
    # 診断用：現在のライブラリバージョンを表示
    try:
        version = youtube_transcript_api.__version__
    except:
        version = "unknown"
    return {"status": "Server is running!", "lib_version": version}

@app.post("/generate_timestamps")
def generate_timestamps(req: VideoRequest):
    if not api_key:
        raise HTTPException(status_code=500, detail="API Key not configured")

    try:
        # ★変更：モジュール名からフルネームで呼び出す（これが一番確実）
        transcript_list = youtube_transcript_api.YouTubeTranscriptApi.list_transcripts(req.video_id)
        
        transcript = transcript_list.find_transcript(['ja', 'en'])
        transcript_data = transcript.fetch()
        
        full_text = " ".join([t['text'] for t in transcript_data])
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "..."

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
        # エラーの詳細を返すようにして原因特定しやすくする
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
