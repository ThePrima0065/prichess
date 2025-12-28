# server.py
import asyncio
import websockets
import json
import os
import uuid

games = {}

async def handler(websocket):
    try:
        message = await websocket.recv()
        data = json.loads(message)

        if data["type"] == "create":
            game_id = str(uuid.uuid4())[:8]
            games[game_id] = {"players": [websocket], "moves": []}
            await websocket.send(json.dumps({"action": "created", "game_id": game_id}))

        elif data["type"] == "join":
            game_id = data["game_id"]
            if game_id not in games or len(games[game_id]["players"]) >= 2:
                await websocket.send(json.dumps({"action": "error", "msg": "Game full or not found"}))
                return
            games[game_id]["players"].append(websocket)
            for player in games[game_id]["players"]:
                await player.send(json.dumps({"action": "start"}))

        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "move":
                game_id = data.get("game_id")
                if game_id in games:
                    for player in games[game_id]["players"]:
                        if player != websocket:
                            await player.send(json.dumps({"action": "move", "move": data["move"]}))

    except Exception:
        pass
    finally:
        for gid in list(games.keys()):
            if websocket in games[gid]["players"]:
                games[gid]["players"].remove(websocket)
                if not games[gid]["players"]:
                    del games[gid]

async def main():
    port = int(os.environ.get("PORT", 8765))
    print(f"Starting WebSocket server on port {port}...")
    server = await websockets.serve(handler, "0.0.0.0", port)
    await server.wait_closed()

if __name__ == "__main__":
    asyncio.run(main())