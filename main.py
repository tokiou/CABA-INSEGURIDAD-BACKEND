from fastapi import FastAPI, WebSocket, HTTPException
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from typing import List
import json
import os
import folium
from routes import distance
from dotenv import load_dotenv

load_dotenv('.env')

app = FastAPI()
MAP_FILE_PATH = os.environ.get("MAP_FILE_PATH")
MAP_INICIAL_FILE_PATH = os.environ.get("MAP_INICIAL_FILE_PATH")
ALLOW_ORIGINS = os.environ.get("ALLOW_ORIGINS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOW_ORIGINS],
    allow_credentials=True,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["*"],
)


async def get_map_html_content(session_id):
    try:
        with open(MAP_FILE_PATH + session_id + '.html', 'r', encoding='utf-8') as file:
            html_content = file.read()
        return html_content
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"HTML file '{MAP_FILE_PATH}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class WebSocketManager:
    def __init__(self):
        self.connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def send_update(self, websocket: WebSocket, response_data: str):
        try:
            await websocket.send_text(response_data)
        except Exception as e:
            print(f"Error sending update to websocket: {e}")

    async def broadcast_update(self, response_data: str):
        for connection in self.connections:
            await self.send_update(connection, response_data)


websocket_manager = WebSocketManager()


async def get_map(session_id):
    try:
        m = folium.Map(location=[-34.6064346, -58.4386913], tiles='cartodbpositron', zoom_start=13)
        mapa_html = MAP_INICIAL_FILE_PATH + session_id + '.html'
        m.save(mapa_html)
        # Leer el HTML generado y devolverlo como respuesta
        with open(mapa_html, 'r', encoding='utf-8') as file:
            html_content = file.read()
        return html_content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            form_data = json.loads(data)
            session_id = form_data.get("session_id")
            print(session_id)
            if form_data.get('estado'):
                estado = form_data.get('estado')
                inicio = form_data.get('inicio')
                fin = form_data.get('fin')
                # Procesar los datos y generar el nuevo contenido del mapa
                route = await distance(inicio, fin, estado, session_id)
                if isinstance(route, dict):
                    response_data = await get_map(session_id)
                    await websocket_manager.send_update(websocket, response_data)
                    await websocket_manager.send_update(websocket, route.get('error'))
                else:
                    response_data = await get_map_html_content(session_id)
                    await websocket_manager.send_update(websocket, response_data)
            else:
                response_data = await get_map(session_id)
                await websocket_manager.send_update(websocket, response_data)
    except Exception as e:
        print(f"WebSocket connection error: {e}")
        if os.path.exists(MAP_INICIAL_FILE_PATH + session_id + '.html'):
            os.remove(MAP_INICIAL_FILE_PATH + session_id + '.html')
            os.remove(MAP_FILE_PATH + session_id + '.html')
        await websocket.send_text(f"Error en el servidor: {str(e)}")
    finally:
        websocket_manager.disconnect(websocket)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
