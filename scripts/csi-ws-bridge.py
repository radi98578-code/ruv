#!/usr/bin/env python3
"""
CSI JSONL → WebSocket bridge for RuView dashboard.

Tails the latest .csi.jsonl recording and converts each CSI frame to the
60-byte nvsim MagFrame binary format the dashboard WsClient expects.

Maps CSI subcarrier amplitudes to b_pt[3] (X/Y/Z) by splitting subcarriers
into thirds, so the dashboard 3-axis view reflects spectral energy distribution.

Usage:
    python scripts/csi-ws-bridge.py
Then in dashboard: connect to http://localhost:7878
"""

import asyncio
import glob
import json
import os
import struct
import time
from aiohttp import web
from aiohttp.web_middlewares import middleware

HTTP_PORT = 7878
MAGIC_CSI = 0xC5110001
FRAME_BYTES = 60
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(os.path.dirname(SCRIPT_DIR), "data", "recordings")

ws_clients: set = set()


def jsonl_to_magframe(line: str) -> bytes | None:
    try:
        d = json.loads(line)
    except Exception:
        return None
    if d.get("type") != "raw_csi":
        return None

    node_id = int(d.get("node_id", 0)) & 0xFFFF
    rssi = float(d.get("rssi", 0))
    channel = float(d.get("channel", 0))
    amps = d.get("amplitudes", [])
    if not amps:
        return None

    n = len(amps)
    t3 = max(1, n // 3)
    bx = sum(amps[:t3]) / t3
    by = sum(amps[t3 : 2 * t3]) / max(1, len(amps[t3 : 2 * t3]))
    bz = sum(amps[2 * t3 :]) / max(1, len(amps[2 * t3 :]))
    mean = sum(amps) / n
    std = (sum((a - mean) ** 2 for a in amps) / n) ** 0.5

    t_us = int(time.time() * 1_000_000)

    # 60-byte MagFrame (little-endian):
    # magic(u32) version(u16) flags(u16) sensor_id(u16) reserved(u16)
    # t_us(u64) b_pt[3](f32) sigma_pt[3](f32) noise_floor(f32) temp_k(f32) pad(2xf32)
    return struct.pack(
        "<IHHHHQffffffffff",
        MAGIC_CSI, 1, 0, node_id, 0,
        t_us,
        bx, by, bz,
        std, abs(rssi), channel,
        abs(rssi), 300.0,
        0.0, 0.0,
    )


def latest_jsonl() -> str | None:
    files = glob.glob(os.path.join(RECORDINGS_DIR, "*.csi.jsonl"))
    return max(files, key=os.path.getmtime) if files else None


async def tail_and_broadcast():
    path = None
    f = None
    frames_sent = 0
    last_log = time.time()

    while True:
        new_path = latest_jsonl()
        if new_path != path:
            if f:
                f.close()
            path = new_path
            if path:
                f = open(path, "r", encoding="utf-8")
                f.seek(0, 2)  # jump to end — only stream new frames
                print(f"Tailing: {os.path.basename(path)}")

        if f:
            line = f.readline()
            if line.strip():
                frame = jsonl_to_magframe(line)
                if frame and ws_clients:
                    dead = set()
                    for ws in list(ws_clients):
                        try:
                            await ws.send_bytes(frame)
                            frames_sent += 1
                        except Exception:
                            dead.add(ws)
                    ws_clients.difference_update(dead)

                now = time.time()
                if now - last_log >= 5 and frames_sent:
                    print(f"  {frames_sent} frames sent to {len(ws_clients)} client(s)")
                    last_log = now
            else:
                await asyncio.sleep(0.02)
        else:
            await asyncio.sleep(0.5)


@middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,POST,PUT,OPTIONS",
            "Access-Control-Allow-Headers": "content-type",
        })
    resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    return resp


async def health(request):
    return web.json_response({
        "nvsim_version": "csi-bridge-1.0",
        "magic": MAGIC_CSI,
        "frame_bytes": FRAME_BYTES,
        "expected_witness_hex": "0" * 64,
    })


async def stub(request):
    return web.json_response({"ok": True})


async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    ws_clients.add(ws)
    print(f"Dashboard connected ({len(ws_clients)} client(s))")
    try:
        async for _ in ws:
            pass
    finally:
        ws_clients.discard(ws)
        print(f"Dashboard disconnected ({len(ws_clients)} client(s))")
    return ws


async def main():
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/api/health", health)
    app.router.add_get("/ws/stream", ws_handler)
    app.router.add_put("/api/scene", stub)
    app.router.add_put("/api/config", stub)
    app.router.add_put("/api/seed", stub)
    app.router.add_post("/api/reset", stub)
    app.router.add_post("/api/run", stub)
    app.router.add_post("/api/pause", stub)
    app.router.add_post("/api/step", stub)
    app.router.add_post("/api/witness/generate", stub)
    app.router.add_post("/api/witness/verify", stub)
    app.router.add_post("/api/export-proof", stub)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", HTTP_PORT)
    await site.start()

    print(f"CSI-WS bridge listening on http://localhost:{HTTP_PORT}")
    print(f"Dashboard: connect to http://localhost:{HTTP_PORT}")
    print(f"Recordings dir: {RECORDINGS_DIR}")

    asyncio.create_task(tail_and_broadcast())
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
