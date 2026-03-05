from pathlib import Path

from util import ida_connect, ida_disconnect, ida_exit_session, ida_open, ida_save, ida_stop_process


def connect_to_ida(port: bytes = b"5945") -> None:
    if not ida_connect(port):
        raise RuntimeError("Could not connect to IDA ICE API.")
    print("Connected to IDA ICE API.")


def open_model(file_path: str | Path):
    building = ida_open(str(file_path))
    if not building:
        raise RuntimeError(f"Could not open model: {file_path}")
    print(f"Model opened: {file_path}")
    return building


def save_model(building, file_path: str | Path, mode: int = 1) -> None:
    ida_save(building, result_path=str(file_path), mode=mode)


def disconnect_from_ida() -> None:
    try:
        ida_disconnect()
        print("Disconnected from IDA ICE API.")
    except Exception as exc:
        print(f"Disconnect warning: {exc}")


def exit_ida() -> None:
    try:
        ida_exit_session()
        print("Closed IDA ICE session.")
    except Exception as exc:
        print(f"IDA shutdown warning: {exc}")
    try:
        ida_stop_process()
        print("Stopped IDA ICE process.")
    except Exception as exc:
        print(f"IDA process stop warning: {exc}")
