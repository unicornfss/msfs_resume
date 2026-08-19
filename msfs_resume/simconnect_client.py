"""Minimal ctypes SimConnect client for snapshot + INITPOSITION restore."""

from __future__ import annotations

import ctypes
import threading
import time
from ctypes import POINTER, WINFUNCTYPE, HRESULT, Structure, byref, c_char, c_char_p, c_double, c_float, c_void_p, sizeof
from ctypes.wintypes import DWORD, HANDLE, HWND
from pathlib import Path

from .paths import bundle_dir
from .snapshot import FlightSnapshot, utc_now_iso

OBJECT_ID_USER = 0
UNUSED = 0xFFFFFFFF
GROUP_PRIORITY_HIGHEST = 1
EVENT_FLAG_GROUPID_IS_PRIORITY = 0x10

RECV_EXCEPTION = 1
RECV_OPEN = 2
RECV_QUIT = 3
RECV_EVENT = 4
RECV_SIMOBJECT_DATA = 8

DATATYPE_FLOAT64 = 4
DATATYPE_STRING256 = 9
DATATYPE_INITPOSITION = 12

PERIOD_SECOND = 4

DEF_SNAPSHOT = 1
DEF_POSITION = 2
DEF_FUEL = 3
REQ_SNAPSHOT = 1

EVT_PAUSE_SET = 1
EVT_SIM_START = 2
EVT_SIM_STOP = 3

DOUBLE_FIELDS = (
    ("PLANE LATITUDE", b"degrees"),
    ("PLANE LONGITUDE", b"degrees"),
    ("PLANE ALTITUDE", b"feet"),
    ("PLANE HEADING DEGREES MAGNETIC", b"degrees"),
    ("PLANE HEADING DEGREES TRUE", b"degrees"),
    ("AIRSPEED INDICATED", b"knots"),
    ("AIRSPEED TRUE", b"knots"),
    ("VERTICAL SPEED", b"feet per minute"),
    ("PLANE PITCH DEGREES", b"degrees"),
    ("PLANE BANK DEGREES", b"degrees"),
    ("SIM ON GROUND", b"Bool"),
    ("FUEL TOTAL QUANTITY WEIGHT", b"pounds"),
    ("FUEL TOTAL QUANTITY", b"gallons"),
    ("FUEL TOTAL CAPACITY", b"gallons"),
    ("FUEL WEIGHT PER GALLON", b"pounds"),
    ("ENG COMBUSTION:1", b"Bool"),
    ("ENG COMBUSTION:2", b"Bool"),
    ("ENG COMBUSTION:3", b"Bool"),
    ("ENG COMBUSTION:4", b"Bool"),
    ("AUTOPILOT MASTER", b"Bool"),
    ("CAMERA STATE", b"Number"),
    ("IS SLEW ACTIVE", b"Bool"),
)

# Cockpit / chase / drone-style views. World map and menus sit outside this set.
IN_WORLD_CAMERAS = {2, 3, 4, 5, 6, 7, 8, 9}


class Recv(Structure):
    _pack_ = 1
    _fields_ = [("dwSize", DWORD), ("dwVersion", DWORD), ("dwID", DWORD)]


class RecvException(Structure):
    _pack_ = 1
    _fields_ = [
        ("dwSize", DWORD),
        ("dwVersion", DWORD),
        ("dwID", DWORD),
        ("dwException", DWORD),
        ("dwSendID", DWORD),
        ("dwIndex", DWORD),
    ]


class RecvEvent(Structure):
    _pack_ = 1
    _fields_ = [
        ("dwSize", DWORD),
        ("dwVersion", DWORD),
        ("dwID", DWORD),
        ("uGroupID", DWORD),
        ("uEventID", DWORD),
        ("dwData", DWORD),
    ]


class RecvOpen(Structure):
    _pack_ = 1
    _fields_ = [
        ("dwSize", DWORD),
        ("dwVersion", DWORD),
        ("dwID", DWORD),
        ("szApplicationName", c_char * 256),
        ("dwApplicationVersionMajor", DWORD),
        ("dwApplicationVersionMinor", DWORD),
        ("dwApplicationBuildMajor", DWORD),
        ("dwApplicationBuildMinor", DWORD),
        ("dwSimConnectVersionMajor", DWORD),
        ("dwSimConnectVersionMinor", DWORD),
        ("dwSimConnectBuildMajor", DWORD),
        ("dwSimConnectBuildMinor", DWORD),
        ("dwReserved1", DWORD),
        ("dwReserved2", DWORD),
    ]


class SnapshotPayload(Structure):
    _pack_ = 1
    _fields_ = [(f"d{i}", c_double) for i in range(len(DOUBLE_FIELDS))] + [
        ("title", c_char * 256)
    ]


class RecvSimObjectData(Structure):
    _pack_ = 1
    _fields_ = [
        ("dwSize", DWORD),
        ("dwVersion", DWORD),
        ("dwID", DWORD),
        ("dwRequestID", DWORD),
        ("dwObjectID", DWORD),
        ("dwDefineID", DWORD),
        ("dwFlags", DWORD),
        ("dwEntryNumber", DWORD),
        ("dwOutOf", DWORD),
        ("dwDefineCount", DWORD),
        ("data", SnapshotPayload),
    ]


class InitPosition(Structure):
    _pack_ = 1
    _fields_ = [
        ("Latitude", c_double),
        ("Longitude", c_double),
        ("Altitude", c_double),
        ("Pitch", c_double),
        ("Bank", c_double),
        ("Heading", c_double),
        ("OnGround", DWORD),
        ("Airspeed", DWORD),
    ]


DispatchProc = WINFUNCTYPE(None, POINTER(Recv), DWORD, c_void_p)


def _ok(hr: int) -> bool:
    return (hr & 0xFFFFFFFF) == 0


def _vendor_dir() -> Path:
    return bundle_dir() / "vendor"


def find_simconnect_dlls() -> list[Path]:
    candidates = [
        _vendor_dir() / "SimConnect.dll",
        _vendor_dir() / "SimConnect_2024.dll",
        Path(r"C:\MSFS SDK\SimConnect SDK\lib\SimConnect.dll"),
        Path(r"C:\MSFS Addons\Addon Linker\Simconnect_2024\SimConnect.dll"),
        Path(r"C:\MSFS Addons\Addon Linker\SimConnect.dll"),
    ]
    found: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve()) if path.exists() else ""
        if path.exists() and key not in seen:
            found.append(path)
            seen.add(key)
    return found


def _decode_title(raw: bytes) -> str:
    return raw.split(b"\x00", 1)[0].decode("utf-8", errors="ignore").strip()


class LiveData:
    def __init__(self) -> None:
        self.connected = False
        self.sim_name = ""
        self.sim_running = False
        self.exception: str | None = None
        self.status = "Waiting for Microsoft Flight Simulator"
        self.aircraft = ""
        self.latitude = 0.0
        self.longitude = 0.0
        self.altitude_ft = 0.0
        self.heading_mag = 0.0
        self.heading_true = 0.0
        self.ias_kt = 0.0
        self.tas_kt = 0.0
        self.vertical_speed_fpm = 0.0
        self.pitch_deg = 0.0
        self.bank_deg = 0.0
        self.on_ground = True
        self.fuel_lb = 0.0
        self.fuel_gal = 0.0
        self.fuel_capacity_gal = 0.0
        self.fuel_lb_per_gal = 6.7
        self.engines_running = False
        self.autopilot = False
        self.camera_state = 0
        self.slew = False
        self.updated_at = 0.0

    @property
    def in_world(self) -> bool:
        if not self.connected or not self.aircraft:
            return False
        if self.slew:
            return False
        if abs(self.latitude) + abs(self.longitude) < 0.01:
            return False
        cam = int(self.camera_state)
        if cam and cam not in IN_WORLD_CAMERAS:
            return False
        if self.sim_running or cam in IN_WORLD_CAMERAS:
            return True
        return (not self.on_ground) or self.ias_kt > 20 or self.altitude_ft > 50

    def to_snapshot(self) -> FlightSnapshot:
        return FlightSnapshot(
            saved_at=utc_now_iso(),
            aircraft=self.aircraft,
            latitude=self.latitude,
            longitude=self.longitude,
            altitude_ft=self.altitude_ft,
            heading_mag=self.heading_mag,
            heading_true=self.heading_true,
            ias_kt=self.ias_kt,
            tas_kt=self.tas_kt,
            vertical_speed_fpm=self.vertical_speed_fpm,
            pitch_deg=self.pitch_deg,
            bank_deg=self.bank_deg,
            on_ground=self.on_ground,
            fuel_lb=self.fuel_lb,
            fuel_gal=self.fuel_gal,
            fuel_capacity_gal=self.fuel_capacity_gal,
            fuel_lb_per_gal=self.fuel_lb_per_gal,
            engines_running=self.engines_running,
            autopilot=self.autopilot,
        )


class SimConnectClient:
    def __init__(self) -> None:
        self.live = LiveData()
        self.lock = threading.Lock()
        self._stop = threading.Event()
        self._restoring = threading.Event()
        self._thread: threading.Thread | None = None
        self._dll = None
        self._handle = HANDLE()
        self._dispatch = DispatchProc(self._on_dispatch)
        self._connected_event = threading.Event()
        self._dll_path: Path | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="SimConnect", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._close()
        if self._thread:
            self._thread.join(timeout=2.0)

    def begin_restore(self) -> None:
        self._restoring.set()

    def end_restore(self) -> None:
        self._restoring.clear()

    def snapshot_if_ready(self) -> FlightSnapshot | None:
        with self.lock:
            if self._restoring.is_set() or not self.live.in_world:
                return None
            return self.live.to_snapshot()

    def restore(self, snapshot: FlightSnapshot) -> None:
        if not self._handle:
            raise RuntimeError("Not connected to the simulator.")
        self.begin_restore()
        try:
            self._pause(True)
            time.sleep(0.35)
            self._set_position(snapshot)
            self._set_fuel_gallons(snapshot.fuel_gal)
            time.sleep(0.45)
            self._pause(False)
        finally:
            # Keep ignoring inbound snapshots briefly so the warp does not overwrite
            # the saved resume point with a mid-teleport sample.
            time.sleep(1.0)
            self.end_restore()

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self._connect():
                time.sleep(2.0)
                continue
            while not self._stop.is_set() and self._handle:
                try:
                    self._dll.SimConnect_CallDispatch(self._handle, self._dispatch, None)
                except OSError:
                    self._mark_disconnected("Lost connection to the simulator")
                    break
                time.sleep(0.01)
            self._close()
            if not self._stop.is_set():
                time.sleep(1.5)

    def _connect(self) -> bool:
        dlls = find_simconnect_dlls()
        if not dlls:
            with self.lock:
                self.live.status = "SimConnect.dll not found"
            return False
        last_error = "Could not open SimConnect"
        for path in dlls:
            try:
                dll = ctypes.WinDLL(str(path))
                self._bind(dll)
            except OSError as exc:
                last_error = str(exc)
                continue
            for config_index in (0xFFFFFFFF, 0):
                handle = HANDLE()
                try:
                    hr = dll.SimConnect_Open(
                        byref(handle),
                        b"MSFS Resume",
                        HWND(0),
                        DWORD(0),
                        HANDLE(0),
                        DWORD(config_index),
                    )
                except OSError as exc:
                    last_error = str(exc)
                    continue
                if _ok(hr):
                    self._dll = dll
                    self._handle = handle
                    self._dll_path = path
                    self._setup()
                    with self.lock:
                        self.live.status = "Connected — waiting for a flight"
                        self.live.connected = True
                    return True
                last_error = f"SimConnect_Open failed (0x{hr & 0xFFFFFFFF:08X})"
        with self.lock:
            self.live.connected = False
            self.live.status = "Waiting for Microsoft Flight Simulator"
            self.live.exception = last_error
        return False

    def _bind(self, dll) -> None:
        dll.SimConnect_Open.restype = HRESULT
        dll.SimConnect_Open.argtypes = [POINTER(HANDLE), c_char_p, HWND, DWORD, HANDLE, DWORD]
        dll.SimConnect_Close.restype = HRESULT
        dll.SimConnect_Close.argtypes = [HANDLE]
        dll.SimConnect_CallDispatch.restype = HRESULT
        dll.SimConnect_CallDispatch.argtypes = [HANDLE, DispatchProc, c_void_p]
        dll.SimConnect_AddToDataDefinition.restype = HRESULT
        dll.SimConnect_AddToDataDefinition.argtypes = [
            HANDLE, DWORD, c_char_p, c_char_p, DWORD, c_float, DWORD
        ]
        dll.SimConnect_RequestDataOnSimObject.restype = HRESULT
        dll.SimConnect_RequestDataOnSimObject.argtypes = [
            HANDLE, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD, DWORD
        ]
        dll.SimConnect_SetDataOnSimObject.restype = HRESULT
        dll.SimConnect_SetDataOnSimObject.argtypes = [
            HANDLE, DWORD, DWORD, DWORD, DWORD, DWORD, c_void_p
        ]
        dll.SimConnect_MapClientEventToSimEvent.restype = HRESULT
        dll.SimConnect_MapClientEventToSimEvent.argtypes = [HANDLE, DWORD, c_char_p]
        dll.SimConnect_TransmitClientEvent.restype = HRESULT
        dll.SimConnect_TransmitClientEvent.argtypes = [HANDLE, DWORD, DWORD, DWORD, DWORD, DWORD]
        dll.SimConnect_SubscribeToSystemEvent.restype = HRESULT
        dll.SimConnect_SubscribeToSystemEvent.argtypes = [HANDLE, DWORD, c_char_p]

    def _setup(self) -> None:
        dll, handle = self._dll, self._handle
        for name, units in DOUBLE_FIELDS:
            dll.SimConnect_AddToDataDefinition(
                handle, DEF_SNAPSHOT, name.encode("ascii"), units,
                DATATYPE_FLOAT64, c_float(0), UNUSED,
            )
        dll.SimConnect_AddToDataDefinition(
            handle, DEF_SNAPSHOT, b"TITLE", None,
            DATATYPE_STRING256, c_float(0), UNUSED,
        )
        dll.SimConnect_RequestDataOnSimObject(
            handle, REQ_SNAPSHOT, DEF_SNAPSHOT, OBJECT_ID_USER,
            PERIOD_SECOND, 0, 0, 0, 0,
        )
        dll.SimConnect_AddToDataDefinition(
            handle, DEF_POSITION, b"Initial Position", None,
            DATATYPE_INITPOSITION, c_float(0), UNUSED,
        )
        dll.SimConnect_AddToDataDefinition(
            handle, DEF_FUEL, b"FUEL TOTAL QUANTITY", b"gallons",
            DATATYPE_FLOAT64, c_float(0), UNUSED,
        )
        dll.SimConnect_MapClientEventToSimEvent(handle, EVT_PAUSE_SET, b"PAUSE_SET")
        dll.SimConnect_SubscribeToSystemEvent(handle, EVT_SIM_START, b"SimStart")
        dll.SimConnect_SubscribeToSystemEvent(handle, EVT_SIM_STOP, b"SimStop")

    def _on_dispatch(self, p_data, cb_data, _context) -> None:
        recv = p_data.contents
        if recv.dwID == RECV_OPEN:
            open_msg = ctypes.cast(p_data, POINTER(RecvOpen)).contents
            name = _decode_title(bytes(open_msg.szApplicationName))
            with self.lock:
                self.live.sim_name = name or "Microsoft Flight Simulator"
                self.live.connected = True
                self.live.status = f"Connected to {self.live.sim_name}"
            self._connected_event.set()
        elif recv.dwID == RECV_QUIT:
            self._mark_disconnected("Simulator closed")
        elif recv.dwID == RECV_EXCEPTION:
            exc = ctypes.cast(p_data, POINTER(RecvException)).contents
            with self.lock:
                self.live.exception = f"SimConnect exception {exc.dwException} (index {exc.dwIndex})"
        elif recv.dwID == RECV_EVENT:
            event = ctypes.cast(p_data, POINTER(RecvEvent)).contents
            with self.lock:
                if event.uEventID == EVT_SIM_START:
                    self.live.sim_running = True
                elif event.uEventID == EVT_SIM_STOP:
                    self.live.sim_running = False
        elif recv.dwID == RECV_SIMOBJECT_DATA:
            msg = ctypes.cast(p_data, POINTER(RecvSimObjectData)).contents
            if msg.dwRequestID != REQ_SNAPSHOT:
                return
            self._apply_payload(msg.data)

    def _apply_payload(self, data: SnapshotPayload) -> None:
        values = [getattr(data, f"d{i}") for i in range(len(DOUBLE_FIELDS))]
        engines = any(v > 0.5 for v in values[15:19])
        title = _decode_title(bytes(data.title))
        with self.lock:
            live = self.live
            live.latitude = values[0]
            live.longitude = values[1]
            live.altitude_ft = values[2]
            live.heading_mag = values[3] % 360
            live.heading_true = values[4] % 360
            live.ias_kt = values[5]
            live.tas_kt = values[6]
            live.vertical_speed_fpm = values[7]
            live.pitch_deg = values[8]
            live.bank_deg = values[9]
            live.on_ground = values[10] > 0.5
            live.fuel_lb = max(0.0, values[11])
            live.fuel_gal = max(0.0, values[12])
            live.fuel_capacity_gal = max(0.0, values[13])
            live.fuel_lb_per_gal = values[14] if values[14] > 0 else 6.7
            live.engines_running = engines
            live.autopilot = values[19] > 0.5
            live.camera_state = int(values[20])
            live.slew = values[21] > 0.5
            live.aircraft = title
            live.updated_at = time.time()
            if live.in_world:
                live.status = "Recording flight"
            elif live.connected:
                live.status = "Connected — load an aircraft to record"

    def _pause(self, paused: bool) -> None:
        self._dll.SimConnect_TransmitClientEvent(
            self._handle,
            OBJECT_ID_USER,
            EVT_PAUSE_SET,
            DWORD(1 if paused else 0),
            GROUP_PRIORITY_HIGHEST,
            EVENT_FLAG_GROUPID_IS_PRIORITY,
        )

    def _set_position(self, snapshot: FlightSnapshot) -> None:
        pos = InitPosition()
        pos.Latitude = snapshot.latitude
        pos.Longitude = snapshot.longitude
        pos.Altitude = snapshot.altitude_ft
        pos.Pitch = snapshot.pitch_deg
        pos.Bank = snapshot.bank_deg
        pos.Heading = snapshot.heading_true
        pos.OnGround = 1 if snapshot.on_ground else 0
        pos.Airspeed = 0 if snapshot.on_ground else max(0, int(round(snapshot.ias_kt)))
        hr = self._dll.SimConnect_SetDataOnSimObject(
            self._handle,
            DEF_POSITION,
            OBJECT_ID_USER,
            0,
            0,
            sizeof(pos),
            ctypes.byref(pos),
        )
        if not _ok(hr):
            raise RuntimeError(f"Warp failed (0x{hr & 0xFFFFFFFF:08X})")

    def _set_fuel_gallons(self, gallons: float) -> None:
        value = c_double(max(0.0, gallons))
        self._dll.SimConnect_SetDataOnSimObject(
            self._handle,
            DEF_FUEL,
            OBJECT_ID_USER,
            0,
            0,
            sizeof(value),
            ctypes.byref(value),
        )

    def _mark_disconnected(self, reason: str) -> None:
        with self.lock:
            self.live.connected = False
            self.live.sim_running = False
            self.live.status = reason
        self._handle = HANDLE()

    def _close(self) -> None:
        handle, dll = self._handle, self._dll
        self._handle = HANDLE()
        if dll and handle:
            try:
                dll.SimConnect_Close(handle)
            except OSError:
                pass
        with self.lock:
            self.live.connected = False
