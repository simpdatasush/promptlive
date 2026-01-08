import os
import json
import asyncio
from flask import Flask, render_template
from flask_sock import Sock
from google import genai
from google.genai import types as gemma_types

app = Flask(__name__)
app.config['SOCK_PING_INTERVAL'] = None 
sock = Sock(app)

# Initialize Gemini Client
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_KEY_HERE")
client = genai.Client(api_key=GEMINI_API_KEY, http_options={'api_version': 'v1alpha'})
MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"

@app.route('/')
def index():
    return render_template('index.html')

@sock.route('/ws/alex-concierge')
def alex_concierge(ws):
    async def start_live_session():
        config = {
            "system_instruction": "You are a professional British Concierge. Always respond with voice. Be brief and elegant.",
            "response_modalities": ["AUDIO"],
            "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": "Kore"}}}
        }

        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            
            async def send_loop():
                try:
                    while True:
                        msg = await asyncio.to_thread(ws.receive)
                        if not msg: break
                        # Filter heartbeat pings
                        if '{"type":"ping"}' in msg.replace(" ", ""): continue
                        
                        await session.send_client_content(
                            turns=[{"role": "user", "parts": [{"text": msg}]}],
                            turn_complete=True
                        )
                except Exception: pass

            async def receive_loop():
                try:
                    async for response in session.receive():
                        # Forward the raw Gemini JSON to the browser
                        ws.send(response.model_dump_json())
                except Exception: pass

            await asyncio.gather(send_loop(), receive_loop())

    asyncio.run(start_live_session())

if __name__ == '__main__':
    app.run(debug=True)
