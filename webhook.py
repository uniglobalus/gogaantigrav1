import json
import os
import uuid
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from livekit.api import LiveKitAPI
from livekit.api.sip_service import CreateSIPParticipantRequest
from livekit.protocol.room import CreateRoomRequest

app = FastAPI()

class TriggerRequest(BaseModel):
    phone: str
    language: str
    user_name: str
    reminder_text: str
    greeting_text: Optional[str] = None

@app.post("/trigger-reminder")
async def trigger_reminder(request: TriggerRequest, x_webhook_secret: Optional[str] = Header(None)):
    expected_secret = os.getenv("WEBHOOK_SECRET")
    if expected_secret and x_webhook_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid Webhook Secret")

    livekit_url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")
    sip_trunk_id = os.getenv("TWILIO_SIP_TRUNK_ID")

    if not all([livekit_url, api_key, api_secret, sip_trunk_id]):
        raise HTTPException(status_code=500, detail="Missing LiveKit or SIP configuration in environment")

    room_name = f"reminder-{uuid.uuid4().hex[:8]}"
    
    greeting = request.greeting_text or f"Hello, {request.user_name}."

    metadata = {
        "phone": request.phone,
        "language": request.language,
        "user_name": request.user_name,
        "reminder_text": request.reminder_text,
        "greeting_text": greeting
    }

    async with LiveKitAPI() as api:
        try:
            # Create the room with the metadata so the agent worker reads it upon entry
            await api.room.create_room(
                CreateRoomRequest(
                    name=room_name,
                    metadata=json.dumps(metadata) # JSON string
                )
            )
            
            # Create the outbound SIP participant
            sip_req = CreateSIPParticipantRequest(
                sip_trunk_id=sip_trunk_id,
                sip_call_to=request.phone,
                room_name=room_name,
                participant_identity=f"sip-{request.phone}"
            )
            await api.sip.create_sip_participant(sip_req)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "ok",
        "room_name": room_name,
        "phone": request.phone
    }

@app.get("/health")
def health():
    return {"status": "ok"}
