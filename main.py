from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from openai import OpenAI
import os

app = FastAPI()

# APIキーの読み込み
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
        # ★ここが修正ポイント：より確実な 'list_transcripts' を使用
        transcript_list = YouTubeTranscriptApi.list_transcripts(req.video_id)
        
        # 日本語(ja)または英語(en)の字幕を探す
        # find_transcriptは、手動作成字幕を優先し、なければ自動生成字幕を探してくれます
        transcript = transcript_list.find_transcript(['ja', 'en'])
        
        # 実際のデータを取得
        transcript_data = transcript.fetch()
        
        # テキスト結合（文字数制限）
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
        # 字幕がない動画の場合
        print(f"No transcript found for {req.video_id}")
        raise HTTPException(status_code=404, detail="この動画には字幕がありません")
        
    except Exception as e:
        # その他のエラー
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
