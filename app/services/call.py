from fastapi import APIRouter, Request
from fastapi.responses import Response

router = APIRouter()


@router.post("/incoming-call")
async def incoming_call(request: Request):
    """
    Twilio calls this webhook when someone dials your number.
    Returns TwiML that tells Twilio to open a Media Stream back to us.
    """
    host = request.headers.get("host")
    twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="wss://{host}/media-stream" />
  </Connect>
</Response>"""
    return Response(content=twiml, media_type="application/xml")
