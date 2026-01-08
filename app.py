import os
import json
import asyncio
import datetime
from flask import Flask, render_template
from flask_sock import Sock
from google import genai

app = Flask(__name__)
app.config['SOCK_PING_INTERVAL'] = None 
sock = Sock(app)

# Initialize Gemini Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"), http_options={'api_version': 'v1alpha'})
MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"

def save_log(user_text, lexi_text):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("lexi_chat_history.txt", "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}]\nUSER: {user_text}\nLEXI: {lexi_text}\n{'-'*30}\n")

@sock.route('/ws/alex-concierge')
def alex_concierge(ws):
    async def start_live_session():
        # Notice: modalities is now empty or text-focused, 
        # but we keep output_audio_transcription to get the text stream.
        config = {
            "system_instruction": "You are Lexi, a helpful British concierge. Provide elegant, brief text responses.",
            "response_modalities": ["TEXT"], 
        }

    async def start_live_session():
        async with client.aio.live.connect(model=MODEL_ID, config=config) as session:
            
            async def send_loop():
                try:
                    while True:
                        msg = await asyncio.to_thread(ws.receive)
                        if not msg: break
                        try:
                            if json.loads(msg).get('type') == 'ping': continue
                        except: pass
                        
                        await session.send_client_content(
                            turns=[{"role": "user", "parts": [{"text": msg}]}],
                            turn_complete=True
                        )
                except: pass

            async def receive_loop():
                try:
                    full_reply = []
                    async for response in session.receive():
                        # Use model_turn.parts to get text
                        if response.server_content and response.server_content.model_turn:
                            for part in response.server_content.model_turn.parts:
                                if part.text:
                                    full_reply.append(part.text)
                                    # Send only the text part to the browser
                                    ws.send(json.dumps({"text": part.text}))

                        if response.server_content and response.server_content.turn_complete:
                            save_log("Web User", "".join(full_reply))
                            full_reply = []
                            ws.send(json.dumps({"done": True}))
                except: pass

            await asyncio.gather(send_loop(), receive_loop())

    asyncio.run(start_live_session())
