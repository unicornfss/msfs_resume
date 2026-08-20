# How to use MSFS Resume

MSFS Resume records a restore point after takeoff and can put you back near that position after a crash or return to the menu. It does not restore FMC/MCDU, switches, or full airliner panel state.

Contact: ostroforge@outlook.com

Virtual airlines are welcome to email about incorporating resume into their own flight-logging software. For freeware VAs that help is free of charge. No timescale or successful implementation is guaranteed.

## Typical flight

1. Start MSFS Resume (it may sit in the system tray — look for the gold icon near the clock).
2. Optional: File → Settings and enter your SimBrief username or numeric ID.
3. Fly as normal. Recording starts when the aircraft leaves the ground.
4. If the sim crashes or you return to the menu, a popup appears. Choose Resume flight.
5. Spawn at the suggested nearby airport (Copy spawn ICAO if useful). Must-match items (aircraft, fuel, engines) have to be right before Restore is available. Useful items (QNH, sim time, heading, next waypoint, gear/flaps) are for you to set.
6. Click Restore flight. If the warp is wrong, pick an earlier restore point from the list. After a successful restore, recording continues.
7. Recording ends when you are parked with engines off.

## Resume vs new flight

If an incomplete flight is found at startup, choose Resume or Start new. Taking off without choosing is treated as a new flight.

If you chose Resume, taking off to configure the aircraft will not start a new flight and will not overwrite the saved restore point. Recording only continues after a successful restore.

## Settings

File → Settings:

- SimBrief username or ID — latest OFP is attached when a new takeoff is recorded
- Fuel restore tolerance — how close current fuel must be to the saved value
- Always on top
- Start in the system tray
- Show a reminder when starting in the tray

## Exit

The title-bar close button is disabled. Use File → Exit.

If a flight is recording you will be asked to Cancel, Minimise to the tray, or Exit. Minimise keeps recording in the background.

## Logs and updates

Help → Error log — restore failures and other errors. You can email the log to ostroforge@outlook.com.

Help → Check for updates — if a newer version is available you are asked, then the installer is downloaded. You can run it straight away; MSFS Resume closes so the files can be replaced.

Help → Changelog — what changed in each version.

## Data stored on this PC

%AppData%\MsfsResume\

- last_snapshot.json — latest restore point
- snapshot_history.json — last few restore points
- settings.json
- airports_cache.json
- error.log
