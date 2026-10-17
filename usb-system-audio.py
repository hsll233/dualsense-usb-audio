"""Windows USB fallback: loop back PC sound directly to DualSense rear channels."""
from __future__ import annotations

import argparse
import ctypes
import math
import msvcrt
import queue
import sys
import time
from contextlib import contextmanager

import hid
import numpy as np
import pyaudiowpatch as pa
import sounddevice as sd
from usb_motor_protection import MotorProtection


@contextmanager
def exclusive_run():
    """Avoid two copies feeding the same motors at once."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    handle = kernel.CreateMutexW(None, False, "Local\\DualSenseNativeAudioHelper")
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    try:
        if error == 183:
            raise RuntimeError("USB 助手已经在运行，请先关闭另一个窗口。")
        yield
    finally:
        kernel.CloseHandle(handle)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version="DualSense USB Audio 1.0.1")
    parser.add_argument("--seconds", type=float, default=0, help="0 means run until Ctrl+C")
    parser.add_argument("--gain", type=float, default=100, help="motor strength/volume, 0-200 percent (default: 100)")
    args = parser.parse_args()
    if not math.isfinite(args.gain) or not 0 <= args.gain <= 200:
        parser.error("gain must be between 0 and 200")
    if not math.isfinite(args.seconds) or args.seconds < 0:
        parser.error("seconds must be a finite nonnegative number")
    return args


def main(args) -> None:
    strength = args.gain
    muted = False

    controllers = [d for d in hid.enumerate(0x054C, 0)
                   if d.get("product_id") in (0x0CE6, 0x0DF2)
                   and d.get("usage_page") == 1 and d.get("usage") == 5
                   and d.get("interface_number", -1) >= 0]
    if len(controllers) != 1:
        raise RuntimeError("Please connect exactly one DualSense / Edge over USB.")
    targets = [(i, d) for i, d in enumerate(sd.query_devices())
               if d["max_output_channels"] >= 4
               and any(name in d["name"].lower() for name in ("dualsense", "wireless controller"))
               and sd.query_hostapis(d["hostapi"])["name"] == "Windows WASAPI"]
    if len(targets) != 1:
        raise RuntimeError("A unique four-channel DualSense output was not found.")

    device = hid.device()
    device.open_path(controllers[0]["path"])

    def volume(enabled: bool) -> None:
        report = bytearray(48)
        report[0] = 0x02
        report[1] = 0xB0  # Headphone/speaker volumes and audio routing only.
        report[5] = 127 if enabled else 0
        report[6] = 100 if enabled else 0
        if device.write(report) < 0:
            raise RuntimeError("Could not enable the controller audio output.")

    capture = None
    try:
        with pa.PyAudio() as manager:
            source = manager.get_default_wasapi_loopback()
            if any(name in source["name"].lower() for name in ("dualsense", "wireless controller")):
                raise RuntimeError("Keep PC speakers/headphones as the Windows default output.")
            rate = int(source["defaultSampleRate"])
            channels = int(source["maxInputChannels"])
            chunk = max(128, rate // 100)
            protection = MotorProtection(rate)
            packets: queue.Queue[tuple[float, bytes]] = queue.Queue(maxsize=4)

            def on_audio(data, _frames, _timing, _status):
                if packets.full():
                    try:
                        packets.get_nowait()
                    except queue.Empty:
                        pass
                try:
                    packets.put_nowait((time.monotonic(), data))
                except queue.Full:
                    pass
                return None, pa.paContinue

            capture = manager.open(format=pa.paFloat32, channels=channels, rate=rate,
                                   input=True, input_device_index=source["index"],
                                   frames_per_buffer=chunk, stream_callback=on_audio, start=False)
            # Keep the original input sample rate. Only the motor feed is processed.
            # WASAPI shared mode performs device-format conversion.
            with sd.RawOutputStream(device=targets[0][0], samplerate=rate, channels=4,
                                    dtype="float32", blocksize=chunk, latency="low",
                                    extra_settings=sd.WasapiSettings(auto_convert=True)) as output:
                volume(True)
                capture.start_stream()
                print("USB system audio following started. Ctrl+C stops it.", flush=True)
                print("按 + / - 调整振动强度（马达音量）；空格静音/恢复；Q 停止。", flush=True)
                print(f"强度 {strength:.0f}% | 原版增益范围；瞬时满幅，持续能量保护；20 分钟后休息 30 秒。", flush=True)
                print(f"Input: {source['name']} | {rate} Hz / {channels} ch", flush=True)
                print(f"Output: {targets[0][1]['name']} | rear channels only", flush=True)
                started = last_status = time.monotonic()
                peak = 0.0
                last_packet = started
                stopping = False
                while not args.seconds or time.monotonic() - started < args.seconds:
                    while msvcrt.kbhit():
                        key = msvcrt.getwch()
                        if key in ("\x00", "\xe0"):
                            msvcrt.getwch()
                            continue
                        if key.lower() == "q":
                            stopping = True
                            break
                        if key in ("+", "="):
                            strength = min(200, strength + 5)
                        elif key in ("-", "_"):
                            strength = max(0, strength - 5)
                        elif key == " ":
                            muted = not muted
                        else:
                            continue
                        print(f"振动强度 {strength:.0f}%" + ("（已静音）" if muted else ""), flush=True)
                    if stopping:
                        break
                    try:
                        timestamp, data = packets.get(timeout=0.05)
                    except queue.Empty:
                        output.write(bytes(chunk * 4 * 4))
                        protection.previous_input.fill(0)
                        protection.previous_dc.fill(0)
                        protection.gain = 0
                        if time.monotonic() - last_packet > 3:
                            raise RuntimeError("音频输入中断，已停止。请检查设备后重新启动。")
                        continue
                    if time.monotonic() - timestamp > 0.1:
                        continue
                    samples = np.frombuffer(data, dtype=np.float32).reshape(-1, channels)
                    motor = samples[:, :2] if channels >= 2 else np.repeat(samples, 2, axis=1)
                    last_packet = time.monotonic()
                    packed = np.zeros((len(samples), 4), dtype=np.float32)
                    packed[:, 2:4] = protection.process(motor, 0 if muted else strength)
                    if muted:
                        packed.fill(0)
                    peak = max(peak, float(np.max(np.abs(motor))))
                    output.write(packed.tobytes())
                    if time.monotonic() - last_status >= 1:
                        status = "定时休息中" if protection.resting else ("限幅保护中" if protection.limited else "正常跟随")
                        print(f"{status} | 强度 {strength:.0f}% | 输入峰值 {peak:.4f}" + (" | 已静音" if muted else ""), flush=True)
                        peak = 0.0
                        last_status = time.monotonic()
            capture.stop_stream()
            capture.close()
            capture = None
    finally:
        if capture is not None:
            try:
                capture.stop_stream()
                capture.close()
            except Exception:
                pass
        try:
            volume(False)
        finally:
            device.close()
        print("Stopped; controller audio muted.", flush=True)


if __name__ == "__main__":
    try:
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        options = parse_args()
        with exclusive_run():
            main(options)
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
