import { useLocalParticipant, useParticipants, useRoomContext, useVoiceAssistant, VideoTrack } from '@livekit/components-react';
import '@livekit/components-styles';
import { RoomEvent, Track, TranscriptionSegment } from 'livekit-client';
import { Languages, MessageSquare, UserRound, Volume2, VolumeX, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

interface ReceptionistRoomProps {
  onDisconnect: () => void;
}

interface TranscriptEntry {
  id: string;
  text: string;
  isAgent: boolean;
  receivedAt: number;
}

// Must stay in sync with SUPPORTED_LANGUAGES in agent/receptionist.py
const LANGUAGES = [
  { code: 'english', label: 'English' },
  { code: 'chinese', label: '中文' },
  { code: 'malay', label: 'Bahasa Melayu' },
] as const;

// Must stay in sync with SUPPORTED_AVATARS in agent/receptionist.py
const AVATARS = [
  { code: 'carl', label: 'Carl' },
  { code: 'cara', label: 'Cara' },
] as const;

function stripMarkdown(text: string): string {
  return text
    .replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/\*(.+?)\*/g, '$1')
    .replace(/__(.+?)__/g, '$1')
    .replace(/_(.+?)_/g, '$1')
    .replace(/`(.+?)`/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[-*+]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .trim();
}

// Avatars alternate between `receptionist-avatar` and `receptionist-avatar-b` while
// switching, so match on the prefix rather than one exact identity.
function isAgentIdentity(identity: string): boolean {
  return identity.startsWith('agent-') || identity.startsWith('receptionist-avatar');
}

export default function ReceptionistRoom({ onDisconnect }: ReceptionistRoomProps) {
  const participants = useParticipants();
  const agent = participants.find((participant) => participant.isAgent);
  // Which avatar participant to render. The agent reports the new identity when a
  // switch completes; until then the outgoing avatar stays on screen.
  const [avatarIdentity, setAvatarIdentity] = useState<string>('receptionist-avatar');
  const receptionistAvatar = participants.find((participant) => participant.identity === avatarIdentity);

  const room = useRoomContext();
  const { localParticipant } = useLocalParticipant();
  const { state: agentState } = useVoiceAssistant();
  const [isMuted, setIsMuted] = useState(false);
  const [caption, setCaption] = useState<{ text: string; final: boolean } | null>(null);
  const [transcript, setTranscript] = useState<TranscriptEntry[]>([]);
  const [showTranscript, setShowTranscript] = useState(false);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const [language, setLanguage] = useState<string>('english');
  const [showLanguageMenu, setShowLanguageMenu] = useState(false);
  const [isSwitchingLanguage, setIsSwitchingLanguage] = useState(false);
  const [avatar, setAvatar] = useState<string>('carl');
  const [isSwitchingAvatar, setIsSwitchingAvatar] = useState(false);

  // RPC must target the agent worker itself. `receptionist-avatar` only renders video,
  // so sending there would silently fail.
  const agentParticipant = participants.find((participant) => participant.identity.startsWith('agent-'));

  const handleLanguageChange = async (code: string) => {
    if (!room || !agentParticipant || code === language || isSwitchingLanguage) return;

    setIsSwitchingLanguage(true);
    try {
      await room.localParticipant.performRpc({
        destinationIdentity: agentParticipant.identity,
        method: 'set_language',
        payload: JSON.stringify({ language: code }),
        responseTimeout: 10000,
      });
      setLanguage(code);
      setShowLanguageMenu(false);
    } catch (error) {
      console.error('Failed to switch language', error);
    } finally {
      setIsSwitchingLanguage(false);
    }
  };

  // Anam can't change the avatar on a live session, so the agent runs a second one
  // alongside the first and only cuts over once it's publishing video. The RPC resolves
  // after that cutover, so flipping to the new identity here is safe — the old avatar
  // stays on screen until this returns.
  const handleAvatarChange = async () => {
    if (!room || !agentParticipant || isSwitchingAvatar || isSwitchingLanguage) return;

    const next = avatar === 'carl' ? 'cara' : 'carl';

    setIsSwitchingAvatar(true);
    try {
      const raw = await room.localParticipant.performRpc({
        destinationIdentity: agentParticipant.identity,
        method: 'switch_avatar',
        payload: JSON.stringify({ avatar: next }),
        // Generous: teardown + waiting for Anam to release the slot + the new avatar's
        // first video frame can legitimately stack up to ~50s in the worst case.
        responseTimeout: 60000,
      });

      const result = JSON.parse(raw) as { ok: boolean; identity?: string; error?: string };
      if (!result.ok) {
        console.error('Avatar switch rejected', result.error);
        return;
      }
      setAvatar(next);
      if (result.identity) setAvatarIdentity(result.identity);
    } catch (error) {
      console.error('Failed to switch avatar', error);
    } finally {
      setIsSwitchingAvatar(false);
    }
  };

  useEffect(() => {
    document.querySelectorAll('audio').forEach((a) => {
      (a as HTMLAudioElement).muted = isMuted;
    });
  }, [isMuted]);

  useEffect(() => {
    localParticipant.setMicrophoneEnabled(agentState === 'listening');
  }, [agentState, localParticipant]);

  useEffect(() => {
    if (!room) return;

    const handleTranscription = (segments: TranscriptionSegment[], participant?: { identity: string }) => {
      const identity = participant?.identity;
      if (!identity) return;

      const fromAgent = isAgentIdentity(identity);

      // On-screen caption stays agent-only and shows just the latest segment.
      if (fromAgent) {
        const latest = segments[segments.length - 1];
        if (latest) {
          const latestText = stripMarkdown(latest.text);
          if (latestText) setCaption({ text: latestText, final: latest.final });
        }
      }

      // Full history keeps both sides. Segments stream in and are updated in place,
      // so upsert by segment id rather than appending blindly.
      setTranscript((prev) => {
        const next = [...prev];

        for (const segment of segments) {
          const text = stripMarkdown(segment.text);
          if (!text) continue;

          const existingIndex = next.findIndex((entry) => entry.id === segment.id);

          if (existingIndex === -1) {
            next.push({
              id: segment.id,
              text,
              isAgent: fromAgent,
              receivedAt: segment.firstReceivedTime ?? Date.now(),
            });
          } else {
            next[existingIndex] = { ...next[existingIndex], text };
          }
        }

        return next.sort((a, b) => a.receivedAt - b.receivedAt);
      });
    };

    room.on(RoomEvent.TranscriptionReceived, handleTranscription);
    return () => { room.off(RoomEvent.TranscriptionReceived, handleTranscription); };
  }, [room]);

  useEffect(() => {
    if (!showTranscript) return;
    transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [transcript, showTranscript]);

  useEffect(() => {
    if (!room) return;
    const handleDisconnected = () => {
      if (room.state === 'disconnected') {
        onDisconnect();
      }
    };
    room.on('disconnected', handleDisconnected);
    return () => { room.off('disconnected', handleDisconnected); };
  }, [room, onDisconnect]);

  useEffect(() => {
    if (!room) return;
    const timer = setTimeout(() => { room.disconnect(); }, 1200000);
    return () => clearTimeout(timer);
  }, [room]);

  return (
    <div className="absolute inset-0 h-full w-full bg-black">
      {receptionistAvatar ? (
        <VideoTrack
          className="h-full w-full object-contain"
          trackRef={{
            participant: receptionistAvatar,
            source: Track.Source.Camera,
            publication: receptionistAvatar.getTrackPublication(Track.Source.Camera)!,
          }}
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center">
          <span className="text-sm font-medium text-white/70">
            {agent ? 'Connecting…' : 'Waiting for receptionist…'}
          </span>
        </div>
      )}

      {/* Full cover on purpose: only one Anam session may exist at a time, so the old
          avatar is torn down before the new one starts. This hides the empty video area
          for the few seconds in between and makes the wait read as intentional. */}
      {isSwitchingAvatar && (
        <div className="absolute inset-0 z-30 flex flex-col items-center justify-center gap-4 bg-black">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-white/20 border-t-white" />
          <div className="flex flex-col items-center gap-1">
            <span className="text-sm font-medium text-white">
              Switching to {AVATARS.find((a) => a.code !== avatar)?.label}…
            </span>
            <span className="text-xs text-white/50">
              Your conversation will continue where you left off
            </span>
          </div>
        </div>
      )}

      <button
        onClick={() => setShowTranscript((s) => !s)}
        title={showTranscript ? 'Hide transcript' : 'Show transcript'}
        className="absolute top-4 left-4 z-20 flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm hover:bg-black/80 transition-colors"
      >
        <MessageSquare className="h-3.5 w-3.5" />
        Transcript
      </button>

      <button
        onClick={() => setIsMuted((m) => !m)}
        title={isMuted ? 'Unmute' : 'Mute'}
        className="absolute top-4 right-4 z-10 flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm hover:bg-black/80 transition-colors"
      >
        {isMuted ? <VolumeX className="h-3.5 w-3.5" /> : <Volume2 className="h-3.5 w-3.5" />}
        {isMuted ? 'Unmute' : 'Mute'}
      </button>

      <div className="absolute top-16 right-4 z-20 flex flex-col items-end gap-2">
        <button
          onClick={() => setShowLanguageMenu((s) => !s)}
          disabled={!agentParticipant || isSwitchingLanguage}
          title="Change language"
          className="flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm transition-colors hover:bg-black/80 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Languages className="h-3.5 w-3.5" />
          {isSwitchingLanguage
            ? 'Switching…'
            : LANGUAGES.find((l) => l.code === language)?.label ?? 'English'}
        </button>

        {showLanguageMenu && (
          <div className="flex w-40 flex-col overflow-hidden rounded-xl bg-black/70 backdrop-blur-sm">
            {LANGUAGES.map((option) => (
              <button
                key={option.code}
                onClick={() => handleLanguageChange(option.code)}
                disabled={isSwitchingLanguage}
                className={`px-3 py-2 text-left text-xs font-medium transition-colors hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50 ${
                  option.code === language ? 'text-white' : 'text-white/70'
                }`}
              >
                {option.label}
                {option.code === language && ' ✓'}
              </button>
            ))}
          </div>
        )}

        <button
          onClick={handleAvatarChange}
          disabled={!agentParticipant || isSwitchingAvatar || isSwitchingLanguage}
          title={`Switch to ${AVATARS.find((a) => a.code !== avatar)?.label}`}
          className="flex items-center gap-1.5 rounded-full bg-black/60 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-sm transition-colors hover:bg-black/80 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <UserRound className="h-3.5 w-3.5" />
          {isSwitchingAvatar
            ? 'Switching…'
            : AVATARS.find((a) => a.code === avatar)?.label ?? 'Carl'}
        </button>
      </div>

      {showTranscript && (
        <div className="absolute top-16 left-4 z-20 flex max-h-[70%] w-[min(22rem,calc(100%-2rem))] flex-col overflow-hidden rounded-xl bg-black/70 backdrop-blur-sm">
          <div className="flex items-center justify-between border-b border-white/10 px-4 py-2.5">
            <span className="text-xs font-semibold text-white">Conversation</span>
            <button
              onClick={() => setShowTranscript(false)}
              title="Close transcript"
              className="rounded-full p-1 text-white/70 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto px-4 py-3">
            {transcript.length === 0 ? (
              <p className="text-xs text-white/50">No conversation yet.</p>
            ) : (
              transcript.map((entry) => (
                <div key={entry.id} className={entry.isAgent ? 'text-left' : 'text-right'}>
                  <p className="mb-0.5 text-[10px] font-medium uppercase tracking-wide text-white/40">
                    {entry.isAgent ? 'Receptionist' : 'You'}
                  </p>
                  <p
                    className={`inline-block max-w-[90%] rounded-lg px-2.5 py-1.5 text-xs leading-relaxed ${
                      entry.isAgent ? 'bg-white/10 text-white' : 'bg-blue-600/80 text-white'
                    }`}
                  >
                    {entry.text}
                  </p>
                </div>
              ))
            )}
            <div ref={transcriptEndRef} />
          </div>
        </div>
      )}

      {caption && (
        <div className="absolute bottom-20 left-1/2 z-10 max-w-[80%] -translate-x-1/2 rounded-xl bg-black/60 px-4 py-2 text-center text-sm font-medium text-white backdrop-blur-sm">
          {caption.text}
        </div>
      )}
    </div>
  );
}
