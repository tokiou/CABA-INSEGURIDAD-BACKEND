import openrouteservice as ors
import folium
from pymongo import GEOSPHERE
from utils import create_route, route_points, add_route_to_map, insecure
import asyncio
import os
from dotenv import load_dotenv
import motor.motor_asyncio


load_dotenv('.env')
ORS_KEY = os.environ.get("ORS_KEY")
MAP_FILE_PATH = os.environ.get("MAP_FILE_PATH")
client_ors = ors.Client(ORS_KEY)

uri = os.environ.get("URI")
client = motor.motor_asyncio.AsyncIOMotorClient(uri)
# client = MongoClient(uri)
db = client['geocordenadas']
collection = db['places']


async def create_index():
    await collection.create_index([("location", GEOSPHERE)])


async def coordenadas_robos(route, multi_poligono_geojson):
    x_list, y_list = await route_points(route)
    lon_point_list = []
    lat_point_list = []
    for i in range(len(x_list)):
        cant, coordinates_lat_lon = await insecure(x_list[i], y_list[i], collection)
        if cant >= 3:
            for coord in coordinates_lat_lon:
                longitud, latitud = coord[0], coord[1]
                if (longitud, latitud) not in zip(lon_point_list, lat_point_list):
                    lon_point_list.append(longitud)
                    lat_point_list.append(latitud)
                    break
    if len(lon_point_list) < 3:
        return False, False
    coordenadas = list(zip(lon_point_list, lat_point_list))
    coordenadas.append(coordenadas[0])
    multi_poligono_geojson["coordinates"].append([coordenadas])
    return multi_poligono_geojson, len(coordenadas)


async def distance(inicio, fin, estado, session_id):
    multi_poligono_geojson = {
        "type": "MultiPolygon",
        "coordinates": []
    }
    m = folium.Map(location=[-34.6064346, -58.4386913], tiles='cartodbpositron', zoom_start=13)

    # Usamos asyncio.to_thread para las operaciones bloqueantes
    inicio = await asyncio.to_thread(client_ors.pelias_search, text=inicio)
    fin = await asyncio.to_thread(client_ors.pelias_search, text=fin)
    coordinates = [inicio['features'][0]['geometry']['coordinates'], fin['features'][0]['geometry']['coordinates']]
    pais_inicio = inicio.get('features')[0].get('properties').get('country_a')
    pais_final = fin.get('features')[0].get('properties').get('country_a')
    if pais_inicio != "ARG" or pais_final != "ARG":
        return {"error": "Error, solo se pueden realizar en Ciudad Autónoma de Buenos Aires Argentina. Intente siendo más especifico"}

    prov_inicio = inicio.get('features')[0].get('properties').get('region')
    prov_final = fin.get('features')[0].get('properties').get('region')
    if prov_inicio not in ["Autonomous City of Buenos Aires"] or prov_final not in ["Autonomous City of Buenos Aires"]:
        return {"error": "Error, solo se pueden realizar rutas en Ciudad Autónoma de Buenos Aires Argentina. Intente siendo más especifico"}
    print('Creating first route')
    route = await asyncio.to_thread(
        client_ors.directions,
        coordinates=coordinates,
        profile=estado,
        format='geojson',
        validate=False,
    )

    routes_and_robos = []
    multi_poligono_geojson, cantidad_robos1 = await coordenadas_robos(route, multi_poligono_geojson)

    if multi_poligono_geojson:
        print('Creating second route')
        route2 = await create_route(coordinates, estado, multi_poligono_geojson, client_ors)
        multi_poligono_geojson, cantidad_robos2 = await coordenadas_robos(route2, multi_poligono_geojson)

        if not multi_poligono_geojson:
            await asyncio.to_thread(m.save, MAP_FILE_PATH + session_id + '.html')
            return MAP_FILE_PATH

        print('Creating third route')
        route3 = await create_route(coordinates, estado, multi_poligono_geojson, client_ors)
        multi_poligono_geojson, cantidad_robos3 = await coordenadas_robos(route3, multi_poligono_geojson)

        routes_and_robos.append({"routes": [route, route2, route3], "robos": [cantidad_robos1, cantidad_robos2, cantidad_robos3]})
        lista_ordenada = sorted(routes_and_robos[0]["robos"])
        m = await add_route_to_map(m, routes_and_robos, lista_ordenada)
        await asyncio.to_thread(m.save, MAP_FILE_PATH + session_id + '.html')
        print('Ruta creada')
        return 'Succesfull route'
    else:
        folium.PolyLine(
            locations=[list(reversed(coord)) for coord in route['features'][0]['geometry']['coordinates']],
            color='green',
        ).add_to(m)

    await asyncio.to_thread(m.save, MAP_FILE_PATH + session_id + '.html')
    return MAP_FILE_PATH
