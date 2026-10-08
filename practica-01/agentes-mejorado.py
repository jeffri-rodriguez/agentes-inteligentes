# Agentes inteligentes: BFS y A* en un laberinto dinamico generado por algoritmo.
# Version mejorada

import random
import time
import heapq
from collections import deque

MOVIMIENTOS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
LIBRES = (".", "S", "G")


def vecinos(posicion):
    fila, columna = posicion
    return [(fila + df, columna + dc) for df, dc in MOVIMIENTOS]


def dentro(posicion, filas, columnas):
    f, c = posicion
    return 0 <= f < filas and 0 <= c < columnas


def generar_laberinto(filas, columnas, semilla):
    # DFS aleatorizado abre pasillos entre celdas separadas por un muro.
    # Generacion dinamica: cambia entre semillas, no durante el recorrido.
    if filas < 7 or columnas < 7 or filas % 2 == 0 or columnas % 2 == 0:
        raise ValueError("Las dimensiones deben ser impares y al menos 7.")
    azar = random.Random(semilla)
    mapa = [["#"] * columnas for _ in range(filas)]
    inicio = (filas - 2, 1)
    mapa[inicio[0]][inicio[1]] = "."
    pila = [inicio]

    while pila:
        f, c = pila[-1]
        opciones = []
        for df, dc in MOVIMIENTOS:
            nf, nc = f + 2 * df, c + 2 * dc
            if 0 < nf < filas - 1 and 0 < nc < columnas - 1:
                if mapa[nf][nc] == "#":
                    opciones.append((nf, nc))
        if opciones:
            nf, nc = azar.choice(opciones)
            mapa[(f + nf) // 2][(c + nc) // 2] = "."
            mapa[nf][nc] = "."
            pila.append((nf, nc))
        else:
            pila.pop()

    # Abrir algunos muros adicionales crea rutas alternativas y ciclos.
    for f in range(1, filas - 1):
        for c in range(1, columnas - 1):
            if mapa[f][c] != "#" or (f % 2 == c % 2):
                continue
            vertical = mapa[f - 1][c] == mapa[f + 1][c] == "."
            horizontal = mapa[f][c - 1] == mapa[f][c + 1] == "."
            if (vertical or horizontal) and azar.random() < 0.18:
                mapa[f][c] = "."

    # La meta tambien varia. Solo el generador conoce su ubicacion inicialmente.
    candidatos = [(f, c) for f in range(1, filas - 1, 2)
                  for c in range(1, columnas - 1, 2)
                  if abs(f - inicio[0]) + abs(c - inicio[1]) >= (filas + columnas) // 3]
    meta = azar.choice(candidatos)
    mapa[inicio[0]][inicio[1]] = "S"
    mapa[meta[0]][meta[1]] = "G"
    return ["".join(fila) for fila in mapa], inicio


def percibir(mapa, posicion):
    # Solo informa sobre la celda actual y las cuatro vecinas.
    return {p: mapa[p[0]][p[1]] for p in [posicion] + vecinos(posicion)
            if dentro(p, len(mapa), len(mapa[0]))}


def reconstruir(padres, actual):
    camino = []
    while actual is not None:
        camino.append(actual)
        actual = padres[actual]
    return camino[::-1]


def buscar_bfs(conocido, inicio, objetivos):
    cola = deque([inicio])
    padres = {inicio: None}
    expandidos = 0
    while cola:
        actual = cola.popleft()
        expandidos += 1
        if actual in objetivos:
            return reconstruir(padres, actual), expandidos
        for p in vecinos(actual):
            if conocido.get(p) in LIBRES and p not in padres:
                padres[p] = actual
                cola.append(p)
    return [], expandidos


def informacion_nueva(posicion, conocido, filas, columnas):
    # Cuantas celdas desconocidas se observarian al llegar a esta posicion.
    # No consulta el contenido oculto: esas celdas tambien podrian ser muros.
    return sum(1 for p in vecinos(posicion)
               if dentro(p, filas, columnas) and p not in conocido)


def distancias_desde_referencia(conocido, referencia):
    # Construye un punto de referencia usando UNICAMENTE pasillos descubiertos.
    # No calcula distancias a G. Su trabajo se contabiliza por separado.
    cola = deque([referencia])
    distancias = {referencia: 0}
    while cola:
        actual = cola.popleft()
        for p in vecinos(actual):
            if conocido.get(p) in LIBRES and p not in distancias:
                distancias[p] = distancias[actual] + 1
                cola.append(p)
    return distancias


def buscar_astar(conocido, inicio, objetivos, informacion, distancias):
    # A* usa f = g + h. g: pasos desde la posicion de planificacion.
    # h: cota inferior hacia una frontera de exploracion, NO hacia la G oculta.
    # d_R(n) = distancia desde una referencia R en el mapa conocido.
    # h(n) = min_t |d_R(n) - d_R(t)|, con t entre los objetivos locales.
    # Por desigualdad triangular, h no sobreestima ese costo local.
    def heuristica(p):
        if not distancias:
            return 0
        return min(abs(distancias[p] - distancias[t]) for t in objetivos)

    orden = 0
    abiertos = [(heuristica(inicio), -informacion[inicio], orden, 0, inicio)]
    costos = {inicio: 0}
    padres = {inicio: None}
    expandidos = 0
    while abiertos:
        _, _, _, costo, actual = heapq.heappop(abiertos)
        if costo != costos[actual]:
            continue  # Entrada vieja: ya se encontro un camino mejor.
        expandidos += 1
        if actual in objetivos:
            return reconstruir(padres, actual), expandidos
        for p in vecinos(actual):
            if conocido.get(p) not in LIBRES:
                continue
            nuevo_costo = costo + 1
            if nuevo_costo < costos.get(p, float("inf")):
                costos[p] = nuevo_costo
                padres[p] = actual
                orden += 1
                prioridad = nuevo_costo + heuristica(p)
                heapq.heappush(abiertos, (prioridad, -informacion[p], orden, nuevo_costo, p))
    return [], expandidos


def decidir(conocido, posicion, visitados, tipo, filas, columnas, referencia):
    # Esta funcion NO recibe el mapa real, su semilla ni la meta oculta.
    metas = {p for p, valor in conocido.items() if valor == "G"}
    pendientes = {p for p, valor in conocido.items()
                  if valor in LIBRES and p not in visitados}
    objetivos = metas if metas else pendientes
    if not objetivos:
        return [], 0, 0
    if tipo == "BFS":
        camino, expandidos = buscar_bfs(conocido, posicion, objetivos)
        return camino, expandidos, 0

    informacion = {p: informacion_nueva(p, conocido, filas, columnas)
                   for p, valor in conocido.items() if valor in LIBRES}
    if not metas:
        # Politica informada: preferir fronteras que revelen mas celdas.
        mejor = max(informacion[p] for p in objetivos)
        objetivos = {p for p in objetivos if informacion[p] == mejor}
        distancias = distancias_desde_referencia(conocido, referencia)
    else:
        # G ya fue vista por el sensor. Se navega hacia ella con h=0.
        # Nunca se entrega una distancia externa a la meta.
        distancias = {}
    camino, expandidos = buscar_astar(conocido, posicion, objetivos, informacion, distancias)
    return camino, expandidos, len(distancias)


def ejecutar_agente(mapa, inicio, tipo):
    if tipo not in ("BFS", "A*"):
        raise ValueError("El tipo debe ser BFS o A*.")
    filas, columnas = len(mapa), len(mapa[0])
    posicion = inicio
    conocido, visitados = {}, set()
    recorrido = [inicio]
    plan = deque()
    expandidos = preparacion = planes = 0
    limite = (filas * columnas) ** 2
    tiempo_inicio = time.perf_counter()

    while True:
        conocido.update(percibir(mapa, posicion))
        visitados.add(posicion)
        if conocido[posicion] == "G":
            estado = "Meta alcanzada"
            break

        # Conservar el plan hasta su destino evita oscilar entre fronteras.
        # Si se descubre G durante el trayecto, se cambia el objetivo.
        meta_visible = any(valor == "G" for valor in conocido.values())
        if not plan or meta_visible:
            camino, cantidad, auxiliar = decidir(
                conocido, posicion, visitados, tipo, filas, columnas, inicio)
            expandidos += cantidad
            preparacion += auxiliar
            planes += 1
            if len(camino) < 2:
                estado = "Sin ruta: se agoto la region accesible"
                break
            plan = deque(camino[1:])

        if len(recorrido) - 1 >= limite:
            estado = "Limite preventivo alcanzado"
            break
        siguiente = plan.popleft()
        # Validacion del simulador. No participa en la eleccion de caminos.
        if siguiente not in vecinos(posicion) or mapa[siguiente[0]][siguiente[1]] == "#":
            raise RuntimeError("Se intento un movimiento invalido.")
        posicion = siguiente
        recorrido.append(posicion)

    tiempo_ms = (time.perf_counter() - tiempo_inicio) * 1000
    metas = {p for p, valor in conocido.items() if valor == "G"}
    ruta, _ = buscar_bfs(conocido, inicio, metas)
    return {"estado": estado, "recorrido": recorrido, "visitados": visitados,
            "conocido": conocido, "ruta": ruta, "tiempo_ms": tiempo_ms,
            "expandidos": expandidos, "preparacion": preparacion, "planes": planes}


def mostrar_resultado(nombre, resultado, filas, columnas):
    print("\nAGENTE", nombre)
    print("Estado:", resultado["estado"])
    print("Movimientos:", len(resultado["recorrido"]) - 1)
    print("Celdas distintas visitadas:", len(resultado["visitados"]))
    print("Revisitas:", len(resultado["recorrido"]) - len(resultado["visitados"]))
    print("Planes calculados:", resultado["planes"])
    print("Nodos procesados por el buscador:", resultado["expandidos"])
    print("Nodos procesados para preparar la heuristica:", resultado["preparacion"])
    print(f"Tiempo del bucle, incluida preparacion: {resultado['tiempo_ms']:.4f} ms")
    print("Recorrido:", " -> ".join(str(p) for p in resultado["recorrido"]))
    if resultado["ruta"]:
        print("Ruta minima en el mapa descubierto:", len(resultado["ruta"]) - 1, "pasos")
    print("Mapa descubierto: ? = desconocido, * = visitado")
    for f in range(filas):
        linea = []
        for c in range(columnas):
            celda = resultado["conocido"].get((f, c), "?")
            if (f, c) in resultado["visitados"] and celda not in ("S", "G"):
                celda = "*"
            linea.append(celda)
        print(" ".join(linea))


def main():
    print("BFS Y A* CON EXPLORACION PARCIAL")
    print("Se genera un laberinto nuevo; ambos agentes usan el mismo mapa.")
    print("Los muros permanecen fijos durante los recorridos.")
    while True:
        entrada = input("Semilla (Enter para crear una nueva): ").strip()
        try:
            semilla = int(entrada) if entrada else random.SystemRandom().randrange(10**9)
            break
        except ValueError:
            print("Escribe un numero entero o pulsa Enter.")
    mapa, inicio = generar_laberinto(11, 15, semilla)
    print("Semilla utilizada:", semilla, "(guardala para repetir el laberinto)")
    print("Mapa completo SOLO para el observador:")
    for fila in mapa:
        print(" ".join(fila))

    resultados = {}
    for tipo in ("BFS", "A*"):
        resultados[tipo] = ejecutar_agente(mapa, inicio, tipo)
        mostrar_resultado(tipo, resultados[tipo], len(mapa), len(mapa[0]))
    print("\nCOMPARACION FINAL")
    print(f"{'Agente':<9}{'Movimientos':>13}{'Visitados':>11}{'Buscador':>11}{'Preparacion':>13}{'Tiempo ms':>13}")
    for tipo, r in resultados.items():
        print(f"{tipo:<9}{len(r['recorrido']) - 1:>13}{len(r['visitados']):>11}"
              f"{r['expandidos']:>11}{r['preparacion']:>13}{r['tiempo_ms']:>13.4f}")
    print("\nBuscador y preparacion cuentan trabajo acumulado, no celdas unicas.")
    print("A* elige zonas por descubrir y planifica sobre conexiones conocidas.")
    print("La ruta minima descubierta se calcula despues; no es todo el recorrido.")
    print("No se garantiza una primera exploracion globalmente optima.")
    print("Con un mismo mapa y reglas de desempate, BFS y A* son deterministas.")


if __name__ == "__main__":
    main()
