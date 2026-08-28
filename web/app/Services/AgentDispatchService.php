<?php

namespace App\Services;

use Agence104\LiveKit\AccessToken;
use Agence104\LiveKit\AccessTokenOptions;
use Agence104\LiveKit\VideoGrant;
use Livekit\AgentDispatchServiceClient;
use Livekit\CreateAgentDispatchRequest;
use Twirp\Context;

class AgentDispatchService
{
    private string $host;
    private string $apiKey;
    private string $apiSecret;

    public function __construct()
    {
        $this->host = config('livekit.host');
        $this->apiKey = config('livekit.api_key');
        $this->apiSecret = config('livekit.api_secret');
    }

    public function dispatch(string $roomName, string $agentName = 'receptionist-standalone-agent'): void
    {
        $ctx = Context::withHttpRequestHeaders([], [
            'Authorization' => 'Bearer ' . $this->makeToken($roomName),
        ]);

        $client = new AgentDispatchServiceClient($this->host);

        $request = new CreateAgentDispatchRequest([
            'agent_name' => $agentName,
            'room' => $roomName,
        ]);

        $client->CreateDispatch($ctx, $request);
    }

    private function makeToken(string $roomName): string
    {
        $tokenOptions = (new AccessTokenOptions())->setTtl(600);

        $videoGrant = (new VideoGrant())
            ->setRoomName($roomName)
            ->setRoomAdmin();

        return (new AccessToken($this->apiKey, $this->apiSecret))
            ->init($tokenOptions)
            ->setGrant($videoGrant)
            ->toJwt();
    }
}
