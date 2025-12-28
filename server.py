# server.py
import asyncio
import websockets
import json
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
            if game_id not in games:
                await websocket.send(json.dumps({"action": "error", "msg": "Game not found"}))
                return
            if len(games[game_id]["players"]) >= 2:
                await websocket.send(json.dumps({"action": "error", "msg": "Game full"}))
                return
            games[game_id]["players"].append(websocket)
            for player in games[game_id]["players"]:
                await player.send(json.dumps({"action": "start"}))

        # Relay moves
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "move" and "game_id" in data:
                game_id = data["game_id"]
                if game_id in games:
                    for player in games[game_id]["players"]:
                        if player != websocket:
                            await player.send(json.dumps({"action": "move", "move": data["move"]}))

    except Exception as e:
        pass
    finally:
        # Clean up
        for gid in list(games.keys()):
            if websocket in games[gid]["players"]:
                games[gid]["players"].remove(websocket)
                if len(games[gid]["players"]) == 0:
                    del games[gid]

start_server = websockets.serve(handler, "0.0.0.0", 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()