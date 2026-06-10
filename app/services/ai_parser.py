import json
import asyncio
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings

router = APIRouter()

OPENAI_REALTIME_URL = (
    f"wss://api.openai.com/v1/realtime?model={settings.openai_model}"
)


@router.websocket("/media-stream")
async def media_stream(twilio_ws: WebSocket):
    """
    WebSocket endpoint that Twilio connects to after /incoming-call.
    Bridges Twilio audio <-> OpenAI Realtime API (STT + LLM + TTS in one hop).
    """
    await twilio_ws.accept()
    print("[call] Twilio connected.")

    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "OpenAI-Beta": "realtime=v1",
    }

    async with websockets.connect(OPENAI_REALTIME_URL, extra_headers=headers) as openai_ws:
        print("[ai] OpenAI Realtime connected.")
        await _configure_session(openai_ws)

        stream_sid = None

        async def twilio_to_openai():
            nonlocal stream_sid
            try:
                async for raw in twilio_ws.iter_text():
                    msg = json.loads(raw)
                    event = msg.get("event")

                    if event == "start":
                        stream_sid = msg["start"]["streamSid"]
                        print(f"[call] Stream started: {stream_sid}")

                    elif event == "media":
                        await openai_ws.send(json.dumps({
                            "type": "input_audio_buffer.append",
                            "audio": msg["media"]["payload"],
                        }))

                    elif event == "stop":
                        print("[call] Twilio stream stopped.")
                        break

            except WebSocketDisconnect:
                print("[call] Twilio disconnected.")
            finally:
                await openai_ws.close()

        async def openai_to_twilio():
            try:
                async for raw in openai_ws:
                    msg = json.loads(raw)
                    event_type = msg.get("type", "")

                    if event_type == "response.audio.delta" and stream_sid:
                        await twilio_ws.send_text(json.dumps({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {"payload": msg["delta"]},
                        }))

                    elif event_type == "response.audio.done":
                        await twilio_ws.send_text(json.dumps({
                            "event": "mark",
                            "streamSid": stream_sid,
                            "mark": {"name": "turn_end"},
                        }))

                    elif event_type == "error":
                        print(f"[ai] Error from OpenAI: {msg}")

                    # Uncomment to log transcripts:
                    # elif event_type == "response.audio_transcript.done":
                    #     print(f"[ai] Agent: {msg.get('transcript')}")
                    # elif event_type == "conversation.item.input_audio_transcription.completed":
                    #     print(f"[call] User: {msg.get('transcript')}")

            except websockets.ConnectionClosed:
                print("[ai] OpenAI connection closed.")
            finally:
                await twilio_ws.close()

        await asyncio.gather(twilio_to_openai(), openai_to_twilio())


async def _configure_session(openai_ws):
    """Send initial session config and trigger an opening greeting."""
    await openai_ws.send(json.dumps({
        "type": "session.update",
        "session": {
            "turn_detection": {"type": "server_vad"},
            "input_audio_format": "g711_ulaw",
            "output_audio_format": "g711_ulaw",
            "input_audio_transcription": {"model": "whisper-1"},
            "voice": settings.voice,
            "instructions": settings.system_prompt,
            "modalities": ["text", "audio"],
            "temperature": 0.8,
        },
    }))

    # Trigger opening greeting
    await openai_ws.send(json.dumps({
        "type": "conversation.item.create",
        "item": {
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": "Greet the caller warmly and ask how you can help."}],
        },
    }))
    await openai_ws.send(json.dumps({"type": "response.create"}))
