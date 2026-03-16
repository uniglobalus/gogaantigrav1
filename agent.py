import asyncio
import json
import logging
from livekit.agents import AutoSubscribe, JobContext, WorkerOptions, cli, llm
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import google

logger = logging.getLogger("outbound-agent")
logger.setLevel(logging.INFO)

async def entrypoint(ctx: JobContext):
    try:
        metadata = json.loads(ctx.room.metadata)
    except Exception as e:
        logger.error(f"Failed to parse room metadata: {e}")
        metadata = {}

    language = metadata.get("language", "hy")
    user_name = metadata.get("user_name", "User")
    reminder_text = metadata.get("reminder_text", "No reminder")
    greeting_text = metadata.get("greeting_text", f"Hello {user_name}.")

    system_prompt = f"""You are a helpful reminder assistant.
You MUST speak exclusively in the language specified by this BCP-47 code: "{language}".
The user's name is {user_name}.
You have already greeted the user with: "{greeting_text}"

Your task is to:
1. Deliver this reminder text: "{reminder_text}"
2. Ask if they have any questions about it.
3. If they don't have questions or after answering them, say goodbye politely and succinctly.

Keep your responses very concise and conversational, appropriate for a voice call.
"""

    initial_ctx = llm.ChatContext().append(role="system", text=system_prompt)
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    agent = VoicePipelineAgent(
        chat_ctx=initial_ctx,
        llm=google.realtime.RealtimeModel(
            model="gemini-2.5-flash-native-audio-preview-12-2025"
        )
    )

    agent.start(ctx.room)
    
    # Wait slightly to ensure the connection is fully settled
    await asyncio.sleep(0.5)
    
    # Issue the required greeting text directly
    agent.say(greeting_text, allow_interruptions=True)

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
