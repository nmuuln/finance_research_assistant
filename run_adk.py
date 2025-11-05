import asyncio
import os
from typing import Optional

from dotenv import load_dotenv
from google.adk import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai.types import Content, Part

from src.adk_app.agent import build_agent

APP_NAME = "agents"


def _format_part(part) -> str:
    if getattr(part, "text", None):
        return part.text
    if getattr(part, "function_call", None):
        func = part.function_call
        return f"[function_call] {func.name}({func.args})"
    if getattr(part, "function_response", None):
        func_resp = part.function_response
        return f"[function_response] {func_resp.name}: {func_resp.response}"
    if getattr(part, "thought", None):
        return f"[thought] {part.thought}"
    if getattr(part, "thought_signature", None):
        return f"[thought_signature] {part.thought_signature}"
    if getattr(part, "inline_data", None):
        return "[inline_data] binary payload"
    return f"[unknown part] {part}"


def _event_text(event) -> str:
    if not getattr(event, "content", None) or not event.content.parts:
        return ""
    segments = [_format_part(part) for part in event.content.parts]
    return "\n".join(segment for segment in segments if segment)


def _print_final(event) -> None:
    print("\n=== ADK AGENT FINAL RESPONSE ===")
    print(_event_text(event))
    if event.actions and event.actions.state_delta:
        final_report = event.actions.state_delta.get("final_report")
        if final_report:
            print("\n[Stored final_report in session state]")


def run_adk(topic: str, user_id: str = "local-user", session_id: str = "session-1") -> Optional[str]:
    agent = build_agent()
    session_service = InMemorySessionService()

    # Pre-create the session so the runner can append events without errors.
    asyncio.run(
        session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
    )

    message = Content(role="user", parts=[Part.from_text(text=topic)])

    final_event = None
    last_agent_event = None
    for event in runner.run(user_id=user_id, session_id=session_id, new_message=message):
        if event.author == "user":
            continue
        last_agent_event = event
        if event.is_final_response():
            final_event = event
            break

    if final_event:
        _print_final(final_event)
        state_delta = getattr(final_event.actions, "state_delta", {}) or {}
        return state_delta.get("final_report") or _event_text(final_event)

    if last_agent_event:
        print("\n--- Last agent event (not marked final) ---")
        print(_event_text(last_agent_event))
        if last_agent_event.actions and last_agent_event.actions.state_delta:
            print("[State delta]")
            for k, v in last_agent_event.actions.state_delta.items():
                print(f"{k}: {v}")
    print("No final response received from the ADK agent.")
    return None


def run_conversation(initial_user_message: Optional[str] = None) -> None:
    user_id = "local-user"
    session_id = "session-1"

    agent = build_agent()
    session_service = InMemorySessionService()
    asyncio.run(
        session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
    )

    runner = Runner(
        app_name=APP_NAME,
        agent=agent,
        session_service=session_service,
    )

    print("Conversation started. Type 'export report' when you are ready for the .docx, or 'quit' to exit.\n")

    def dispatch(message: str):
        last_agent_event = None
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=Content(role="user", parts=[Part.from_text(text=message)]),
        ):
            if event.author == "user":
                continue
            last_agent_event = event
            text = _event_text(event)
            if text:
                print("Agent>")
                print(text)
            state_delta = getattr(event.actions, "state_delta", None)
            if state_delta:
                for key, value in state_delta.items():
                    print(f"[State updated] {key}: {value}")
        if not last_agent_event:
            print("Agent produced no response.")

    if initial_user_message:
        print(f"You> {initial_user_message}")
        dispatch(initial_user_message)

    while True:
        try:
            user_msg = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting conversation.")
            break
        if not user_msg:
            continue
        if user_msg.lower() in {"quit", "exit"}:
            print("Exiting conversation.")
            break
        dispatch(user_msg)


def main() -> None:
    load_dotenv()
    initial_topic = os.getenv("TOPIC")
    if initial_topic:
        run_conversation(initial_topic)
    else:
        run_conversation()


if __name__ == "__main__":
    main()
