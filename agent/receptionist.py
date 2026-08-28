import asyncio
import json
import logging
import os

import aiohttp
from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentSession,
    APIStatusError,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    WorkerOptions,
    cli,
    metrics,
    room_io,
)
from livekit.plugins import openai, silero, anam, noise_cancellation

logger = logging.getLogger("receptionist")

load_dotenv(".env.local")

RECEPTIONIST_INSTRUCTIONS = """You are Sandbox Space's virtual receptionist. Your role is to welcome visitors, answer common questions, help people choose the right workspace, explain Sandbox's services, and assist with bookings or direct them to the human team when necessary.

Your tone is friendly, professional, helpful, short and conversational. Never overly robotic. Always greet users warmly.

ABOUT SANDBOX SPACE:
Sandbox Space is a modern coworking space in Malaysia with locations in Sri Petaling, Kuala Lumpur, and Bandar Sunway, Petaling Jaya. Sandbox provides flexible workspaces for freelancers, remote workers, entrepreneurs, startups, SMEs, students, small teams, and growing businesses. Sandbox focuses on flexibility, affordability, productivity, and community. Key features include true 24/7 member access, air conditioning available 24/7, high-speed WiFi 7, flexible daily and monthly plans, no long-term contracts for many plans, a professional working environment, and community networking opportunities.

SERVICES:
Hot Desk: best for freelancers, students, remote workers, and anyone needing a flexible workspace. Available as a walk-in day pass or a monthly membership. Monthly members receive additional benefits like 24/7 access, a business address, mail handling, and community portal access. Amenities include WiFi 7, free-flow coffee, tea, snacks, private phone booths, a rain shower, locker rental, and professional networking events.

Dedicated Desk: a permanent desk in a shared coworking area, suitable for users who want their own workstation, want to leave equipment at the office, and want daily access without changing seats. Includes 24/7 member access.

Private Office: fully furnished offices suitable for 1 to 10 people, startups, small companies, and growing teams. Features include 24/7 access, air conditioning, office furniture, and flexible plans. Starting from approximately RM780 per room.

Meeting Rooms: available for booking, suitable for client meetings, interviews, team discussions, and workshops. If users ask about capacity or pricing and you don't know the latest information, politely offer to connect them with the Sandbox team.

Event Space: venues for workshops, seminars, training sessions, networking events, product launches, and community gatherings. If users need custom event arrangements, collect the date, number of attendees, and event type, then recommend contacting the Sandbox team.

RULES:
- If asked about anything you don't have confirmed details on (exact pricing, live availability, capacity), politely offer to connect the visitor with the Sandbox team rather than guessing.
- For event space requests, always collect date, number of attendees, and event type before recommending they contact the team.
- Keep responses to one or two short spoken sentences unless walking through details the visitor asked for.
- IMPORTANT: Your responses will be read aloud by a text-to-speech system. Never use markdown formatting of any kind — no asterisks, no bullet points, no numbered lists, no hashes, no underscores, no ellipses (...). Write in plain natural spoken language only.

FREQUENTLY ASKED QUESTIONS:
When a visitor asks any of the following, answer using the exact wording provided. You may add a short friendly lead-in, but never change the facts, numbers, prices, or phone number.

Q: What are your operating hours?
A: Our staff operating hours are Monday to Sunday, from 9 AM to 6 PM.

Q: What are the Day Pass access hours?
A: Day Pass users can access the space from 9 AM to 6 PM. No advance booking is required for a walk-in Day Pass.

Q: Who is eligible for 24/7 access?
A: Monthly Hot Desk residents, Dedicated Desk members, and Private Office members receive 24/7 access with air conditioning.

Q: Is parking available?
A: Yes. Street parking is available around the Sri Petaling branch, and monthly parking spaces start from 150 ringgit. Parking availability at Bandar Sunway may vary.

Q: What is your Wi-Fi speed?
A: Sandbox provides high-speed Wi-Fi 7. Private offices have speeds of up to 2 gigabits per second, while Hot Desk and Dedicated Desk areas provide up to 1 gigabit per second.

Q: How much does a private office cost?
A: Private offices start from 780 ringgit per month at Sri Petaling and 880 ringgit per month at Bandar Sunway. Prices depend on the office size and number of people.

Q: What is the difference between a Hot Desk, Dedicated Desk, and Private Office?
A: A Hot Desk lets you use any available shared desk. A Dedicated Desk is reserved for you, while a Private Office gives you a private, lockable room for one to ten people.

Q: Where are your branch locations?
A: We have two branches: Sri Petaling, Kuala Lumpur, and Bandar Sunway, Petaling Jaya.

Q: How do I book a workspace or schedule a tour?
A: You can contact Sandbox through the website, WhatsApp, or call 012-326 7533. Day Pass users may walk in without making a booking.

Q: Is a deposit required?
A: Yes. A refundable security deposit is required for monthly workspaces, private offices, meeting rooms, podcast rooms, and event bookings. The amount will be confirmed during booking.

Q: What amenities are included with a membership?
A: Amenities include fast Wi-Fi 7, free-flow coffee, tea and snacks, private call booths, printing and scanning facilities, rain showers, and community events.

Q: What member benefits do I get?
A: Depending on your plan, benefits may include 24/7 access, a business address, mail handling, meeting-room credits, printing credits, and access to the community portal.

Q: Can I use both Sandbox branches under one membership?
A: Yes, you can access both Sandbox branches under one membership.

Q: How much is a Hot Desk Day Pass?
A: A normal Day Pass is 28 ringgit. Students pay 18 ringgit, while Sandbox members pay 14 ringgit.

Q: How much is the monthly Hot Desk plan?
A: The monthly Hot Desk resident plan is 400 ringgit per person at both branches.

Q: What is included with the monthly Hot Desk plan?
A: It includes 24/7 access, air conditioning, a business address, mail handling, and access to the community portal.

Q: Do Day Pass users receive 24/7 access?
A: No. Day Pass access is from 9 AM to 6 PM. Monthly residents receive 24/7 access.

Q: Do I need to book a Day Pass in advance?
A: No. Day Passes are available for walk-ins, so advance booking is not required.

Q: How much is a Dedicated Desk?
A: A Dedicated Desk costs 530 ringgit per month at both Sri Petaling and Bandar Sunway.

Q: What is included with a Dedicated Desk?
A: It includes 24/7 access, a lockable drawer, meeting-room credits, printing credits, a business address, and mail handling.

Q: Can I leave my equipment at a Dedicated Desk?
A: Yes. The desk is reserved for you, so you can leave equipment such as your computer or monitor set up there.

Q: How much is a meeting room?
A: Meeting rooms start from 38 ringgit per hour.

Q: How many people can the meeting rooms accommodate?
A: The meeting and training rooms can accommodate up to 30 people.

Q: What equipment is included in the meeting rooms?
A: The rooms include high-speed Wi-Fi, an HDTV, and a whiteboard.

Q: Do you have a podcast room?
A: Yes. The podcast room supports audio and video recording and can accommodate up to five people.

Q: How much is the podcast room?
A: The podcast room starts from 58 ringgit per hour.

Q: Do you provide event spaces?
A: Yes. Sandbox provides event spaces for seminars, workshops, product launches, and other events.

Q: Can events be held after operating hours?
A: Yes. Events can be arranged after normal operating hours.

Q: What is the Wi-Fi speed for Hot Desks and Dedicated Desks?
A: Hot Desk and Dedicated Desk areas provide Wi-Fi 7 with speeds of up to 1 gigabit per second.

Q: Is coffee included?
A: Yes. Members and workspace users can enjoy free-flow coffee, tea, and snacks.

Q: Are private call booths available?
A: Yes. Private call booths are available for calls and online meetings.

Q: Can I use Sandbox as my business address?
A: Yes. Monthly Hot Desk, Dedicated Desk, and Private Office plans can include a business address and mail handling.

Q: Are the workspaces fully furnished?
A: Yes. Private offices are fully furnished and ready for teams of one to ten people.

Q: Are utilities included in the private-office price?
A: Yes. Private-office rates include furniture, utilities, and shared coworking amenities.

Q: Is there a long-term contract?
A: Sandbox offers flexible daily and monthly plans without binding long-term contracts."""

RECEPTIONIST_GREETING = (
    "Hi! Welcome to Sandbox Space. I'm here to help you with our coworking spaces, "
    "private offices, meeting rooms, event spaces, memberships, pricing, and general "
    "questions. What can I help you with today?"
)

DEFAULT_LANGUAGE = "english"

# Languages the visitor can switch to mid-session. Confirmation lines mirror the
# wording style already used for interviews in agent.py.
SUPPORTED_LANGUAGES = {
    "english": {
        "label": "English",
        "stt_code": "en",
        "confirmation": "Sure, I'll continue in English. How can I help you?",
    },
    "chinese": {
        "label": "Chinese",
        "stt_code": "zh",
        "confirmation": "好的,我会用中文继续为您服务。请问有什么可以帮您?",
    },
    "malay": {
        "label": "Malay",
        "stt_code": "ms",
        "confirmation": "Baik, saya akan teruskan dalam Bahasa Melayu. Apa yang boleh saya bantu?",
    },
}

DEFAULT_AVATAR = "carl"

# Switching avatars briefly runs two Anam sessions at once so the outgoing avatar can
# keep talking until the incoming one is live. LiveKit evicts duplicate identities, so
# the two must alternate between these instead of sharing one name.
AVATAR_IDENTITY_PREFIX = "receptionist-avatar"
AVATAR_IDENTITIES = (AVATAR_IDENTITY_PREFIX, f"{AVATAR_IDENTITY_PREFIX}-b")


def other_avatar_identity(identity: str) -> str:
    return AVATAR_IDENTITIES[1] if identity == AVATAR_IDENTITIES[0] else AVATAR_IDENTITIES[0]

# Avatars the visitor can switch to mid-session, each paired with a matching TTS voice.
#
# Anam cannot change the avatar on a live session (avatarId is fixed when the session
# token is created), so switching tears down the Anam engine session and starts a new
# one under the same participant identity. Reusing the identity is deliberate: it keeps
# the frontend video lookup, transcript attribution and is_visitor_participant() working
# untouched. See anam-avatar-switch-analysis.md for the full reasoning.
#
# Must stay in sync with AVATARS in web/resources/js/pages/room/receptionist-room.tsx.
SUPPORTED_AVATARS = {
    "carl": {
        "label": "Carl",
        "avatar_id_env": "ANAM_RECEPTIONIST_AVATAR_ID",
        "voice": "ash",
    },
    "cara": {
        "label": "Cara",
        "avatar_id_env": "ANAM_RECEPTIONIST_AVATAR_ID_FEMALE",
        "voice": "coral",
    },
}


def get_avatar_id(avatar: str) -> str | None:
    """Resolve an avatar key to its Anam avatar id, read at call time so .env.local wins."""
    return os.getenv(SUPPORTED_AVATARS[avatar]["avatar_id_env"])


def build_language_instructions(language: str) -> str:
    """Locked-language directive: the receptionist never mirrors the visitor's language."""
    label = SUPPORTED_LANGUAGES[language]["label"]
    return f"""

LANGUAGE RULES (CRITICAL):
- You must always respond in {label}, for every single reply, for the entire conversation.
- This applies no matter what language the visitor speaks. If they speak English, Chinese, Malay, or any other language, you still reply only in {label}.
- You may understand and interpret questions asked in other languages, but your spoken responses must never switch away from {label}.
- Do not mirror the visitor's language. Do not ask the visitor to switch languages — simply continue in {label}."""


def build_instructions(language: str) -> str:
    return RECEPTIONIST_INSTRUCTIONS + build_language_instructions(language)


def is_visitor_participant(participant) -> bool:
    identity = participant.identity
    # Prefix match, not equality: an avatar switch briefly puts two avatars in the room
    # under alternating identities (see AVATAR_IDENTITIES).
    if identity.startswith(AVATAR_IDENTITY_PREFIX) or identity.startswith("agent-"):
        return False
    if participant.attributes.get(room_io.ATTRIBUTE_PUBLISH_ON_BEHALF):
        return False
    return True


async def wait_for_visitor_participant(room):
    while True:
        for participant in room.remote_participants.values():
            if is_visitor_participant(participant):
                return participant
        await asyncio.sleep(0.25)


async def stop_anam_session(session_id: str) -> bool:
    """Ask Anam to end a session so its concurrent-session slot is freed.

    Anam documents no endpoint for terminating a running session, so this is a
    best-effort call. The response is checked rather than blindly logged as success —
    a silent 404 here used to look identical to a working teardown.
    """
    api_key = os.getenv("ANAM_RECEPTIONIST_API_KEY")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.delete(
                f"https://api.anam.ai/v1/engine/session/{session_id}",
                headers={"Authorization": f"Bearer {api_key}"},
            ) as resp:
                if resp.ok:
                    logger.info(f"Anam session {session_id} terminated (status {resp.status})")
                    return True

                body = await resp.text()
                logger.warning(
                    f"Anam refused to terminate session {session_id} "
                    f"(status {resp.status}): {body[:200]}"
                )
                return False
    except Exception as e:
        logger.warning(f"Failed to terminate Anam session {session_id}: {e}")
        return False


async def remove_avatar_participant(room_name: str, identity: str) -> bool:
    """Kick an avatar out of the LiveKit room.

    Anam streams in as a room participant, so dropping that participant is what
    actually ends its session — the HTTP DELETE above is not reliably enough.
    """
    try:
        lkapi = api.LiveKitAPI()
        try:
            await lkapi.room.remove_participant(
                api.RoomParticipantIdentity(room=room_name, identity=identity)
            )
            logger.info(f"Removed avatar participant '{identity}' from {room_name}")
            return True
        finally:
            await lkapi.aclose()
    except Exception as e:
        logger.warning(f"Could not remove avatar participant '{identity}': {e}")
        return False


async def retire_avatar(avatar, identity: str, room_name: str) -> None:
    """Fully tear down an avatar: detach handlers, kick it, then free the Anam slot."""
    try:
        await avatar.aclose()
    except Exception as e:
        logger.warning(f"avatar.aclose() failed for '{identity}': {e}")

    await remove_avatar_participant(room_name, identity)

    if avatar.session_id:
        await stop_anam_session(avatar.session_id)


class Assistant(Agent):
    def __init__(self, room, language: str = DEFAULT_LANGUAGE) -> None:
        self._room = room
        self._greeted = False
        self.language = language
        super().__init__(instructions=build_instructions(language))

    async def on_enter(self) -> None:
        # on_enter fires again every time the session is rebuilt for an avatar switch.
        # The visitor is mid-conversation by then, so greet only the first time.
        if self._greeted:
            return
        self._greeted = True

        await wait_for_visitor_participant(self._room)
        await self.session.say(RECEPTIONIST_GREETING, allow_interruptions=False)


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    await ctx.room.local_participant.set_name("Sandbox Receptionist")

    ctx.log_context_fields = {"room": ctx.room.name}

    stt = openai.STT(detect_language=True)
    # Held in a variable (like stt) so the avatar switch can call tts.update_options()
    # to change voice mid-session without rebuilding the AgentSession.
    tts = openai.TTS(voice=SUPPORTED_AVATARS[DEFAULT_AVATAR]["voice"], speed=1.1)

    usage_collector = metrics.UsageCollector()

    def build_session() -> AgentSession:
        """Create a fresh AgentSession sharing the same stt/tts/vad instances.

        A new session is built for every avatar switch. That is deliberate: the
        LiveKit avatar API expects AvatarSession.start() to run *before*
        AgentSession.start(). Starting an avatar under a live session reassigns
        session.output.audio, which detaches the TranscriptSynchronizer RoomIO
        installed at start — and once detached it cannot be re-pointed, leaving
        captions racing ahead of the voice. Rebuilding the session restores the
        supported ordering instead of fighting it.
        """
        s = AgentSession(
            llm=openai.LLM(model="gpt-4o-mini"),
            stt=stt,
            tts=tts,
            vad=ctx.proc.userdata["vad"],
            preemptive_generation=True,
            min_endpointing_delay=0.2,
            max_endpointing_delay=0.8,
        )

        @s.on("metrics_collected")
        def _on_metrics_collected(ev: MetricsCollectedEvent):
            metrics.log_metrics(ev.metrics)
            usage_collector.collect(ev.metrics)

        return s

    def build_room_options() -> room_io.RoomOptions:
        """Room I/O options — identical for the first session and every rebuild."""
        return room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=noise_cancellation.BVC(),
            ),
            text_output=room_io.TextOutputOptions(sync_transcription=True),
        )

    session = build_session()

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # The avatar currently on screen. Held in a dict rather than a plain local so the
    # switch handler and the shutdown callback both always act on whichever Anam
    # session is live right now.
    avatar_state: dict = {
        "key": DEFAULT_AVATAR,
        "session": None,
        "identity": AVATAR_IDENTITIES[0],
    }

    async def start_anam_avatar(avatar_key: str, identity: str):
        """Create and start an Anam avatar session under the given participant identity."""
        avatar_id = get_avatar_id(avatar_key)
        if not avatar_id:
            raise RuntimeError(
                f"no Anam avatar id configured for '{avatar_key}' "
                f"(expected {SUPPORTED_AVATARS[avatar_key]['avatar_id_env']} in .env.local)"
            )

        avatar = anam.AvatarSession(
            persona_config=anam.PersonaConfig(
                name="Sandbox Receptionist",
                avatarId=avatar_id,
            ),
            api_key=os.getenv("ANAM_RECEPTIONIST_API_KEY"),
            avatar_participant_identity=identity,
            avatar_participant_name="Sandbox Receptionist",
        )
        await avatar.start(session, room=ctx.room)
        return avatar

    async def wait_for_avatar_video(identity: str, timeout: float = 20.0) -> bool:
        """Block until `identity` is publishing video, so we never cut over too early."""
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            participant = ctx.room.remote_participants.get(identity)
            if participant is not None:
                for pub in participant.track_publications.values():
                    if pub.kind == rtc.TrackKind.KIND_VIDEO:
                        return True
            await asyncio.sleep(0.2)
        return False

    async def wait_for_participant_gone(identity: str, timeout: float = 5.0) -> bool:
        """Block until `identity` has left the room — our best signal that Anam is
        actually tearing the session down and releasing its concurrency slot."""
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if ctx.room.remote_participants.get(identity) is None:
                return True
            await asyncio.sleep(0.2)
        return False

    async def start_avatar_with_retry(
        avatar_key: str, identity: str, timeout: float = 25.0
    ):
        """Start an avatar, retrying while Anam still reports its concurrency limit.

        On the Starter plan only one session may exist at a time, and Anam does not
        release the slot the instant the old session is torn down. The plugin itself
        never retries an APIStatusError, so the backoff has to live here.
        """
        deadline = asyncio.get_running_loop().time() + timeout
        attempt = 0
        started_at = asyncio.get_running_loop().time()

        while True:
            attempt += 1
            try:
                avatar = await start_anam_avatar(avatar_key, identity)
                waited = asyncio.get_running_loop().time() - started_at
                logger.info(
                    f"Anam accepted the new session on attempt {attempt} "
                    f"after {waited:.1f}s"
                )
                return avatar
            except APIStatusError as e:
                if e.status_code != 429:
                    raise
                if asyncio.get_running_loop().time() >= deadline:
                    raise RuntimeError(
                        f"Anam still reported its concurrent-session limit after "
                        f"{timeout:.0f}s ({attempt} attempts). The previous session "
                        f"has not been released — this plan may not support switching."
                    ) from e
                logger.warning(
                    f"Anam slot still busy (attempt {attempt}), retrying in 2s…"
                )
                await asyncio.sleep(2.0)

    # Try to start Anam avatar; fall back to voice-only if the concurrent limit is hit
    try:
        # Retried rather than attempted once. Anam allows a single concurrent session
        # for the whole organisation, and the previous visit's session is not released
        # until its room is torn down — so a reload lands inside that gap and used to
        # give up instantly, leaving the visitor with a voice and no face.
        avatar_state["session"] = await start_avatar_with_retry(
            DEFAULT_AVATAR, avatar_state["identity"], timeout=40.0
        )
        logger.info("Anam avatar started successfully")

        # Register cleanup so the session slot is freed when the job ends. Reads
        # avatar_state at call time so it terminates whichever avatar is current.
        # retire_avatar() rather than stop_anam_session() alone: kicking the participant
        # is what actually ends the session — the HTTP DELETE answers 404.
        async def stop_avatar():
            avatar = avatar_state["session"]
            if avatar is not None:
                avatar_state["session"] = None
                await retire_avatar(avatar, avatar_state["identity"], ctx.room.name)

        ctx.add_shutdown_callback(stop_avatar)

    except Exception as e:
        logger.warning(f"Anam avatar unavailable ({e}), continuing as voice-only")

    # Anam's single org-wide slot is held until the avatar participant leaves, and
    # LiveKit keeps the room alive ~20s past the last visitor. Waiting that out meant
    # the next visitor's avatar request was refused, so release the slot the moment the
    # visitor is actually gone. is_visitor_participant() is the guard that makes this
    # safe: an avatar switch disconnects the outgoing avatar, and that must never be
    # mistaken for the visitor leaving.
    release_tasks: set[asyncio.Task] = set()

    def on_visitor_disconnected(participant: rtc.RemoteParticipant) -> None:
        if not is_visitor_participant(participant):
            return

        avatar = avatar_state["session"]
        if avatar is None:
            return

        # Claimed before awaiting so the shutdown callback cannot retire it twice.
        avatar_state["session"] = None
        identity = avatar_state["identity"]

        async def release() -> None:
            logger.info(
                f"Visitor '{participant.identity}' left; releasing the Anam slot"
            )
            await retire_avatar(avatar, identity, ctx.room.name)

        task = asyncio.create_task(release())
        release_tasks.add(task)
        task.add_done_callback(release_tasks.discard)

    ctx.room.on("participant_disconnected", on_visitor_disconnected)

    assistant = Assistant(ctx.room)

    async def handle_set_language(data: rtc.RpcInvocationData) -> str:
        """Switch the conversation language mid-session, on request from the browser."""
        try:
            payload = json.loads(data.payload or "{}")
        except json.JSONDecodeError:
            return json.dumps({"ok": False, "error": "invalid payload"})

        language = str(payload.get("language", "")).strip().lower()

        if language not in SUPPORTED_LANGUAGES:
            return json.dumps({"ok": False, "error": f"unsupported language: {language}"})

        if language == assistant.language:
            return json.dumps({"ok": True, "language": language, "changed": False})

        config = SUPPORTED_LANGUAGES[language]

        try:
            # Stop any in-flight reply so the switch takes effect immediately rather than
            # after the agent finishes its current sentence.
            await session.interrupt()

            await assistant.update_instructions(build_instructions(language))
            stt.update_options(language=config["stt_code"], detect_language=False)
            assistant.language = language

            session.say(config["confirmation"], allow_interruptions=True)
        except RuntimeError as e:
            # Session not started yet (or already closing) — leave the language untouched.
            logger.warning(f"Language switch to {config['label']} rejected: {e}")
            return json.dumps({"ok": False, "error": "session not ready"})

        logger.info(f"Conversation language switched to {config['label']}")
        return json.dumps({"ok": True, "language": language, "changed": True})

    ctx.room.local_participant.register_rpc_method("set_language", handle_set_language)

    # Serialises avatar switches so a double-click can't start two Anam sessions at once.
    avatar_switch_lock = asyncio.Lock()

    async def handle_switch_avatar(data: rtc.RpcInvocationData) -> str:
        """Swap the on-screen avatar mid-conversation, on request from the browser.

        Anam cannot change avatarId on a live session, and this plan allows only one
        Anam session at a time, so the old avatar is fully torn down before the new one
        starts. The browser shows a loading screen across the gap.

        The AgentSession is rebuilt rather than reused. That is what keeps captions
        paced: the avatar must be started before AgentSession.start(), otherwise the
        avatar's own start() reassigns session.output.audio and permanently detaches the
        transcript synchronizer.

        The conversation survives regardless — the LLM, history and transcript live in
        the AgentSession, and are carried across via session.history -> update_chat_ctx.
        Anam only ever renders a lip-synced face.
        """
        nonlocal session

        try:
            payload = json.loads(data.payload or "{}")
        except json.JSONDecodeError:
            return json.dumps({"ok": False, "error": "invalid payload"})

        avatar_key = str(payload.get("avatar", "")).strip().lower()

        if avatar_key not in SUPPORTED_AVATARS:
            return json.dumps({"ok": False, "error": f"unsupported avatar: {avatar_key}"})

        if avatar_state["session"] is None:
            # Running voice-only (Anam was unavailable at startup) — nothing to swap.
            return json.dumps({"ok": False, "error": "avatar not available"})

        if avatar_key == avatar_state["key"]:
            return json.dumps({"ok": True, "avatar": avatar_key, "changed": False})

        config = SUPPORTED_AVATARS[avatar_key]

        if avatar_switch_lock.locked():
            return json.dumps({"ok": False, "error": "switch already in progress"})

        async with avatar_switch_lock:
            old_avatar = avatar_state["session"]
            old_identity = avatar_state["identity"]
            old_key = avatar_state["key"]
            new_identity = other_avatar_identity(old_identity)

            # Stop any in-flight reply so the switch doesn't cut a sentence in half.
            # force=True because the greeting is deliberately uninterruptible; failing
            # to interrupt is not a reason to abandon the switch.
            try:
                await session.interrupt(force=True)
            except Exception as e:
                logger.debug(f"Nothing to interrupt before avatar switch: {e}")

            # Keep the conversation before tearing anything down. This is the whole
            # reason a switch is survivable: history lives in the AgentSession, not in
            # Anam, so it can be carried into a replacement session verbatim.
            saved_history = session.history.copy()

            # Close the session *first*. The avatar must be started before
            # AgentSession.start(), so there is no live session to start it under —
            # that ordering is what keeps the transcript synchronizer attached.
            # aclose() shuts down RoomIO but leaves the room connected, so the visitor
            # never drops.
            await session.aclose()

            # Only one Anam session may exist at a time on this plan, so the outgoing
            # avatar has to be fully gone before the new one can even be requested.
            # The browser shows a loading screen for the whole of this.
            await retire_avatar(old_avatar, old_identity, ctx.room.name)
            avatar_state["session"] = None
            if not await wait_for_participant_gone(old_identity):
                logger.warning(
                    f"'{old_identity}' still in the room after teardown; "
                    f"continuing anyway"
                )

            new_avatar = None
            try:
                # Order matters: fresh session -> avatar -> session.start().
                session = build_session()
                new_avatar = await start_avatar_with_retry(avatar_key, new_identity)

                # Hold the loading screen until the new face is genuinely on screen.
                if not await wait_for_avatar_video(new_identity):
                    raise RuntimeError(
                        f"'{new_identity}' never published video within the timeout"
                    )

                tts.update_options(voice=config["voice"])
                await assistant.update_chat_ctx(saved_history)
                await session.start(
                    agent=assistant, room=ctx.room, room_options=build_room_options()
                )

            except Exception as e:
                logger.error(f"Avatar switch to {config['label']} failed: {e}")

                # A half-started avatar still holds the only slot, so it has to go
                # before there is any hope of restoring the previous one.
                if new_avatar is not None:
                    await retire_avatar(new_avatar, new_identity, ctx.room.name)
                    await wait_for_participant_gone(new_identity)

                # The old avatar is already gone, so put it back the same way — and
                # bring the conversation with it, so a failed switch still leaves the
                # visitor talking to the receptionist they started with.
                try:
                    recovered_identity = other_avatar_identity(new_identity)
                    tts.update_options(voice=SUPPORTED_AVATARS[old_key]["voice"])

                    session = build_session()
                    avatar_state["session"] = await start_avatar_with_retry(
                        old_key, recovered_identity, timeout=15.0
                    )
                    avatar_state["identity"] = recovered_identity

                    await assistant.update_chat_ctx(saved_history)
                    await session.start(
                        agent=assistant, room=ctx.room, room_options=build_room_options()
                    )
                    logger.info(f"Restored the previous avatar ({old_key})")
                except Exception as inner:
                    logger.error(
                        f"Could not restore the previous avatar either: {inner}. "
                        f"The session could not be rebuilt."
                    )

                return json.dumps({"ok": False, "error": "avatar switch failed"})

            # New avatar is live under a freshly started session.
            avatar_state["session"] = new_avatar
            avatar_state["key"] = avatar_key
            avatar_state["identity"] = new_identity

            # Spoken via generate_reply (not a fixed string) so the confirmation follows
            # whichever language the visitor has locked in.
            try:
                session.generate_reply(
                    instructions=(
                        "You just changed your on-screen appearance at the visitor's "
                        "request. In one short sentence, acknowledge the new look and "
                        "invite them to continue. Do not restart the conversation or "
                        "re-introduce Sandbox Space."
                    )
                )
            except RuntimeError as e:
                logger.warning(f"Could not announce avatar switch: {e}")

        logger.info(f"Avatar switched to {config['label']} (voice: {config['voice']})")
        return json.dumps(
            {
                "ok": True,
                "avatar": avatar_key,
                "identity": avatar_state["identity"],
                "changed": True,
            }
        )

    ctx.room.local_participant.register_rpc_method("switch_avatar", handle_switch_avatar)

    await session.start(
        agent=assistant,
        room=ctx.room,
        room_options=build_room_options(),
    )


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint,
                prewarm_fnc=prewarm,
                # Distinct from the TalentScreen-embedded receptionist ("receptionist-agent")
                # so the two dispatch independently and never steal each other's jobs.
                agent_name="receptionist-standalone-agent",
                # Ports already spoken for on this host: 8080/8082 livekit ingress,
                # 8081 TalentScreen's agent.py, 8083 TalentScreen's receptionist.py.
                # 8084 keeps all four runnable at once instead of crash-looping on
                # "address already in use".
                port=8084))
