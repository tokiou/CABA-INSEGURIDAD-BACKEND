from itertools import cycle
import folium
import asyncio

colors = ['red', 'blue', 'green', 'purple', 'orange', 'darkred',
          'lightred', 'beige', 'darkblue', 'darkgreen', 'cadetblue',
          'darkpurple', 'white', 'pink', 'lightblue', 'lightgreen',
          'gray', 'black', 'lightgray']


color_cycle = cycle(colors)


async def insecure(longitud, latitud, collection):
    point_list = []
    cursor = collection.find({"location": {
        "$nearSphere": {
            "$geometry": {
                "type": "Point",
                "coordinates": [longitud, latitud]
            },
            "$maxDistance": 1
        }
    }})
    async for doc in cursor:
        point_list.append(doc['location']['coordinates'])
    return len(point_list), point_list


async def create_route(coordinates, estado, avoid_coordinates, client_ors):
    route = await asyncio.to_thread(
        client_ors.directions,
        coordinates=coordinates,
        profile=estado,
        format='geojson',
        options={"avoid_polygons": avoid_coordinates},
        validate=False,
    )
    return route


async def route_points(route):
    x_list = []
    y_list = []
    for coordinate in route['features'][0]['geometry']['coordinates']:
        x_list.append(coordinate[0])
        y_list.append(coordinate[1])
    return x_list, y_list


async def add_route_to_map(m, routes_and_robos, lista_ordenada):
    # Obtener los límites de robos mínimo y máximo
    min_robos = lista_ordenada[0]
    max_robos = lista_ordenada[-1]

    for i, route in enumerate(routes_and_robos[0]["routes"]):
        robos = routes_and_robos[0]["robos"][i]
        if robos == min_robos:
            color = 'green'
            marker_text = f"Ruta {i+1}: Robos {robos} (Menos robos)"
        elif robos == max_robos:
            color = 'red'
            marker_text = f"Ruta {i+1}: Robos {robos} (Más robos)"
        else:
            color = 'orange'
            marker_text = f"Ruta {i+1}: Robos {robos}"
        folium.PolyLine(
            locations=[list(reversed(coord)) for coord in route['features'][0]['geometry']['coordinates']],
            color=color,
            popup=marker_text,  # Asignar el Popup
            icon=folium.Icon(color=color)
        ).add_to(m)
    return m
