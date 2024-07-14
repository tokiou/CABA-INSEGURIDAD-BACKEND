import openrouteservice as ors
import folium
from pymongo import MongoClient, GEOSPHERE
from utils import create_route, route_points, add_route_to_map, insecure
import os
from dotenv import load_dotenv
from pymongo.server_api import ServerApi


load_dotenv('.env')
ORS_KEY = os.environ.get("ORS_KEY")
MAP_FILE_PATH = os.environ.get("MAP_FILE_PATH")
client_ors = ors.Client(ORS_KEY)

uri = os.environ.get("URI")
client = MongoClient('localhost', 27017)
db = client['geocordenadas']
collection = db['places']
collection.create_index([("location", GEOSPHERE)])


def coordenadas_robos(route, multi_poligono_geojson):
    x_list, y_list = route_points(route)
    lon_point_list = []
    lat_point_list = []
    for i in range(len(x_list)):
        cant, coordinates_lat_lon = insecure(x_list[i], y_list[i], collection)
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


async def distance(inicio, fin, estado):
    multi_poligono_geojson = {
         "type": "MultiPolygon",
         "coordinates": []
     }
    m = 0
    m = folium.Map(location=[-34.6064346, -58.4386913], tiles='cartodbpositron', zoom_start=13)
    inicio = client_ors.pelias_search(text=inicio)
    fin = client_ors.pelias_search(text=fin)
    coordinates = [inicio['features'][0]['geometry']['coordinates'],  fin['features'][0]['geometry']['coordinates']]
    print(coordinates)
    route = client_ors.directions(
        coordinates=coordinates,
        profile=estado,
        format='geojson',
        validate=False,
    )
    routes_and_robos = []
    multi_poligono_geojson, cantidad_robos1 = coordenadas_robos(route, multi_poligono_geojson)
    if multi_poligono_geojson:
        route2 = create_route(coordinates, estado, multi_poligono_geojson, client_ors)
        multi_poligono_geojson, cantidad_robos2 = coordenadas_robos(route2, multi_poligono_geojson)
        if not multi_poligono_geojson:
            m.save(MAP_FILE_PATH)
            return MAP_FILE_PATH
        route3 = create_route(coordinates, estado, multi_poligono_geojson, client_ors)
        multi_poligono_geojson, cantidad_robos3 = coordenadas_robos(route3, multi_poligono_geojson)
        routes_and_robos.append({"routes": [route, route2, route3], "robos": [cantidad_robos1, cantidad_robos2, cantidad_robos3]})
        lista_ordenada = sorted(routes_and_robos[0]["robos"])
        m = add_route_to_map(m, routes_and_robos, lista_ordenada)
        m.save(MAP_FILE_PATH)
        return MAP_FILE_PATH
    else:
        folium.PolyLine(
            locations=[list(reversed(coord)) for coord in route['features'][0]['geometry']['coordinates']],
            color='green',
        ).add_to(m)
        m.save(MAP_FILE_PATH)
        return MAP_FILE_PATH
