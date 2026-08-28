import { Head, usePage } from '@inertiajs/react';
import { ControlBar, LiveKitRoom, RoomAudioRenderer } from '@livekit/components-react';
import '@livekit/components-styles';
import { Room } from 'livekit-client';
import { Mic, MicOff, Video } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import ReceptionistRoom from './room/receptionist-room';

interface Props {
  token: string;
  wsUrl: string;
  roomName: string;
  [key: string]: unknown;
}

export default function Receptionist() {
  const { token, wsUrl } = usePage<Props>().props;

  const [started, setStarted] = useState(false);
  const [micEnabled, setMicEnabled] = useState(true);
  const [sessionEnded, setSessionEnded] = useState(false);

  // Frozen when the session starts: `audio` is a connect-time option, and letting
  // it change afterwards would re-run LiveKitRoom's connect effect. Mid-call
  // muting is the ControlBar's job.
  const [micAtStart, setMicAtStart] = useState(true);

  // One Room for the life of the page. LiveKitRoom builds its own room from the
  // props otherwise, and any re-render that changes a prop identity tears the
  // connection down and reconnects — which dropped the avatar mid-greeting.
  const room = useMemo(() => new Room(), []);

  const handleDisconnect = useCallback(() => {
    setStarted(false);
    setSessionEnded(true);
  }, []);

  const restart = () => {
    // A fresh session needs a fresh room and token, so reload rather than
    // reconnecting with the spent one.
    window.location.reload();
  };

  if (started && !sessionEnded) {
    return (
      <>
        <Head title="Receptionist" />
        <div className="h-screen w-screen overflow-hidden bg-black">
          <LiveKitRoom
            className="relative h-full w-full overflow-hidden"
            room={room}
            video={false}
            audio={micAtStart}
            token={token}
            serverUrl={wsUrl}
          >
            <ReceptionistRoom onDisconnect={handleDisconnect} />

            <RoomAudioRenderer />
            <div className="absolute bottom-4 left-1/2 z-10 -translate-x-1/2">
              <ControlBar
                controls={{ screenShare: false, camera: false, leave: false }}
                data-lk-theme="default"
              />
            </div>
          </LiveKitRoom>
        </div>
      </>
    );
  }

  return (
    <>
      <Head title="Receptionist" />

      <div className="flex h-screen w-screen items-center justify-center overflow-hidden bg-slate-950 px-6 text-center">
        <div className="flex max-w-md flex-col items-center">
          {sessionEnded ? (
            <>
              <div className="mb-6 text-6xl">👋</div>
              <h1 className="mb-3 text-3xl font-semibold text-white">Session ended</h1>
              <p className="mb-10 text-slate-400">
                Thanks for chatting with the Sandbox Space receptionist.
              </p>
              <button
                type="button"
                onClick={restart}
                className="rounded-full bg-white px-8 py-4 text-base font-medium text-slate-950 transition hover:bg-slate-200"
              >
                Start a new session
              </button>
            </>
          ) : (
            <>
              <div className="mb-8 flex h-20 w-20 items-center justify-center rounded-2xl bg-white/10">
                <Video className="h-9 w-9 text-white" strokeWidth={1.5} />
              </div>

              <h1 className="mb-3 text-4xl font-semibold text-white">Sandbox Receptionist</h1>
              <p className="mb-10 text-slate-400">
                Say hello to our virtual receptionist. Ask about the space, the facilities,
                or anything else — in English, 中文 or Bahasa Melayu.
              </p>

              <button
                type="button"
                onClick={() => {
                  setMicAtStart(micEnabled);
                  setStarted(true);
                }}
                className="mb-6 rounded-full bg-white px-10 py-4 text-base font-medium text-slate-950 transition hover:bg-slate-200"
              >
                Start session
              </button>

              <button
                type="button"
                onClick={() => setMicEnabled((on) => !on)}
                className="flex items-center gap-2 text-sm text-slate-400 transition hover:text-white"
              >
                {micEnabled ? (
                  <>
                    <Mic className="h-4 w-4" /> Microphone on
                  </>
                ) : (
                  <>
                    <MicOff className="h-4 w-4" /> Microphone off
                  </>
                )}
              </button>

              <p className="mt-8 text-xs text-slate-600">
                Your browser will ask for microphone access after you start.
              </p>
            </>
          )}
        </div>
      </div>
    </>
  );
}
