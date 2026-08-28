<?php

namespace App\Http\Controllers;

use App\Services\AgentDispatchService;
use Agence104\LiveKit\AccessToken;
use Agence104\LiveKit\AccessTokenOptions;
use Agence104\LiveKit\RoomCreateOptions;
use Agence104\LiveKit\RoomServiceClient;
use Agence104\LiveKit\VideoGrant;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Inertia\Inertia;

class ReceptionistController extends Controller
{
    public function start(AgentDispatchService $agentDispatch)
    {
        $roomName = 'Sandbox Receptionist - ' . Str::uuid();

        $svc = new RoomServiceClient(config('livekit.host'), config('livekit.api_key'), config('livekit.api_secret'));
        $svc->createRoom(new RoomCreateOptions([
            'name' => $roomName,
            // Headroom for the avatar switch, which briefly runs two Anam avatars in
            // the room at once so the outgoing one can keep talking until the new one
            // is live. Agent-kind participants appear not to count toward this, but
            // the cap is cheap insurance.
            'maxParticipants' => 4,
            'emptyTimeout' => 60,
        ]));

        // This dashboard has no login, so there is no account name to identify the
        // visitor by. It must still be unique per session: LiveKit evicts an existing
        // participant when a second one joins under the same identity, so a constant
        // here would let a new visitor kick the previous one out of their room.
        $identity = 'Visitor-' . Str::random(6);

        $tokenOptions = (new AccessTokenOptions())
            ->setIdentity($identity)
            ->setName($identity)
            ->setTtl(3600);

        $videoGrant = (new VideoGrant())
            ->setRoomJoin()
            ->setRoomName($roomName);

        $token = (new AccessToken(config('livekit.api_key'), config('livekit.api_secret')))
            ->init($tokenOptions)
            ->setGrant($videoGrant)
            ->toJwt();

        try {
            $agentDispatch->dispatch($roomName, 'receptionist-standalone-agent');
        } catch (\Throwable $e) {
            Log::warning('Receptionist agent dispatch failed', ['error' => $e->getMessage(), 'room' => $roomName]);
        }

        return Inertia::render('receptionist', [
            'token' => $token,
            'wsUrl' => config('livekit.url'),
            'roomName' => $roomName,
        ]);
    }
}
