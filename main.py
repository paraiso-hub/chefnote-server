from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
# 内部インポート（裏技）を継続
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
        # 1. とにかく字幕リストを取得
        transcript_list = YouTubeTranscriptApi.list_transcripts(req.video_id)
        
        # 2. 言語を指定せず、取れるものを何でもいいから1つ取る
        # (手動字幕があれば優先され、なければ自動生成が選ばれます)
        try:
            # 手動作成された字幕を探す
            transcript = transcript_list.find_manually_created_transcript(['ja', 'en', 'ja-JP'])
        except:
            try:
                # なければ自動生成字幕を探す（ここが本命）
                transcript = transcript_list.find_generated_transcript(['ja', 'en', 'ja-JP'])
            except:
                # それでもなければ、とにかくリストの最初にあるやつを取る（最強の保険）
                transcript = next(iter(transcript_list))
        
        # データを取得
        transcript_data = transcript.fetch()
        
        # テキスト結合
        full_text = " ".join([t['text'] for t in transcript_data])
        if len(full_text) > 15000:
            full_text = full_text[:15000] + "..."

        # AIへ命令
        prompt = f"""
        以下の動画字幕から、料理の重要な手順を抽出しJSONで出力してください。
        言語が日本語以外の場合は、日本語に翻訳して出力してください。
        フォーマット: {{ "steps": [ {{ "time": 秒数(int), "text": "短い手順名" }} ] }}
        
        字幕データ:
        {full_text}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Output valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        return response.choices[0].message.content

    except (TranscriptsDisabled, NoTranscriptFound):
        print(f"No transcript found for {req.video_id}")
        # 具体的にどんなエラーかログに残すため詳細化
        raise HTTPException(status_code=404, detail="字幕データが見つかりませんでした(IPブロックの可能性あり)")
        
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=f"Server Error: {str(e)}")
