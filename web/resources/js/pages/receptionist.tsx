import { Head, usePage } from '@inertiajs/react';
import { ControlBar, LiveKitRoom, PreJoin, RoomAudioRenderer } from '@livekit/components-react';
import '@livekit/components-styles';
import { useState } from 'react';
import ReceptionistRoom from './room/receptionist-room';

interface Props {
  token: string;
  wsUrl: string;
  roomName: string;
  [key: string]: unknown;
}

type UserChoices = {
  videoEnabled: boolean;
  audioEnabled: boolean;
  username?: string;
};

export default function Receptionist() {
  const { token, wsUrl } = usePage<Props>().props;

  const [userChoices, setUserChoices] = useState<UserChoices | null>(null);
  const [sessionEnded, setSessionEnded] = useState(false);

  const handleDisconnect = () => {
    setSessionEnded(true);
  };

  return (
    <>
      <Head title="Receptionist" />

      {userChoices && !sessionEnded ? (
        <div className="h-screen w-screen overflow-hidden bg-black">
          <LiveKitRoom
            className="relative h-full w-full overflow-hidden"
            video={userChoices.videoEnabled}
            audio={userChoices.audioEnabled}
            token={token}
            serverUrl={wsUrl}
          >
            <ReceptionistRoom onDisconnect={handleDisconnect} />

            <RoomAudioRenderer />
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10">
              <ControlBar controls={{ screenShare: false, camera: false, leave: false }} data-lk-theme="default" />
            </div>
          </LiveKitRoom>
        </div>
      ) : (
        <div className="h-screen overflow-hidden bg-background flex flex-col">
          <div className="flex-1 min-h-0 w-full max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col py-4">
            {sessionEnded ? (
              <div className="flex flex-1 flex-col items-center justify-center text-center">
                <h1 className="text-7xl mb-4">👋</h1>
                <h1 className="text-3xl font-bold text-gray-900 mb-4">Session Ended</h1>
                <p className="text-lg text-gray-600 mb-8">
                  Thanks for chatting with the Sandbox Space receptionist.
                </p>
              </div>
            ) : (
              <div className="flex flex-1 items-center justify-center">
                <PreJoin
                  data-lk-theme="default"
                  onSubmit={(values) => setUserChoices(values)}
                  defaults={{ username: 'Visitor' }}
                />
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
