# MSFS Resume

Freeware restore helper for Microsoft Flight Simulator 2020 and 2024. After a crash or return to the menu it can put you back near the last recorded airborne position.

This is **not** a virtual airline client and it does **not** restore FMC/MCDU or full airliner panel state.

**Licence:** free for personal, non-commercial use. You may not sell it or use it to make a profit. See `LICENSE.txt`.

**Contact:** ostroforge@outlook.com

Virtual airlines are welcome to get in touch about incorporating resume into their own flight-logging software. For freeware VAs that assistance is free of charge. No timescale or successful implementation is guaranteed.

## Install

Download `MSFSResumeSetup-0.4.3.exe` from [Releases](https://github.com/unicornfss/msfs_resume/releases) and run it. The installer does not need administrator rights.

Portable copy: unzip or copy the `MSFSResume` folder and run `MSFSResume.exe`.

## Run from source

```
pip install -r requirements.txt
python -m msfs_resume
```

Or double-click `run.bat`.

## How it works

- Recording starts at takeoff and ends when you are parked with engines off.
- If the sim crashes, choose **Resume flight** on the next launch.
- Spawn near the suggested airport, set fuel, configure the aircraft, then click **Restore**.
- SimBrief username, fuel tolerance and always-on-top are under **File → Settings**.
- Exit is **File → Exit**. If a flight is recording you can cancel, minimise to the tray, or exit.
- Failures are written to `%AppData%\MsfsResume\error.log` (**Help → Error log**). You can email that log from the same screen.
- **Help → Check for updates** downloads the installer and can run it.

See `HELP.md` for the full guide.

## Build the installer

1. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php) (optional, for `MSFSResumeSetup-*.exe`).
2. From the repo root:

```
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

Output:

- `dist\MSFSResume\` — portable app folder
- `dist\MSFSResumeSetup-0.4.3.exe` — Windows installer (if Inno Setup is installed)

After the repo exists, publish a Release with the installer attached so in-app update checks can find it.
