# Changelog

All notable changes to MSFS Resume are listed here.

## 0.4.4

- Restore card shows QNH and simulator time
- Copy spawn ICAO to the clipboard
- Last few restore points kept (about every 2 minutes or 10 nm) so an earlier point can be chosen
- Starts in the system tray, with a reminder that can be turned off
- Popup if an incomplete flight is found on launch, and if a sim crash / return to menu is detected
- Next waypoint estimated from SimBrief navlog (recording and restore screens)
- Restore checklist split into Must match (sim, aircraft, fuel, engines) and Useful to set (QNH, time, heading, spawn, gear/flaps)

## 0.4.3

- Check for updates downloads the installer and can run it (the app closes so files can be replaced)
- Smaller installer by omitting unused image codecs (especially AVIF)
- Icon is a gold disc with a navy resume mark (readable in the title bar)

## 0.4.2

- New app icon in the title bar, Start menu and tray (navy disc with a resume play mark)
- Use this release to confirm Help → Check for updates from 0.4.1

## 0.4.1

- Fix installer launch crash (`attempted relative import with no known parent package`)

## 0.4.0

- File and Help menus; SimBrief, fuel tolerance and always-on-top moved to Settings
- How to use, changelog, About and contact under Help
- Title-bar close button removed; Exit is under File
- Exit confirmation while a flight is recording (Cancel / Minimise / Exit)
- Error log with option to email ostroforge@outlook.com
- Changelog and About screens
- Check for updates on startup and from Help (you are asked before downloading)
- Windows installer package
- Freeware licence for personal non-commercial use
- Virtual airlines may contact ostroforge@outlook.com about integrating resume into their logging software (freeware VAs: no charge; no timescale or success guarantee)

## 0.3.2

- Choosing Resume no longer starts a new flight if you take off to configure the aircraft

## 0.3.1

- Minimise sends the app to the system tray

## 0.3.0

- Startup prompt for an incomplete flight vs a new flight
- Live Flight recording view
- SimBrief OFP attached on takeoff
- Nearest suitable airport suggestion for resume spawn

## 0.2.0

- Recording starts at takeoff and ends when parked with engines off

## 0.1.1

- Start new flight control

## 0.1.0

- First local resume app: SimConnect snapshot, fuel min/max, heading and IAS warp
