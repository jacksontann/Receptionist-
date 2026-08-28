<?php

use App\Http\Controllers\ReceptionistController;
use Illuminate\Support\Facades\Route;

// The whole app is this one page: opening it provisions a LiveKit room, mints a
// visitor token and dispatches the receptionist agent into it. No auth by design —
// this is a public-facing kiosk-style receptionist.
Route::get('/', [ReceptionistController::class, 'start'])->name('receptionist.start');
