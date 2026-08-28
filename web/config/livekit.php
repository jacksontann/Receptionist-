<?php

return [
    /*
    |----------------------------------------------------------------------
    | LiveKit WebSocket URL
    |----------------------------------------------------------------------
    |
    | Handed to the browser so the client SDK can join the room.
    |
    */

    'url' => env('LIVEKIT_URL'),

    /*
    |--------------------------------------------------------------------------
    | LiveKit Host (for server-side API calls)
    |--------------------------------------------------------------------------
    |
    | The https:// endpoint this backend uses to create rooms and dispatch the
    | agent. Deliberately separate from 'url' above, which is the ws:// one.
    |
    */

    'host' => env('LIVEKIT_HOST'),

    /*
    |----------------------------------------------------------------------
    | LiveKit API credentials
    |----------------------------------------------------------------------
    |
    | No fallback values on purpose: a missing .env should fail loudly rather
    | than silently connecting to somebody else's LiveKit project.
    |
    */

    'api_key' => env('LIVEKIT_API_KEY'),

    'api_secret' => env('LIVEKIT_API_SECRET'),
];
