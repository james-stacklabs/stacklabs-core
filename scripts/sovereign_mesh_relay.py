import asyncio
import json
import websockets
from datetime import datetime

# ─── State ────────────────────────────────────────────────────────────────────
# {user_name: {ws, display_name, role, connected_at, queues: []}}
connected_users: dict = {}
# {queue_name: {user_name: ws}}  — AetherVet / waiting-room model
queues: dict = {}
# {room_id: {peer_id: {ws, display_name, role, joined_at}}} — Multi-Party HoloLink Room Mesh
rooms: dict = {}
# All sockets (registered + anonymous) for legacy broadcast fallback
all_clients: set = set()


# ─── Presence & Room Broadcasts ───────────────────────────────────────────────
async def broadcast_presence():
    """Push the current online roster to every registered client."""
    presence = [
        {
            "user_name": u,
            "display_name": m.get("display_name", u),
            "role": m.get("role", "user"),
            "queues": m.get("queues", []),
            "status": "online",
        }
        for u, m in connected_users.items()
    ]
    msg = json.dumps({
        "type": "PRESENCE_UPDATE",
        "users": presence,
        "queues": list(queues.keys()),
    })
    for meta in list(connected_users.values()):
        try:
            await meta["ws"].send(msg)
        except Exception:
            pass


async def broadcast_room_peers(room_id: str):
    """Notify all participants in a room of current peers."""
    room_members = rooms.get(room_id, {})
    peers = [
        {
            "peerId": pid,
            "displayName": info.get("display_name", pid),
            "role": info.get("role", "guest"),
            "joinedAt": info.get("joined_at"),
        }
        for pid, info in room_members.items()
    ]
    msg = json.dumps({
        "type": "ROOM_PEERS",
        "room": room_id,
        "peers": peers,
    })
    for pid, info in list(room_members.items()):
        try:
            await info["ws"].send(msg)
        except Exception:
            pass


# ─── Routing helpers ──────────────────────────────────────────────────────────
async def route_to_user(to_user: str, raw: str, sender_ws) -> bool:
    if to_user:
        to_user = to_user.lower().strip()
    meta = connected_users.get(to_user)
    if meta and meta["ws"] != sender_ws:
        try:
            await meta["ws"].send(raw)
            return True
        except Exception:
            pass
    return False


async def route_to_queue(queue_name: str, raw: str, sender_ws):
    """Deliver to the first available receiver in the queue."""
    members = queues.get(queue_name, {})
    for uid, qws in list(members.items()):
        if qws != sender_ws:
            try:
                await qws.send(raw)
                return
            except Exception:
                pass


async def route_to_room_peer(room_id: str, target_peer_id: str, raw: str, sender_ws):
    """Deliver message to a specific peer in a room."""
    room_members = rooms.get(room_id, {})
    target = room_members.get(target_peer_id)
    if target and target["ws"] != sender_ws:
        try:
            await target["ws"].send(raw)
            return True
        except Exception:
            pass
    return False


async def broadcast_to_room(room_id: str, raw: str, sender_ws):
    """Deliver message to all other peers in a room."""
    room_members = rooms.get(room_id, {})
    for pid, info in list(room_members.items()):
        if info["ws"] != sender_ws:
            try:
                await info["ws"].send(raw)
            except Exception:
                pass


async def legacy_broadcast(raw: str, sender_ws):
    """Backward-compat: send to every connected socket except the sender."""
    for meta in list(connected_users.values()):
        if meta["ws"] != sender_ws:
            try:
                await meta["ws"].send(raw)
            except Exception:
                pass
    for c in list(all_clients):
        if c != sender_ws and c not in [m["ws"] for m in connected_users.values()]:
            try:
                await c.send(raw)
            except Exception:
                pass


# ─── Client handler ───────────────────────────────────────────────────────────
async def handle_client(ws):
    user_name = None
    joined_rooms = set()
    all_clients.add(ws)
    print(f"⚡ Client connected ({ws.remote_address})")

    try:
        async for raw in ws:
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = data.get("type", "")

            # ── Heartbeat ────────────────────────────────────────────────────
            if msg_type == "PING":
                await ws.send(json.dumps({"type": "PONG", "timestamp": datetime.utcnow().isoformat()}))

            # ── HoloLink Multi-Party Rooms ───────────────────────────────────
            elif msg_type == "JOIN_ROOM":
                room_id = data.get("room", "default")
                peer_id = data.get("peerId") or data.get("userId") or f"guest_{id(ws)}"
                display_name = data.get("displayName", peer_id)
                role = data.get("role", "guest")

                rooms.setdefault(room_id, {})[peer_id] = {
                    "ws": ws,
                    "display_name": display_name,
                    "role": role,
                    "joined_at": datetime.utcnow().isoformat(),
                }
                joined_rooms.add((room_id, peer_id))
                print(f"🚪 JOIN_ROOM: {peer_id} ('{display_name}') joined room [{room_id}]")
                await broadcast_room_peers(room_id)

            elif msg_type == "LEAVE_ROOM":
                room_id = data.get("room")
                peer_id = data.get("peerId") or data.get("userId")
                if room_id and peer_id:
                    rooms.get(room_id, {}).pop(peer_id, None)
                    if not rooms.get(room_id):
                        rooms.pop(room_id, None)
                    joined_rooms.discard((room_id, peer_id))
                    print(f"🚪 LEAVE_ROOM: {peer_id} left room [{room_id}]")
                    await broadcast_room_peers(room_id)

            elif msg_type in ["ROOM_OFFER", "ROOM_ANSWER", "ROOM_ICE_CANDIDATE", "ROOM_CHAT"]:
                room_id = data.get("room")
                target_peer = data.get("to") or data.get("targetPeerId")
                if room_id:
                    if target_peer:
                        await route_to_room_peer(room_id, target_peer, raw, ws)
                    else:
                        await broadcast_to_room(room_id, raw, ws)

            # ── Registration (Legacy / Portal) ───────────────────────────────
            elif msg_type == "REGISTER":
                u_raw = data.get("userId") or data.get("user_name")
                if u_raw:
                    user_name = u_raw.lower().strip()
                    connected_users[user_name] = {
                        "ws": ws,
                        "display_name": data.get("displayName", u_raw),
                        "role": data.get("role", "user"),
                        "connected_at": datetime.utcnow().isoformat(),
                        "queues": [],
                    }
                    print(f"✅ REGISTER  {user_name} ({data.get('role', 'user')})")
                    await ws.send(json.dumps({"type": "REGISTERED", "userId": user_name}))
                    await broadcast_presence()

            # ── Queue management (AetherVet / waiting-room model) ────────────
            elif msg_type == "JOIN_QUEUE":
                queue = data.get("queue")
                uid = data.get("userId") or user_name
                if queue and uid:
                    uid = uid.lower().strip()
                    queues.setdefault(queue, {})[uid] = ws
                    if uid in connected_users:
                        connected_users[uid].setdefault("queues", [])
                        if queue not in connected_users[uid]["queues"]:
                            connected_users[uid]["queues"].append(queue)
                    print(f"📋 JOIN_QUEUE  {uid} → {queue}")
                    await broadcast_presence()

            elif msg_type == "LEAVE_QUEUE":
                queue = data.get("queue")
                uid = data.get("userId") or user_name
                if queue and uid:
                    uid = uid.lower().strip()
                    queues.get(queue, {}).pop(uid, None)
                    if not queues.get(queue):
                        queues.pop(queue, None)
                    if uid in connected_users:
                        connected_users[uid]["queues"] = [
                            q for q in connected_users[uid].get("queues", []) if q != queue
                        ]
                    await broadcast_presence()

            # ── Presence request ─────────────────────────────────────────────
            elif msg_type == "GET_PRESENCE":
                presence = [
                    {
                        "user_name": u,
                        "display_name": m.get("display_name", u),
                        "role": m.get("role", "user"),
                        "queues": m.get("queues", []),
                        "status": "online",
                    }
                    for u, m in connected_users.items()
                ]
                await ws.send(json.dumps({
                    "type": "PRESENCE_UPDATE",
                    "users": presence,
                    "queues": list(queues.keys()),
                }))

            # ── WebRTC signaling + HoloLink events (Legacy 1-on-1) ───────────
            elif msg_type in [
                "WEBRTC_OFFER", "WEBRTC_ANSWER", "WEBRTC_ICE_CANDIDATE",
                "HOLOLINK_END", "HOLOLINK_REQUEST",
            ]:
                to_user  = data.get("to")
                to_queue = data.get("toQueue")

                if to_user:
                    to_user = to_user.lower().strip()
                    await route_to_user(to_user, raw, ws)
                elif to_queue:
                    await route_to_queue(to_queue, raw, ws)
                else:
                    await legacy_broadcast(raw, ws)

            # ── Call decline / busy ──────────────────────────────────────────
            elif msg_type in ["CALL_DECLINED", "CALL_BUSY"]:
                to_user = data.get("to")
                if to_user:
                    to_user = to_user.lower().strip()
                    await route_to_user(to_user, raw, ws)

    except Exception as e:
        print(f"⚠️  Client error: {e}")
    finally:
        all_clients.discard(ws)
        # Clean up room memberships
        for room_id, peer_id in joined_rooms:
            rooms.get(room_id, {}).pop(peer_id, None)
            if not rooms.get(room_id):
                rooms.pop(room_id, None)
            print(f"🚪 CLEANUP: {peer_id} removed from [{room_id}]")
            await broadcast_room_peers(room_id)

        if user_name:
            user_name = user_name.lower().strip()
            if user_name in connected_users:
                for q_name in list(queues.keys()):
                    queues[q_name].pop(user_name, None)
                    if not queues[q_name]:
                        queues.pop(q_name, None)
                del connected_users[user_name]
                print(f"❌ DISCONNECT  {user_name}")
                await broadcast_presence()
        else:
            print(f"❌ Anonymous client disconnected")


# ─── Entry point ──────────────────────────────────────────────────────────────
async def main():
    print("🛰  Sovereign Mesh Relay v3.0 — Port 8012")
    print("   Modes: multi-peer room mesh | user-addressed | queue | legacy broadcast")
    async with websockets.serve(handle_client, "0.0.0.0", 8012):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
