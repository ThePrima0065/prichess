# server.py
import asyncio
import websockets
import json
import os
import uuid

# Store active games: game_id -> { 'players': [ws1, ws2], 'moves': [...] }
games = {}

async def handler(websocket):
    try:
        # Receive initial message: create or join
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
            # Notify both players that the game starts
            for player in games[game_id]["players"]:
                await player.send(json.dumps({"action": "start"}))

        # Relay moves between players
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "move":
                game_id = data.get("game_id")
                if game_id in games:
                    for player in games[game_id]["players"]:
                        if player != websocket:
                            await player.send(json.dumps({"action": "move", "move": data["move"]}))

    except Exception as e:
        pass
    finally:
        # Clean up disconnected player
        for gid in list(games.keys()):
            if websocket in games[gid]["players"]:
                games[gid]["players"].remove(websocket)
                if len(games[gid]["players"]) == 0:
                    del games[gid]

# Use PORT from environment (Render sets this)
port = int(os.environ.get("PORT", 8765))
start_server = websockets.serve(handler, "0.0.0.0", port)

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()