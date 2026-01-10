import asyncio
import os
import json
import base64
from quart import Quart, render_template, websocket
from google import genai
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

app = Quart(__name__)

# --- CONFIG ---
API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"

client = genai.Client(api_key=API_KEY, http_options={'api_version': 'v1alpha'})

@app.route('/')
async def index():
    return await render_template('index.html')

@app.websocket('/ws')
async def ws():
    # ADD THIS: output_audio_transcription enables text while speaking
    config = {
        "system_instruction": "You are Lexi. Be concise. Respond in audio.",
        "response_modalities": ["AUDIO"],
        "output_audio_transcription": {}  # This triggers the transcription events
    }

    try:
        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            
            # TASK: Gemini -> Browser
            async def gemini_to_browser():
                async for response in session.receive():
                    # 1. Handle Transcribed Text
                    # This now populates because of 'output_audio_transcription'
                    if response.server_content and response.server_content.output_transcription:
                        await websocket.send(json.dumps({
                            "type": "text", 
                            "data": response.server_content.output_transcription.text
                        }))

                    # 2. Handle Audio Data
                    if response.server_content and response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data:
                                b64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                await websocket.send(json.dumps({
                                    "type": "audio", 
                                    "data": b64_audio
                                }))

            # TASK: Browser -> Gemini
            async def browser_to_gemini():
                while True:
                    message = await websocket.receive()
                    data = json.loads(message)
                    if data.get("type") == "text":
                        # Send text input to Gemini
                        await session.send(input=data["data"], end_of_turn=True)

            await asyncio.gather(gemini_to_browser(), browser_to_gemini())
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Host on 0.0.0.0 to make it accessible on your network
    app.run(host="0.0.0.0", port=5000)
