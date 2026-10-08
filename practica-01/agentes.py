# Practica de Agentes Inteligentes: navegacion en una grilla.

import random
import time
from collections import deque

# Mapa adaptado al ejercicio. S = inicio, G = meta, # = muro, . = libre.
mapa = [
    "#############",
    "#...#......G#",
    "#.#.#.###.#.#",
    "#.#...#...#.#",
    "#.#####.###.#",
    "#.....#.....#",
    "###.#.#####.#",
    "#...#.....#.#",
    "#.#######.#.#",
    "#S..........#",
    "#############"
]

# Prioridad fija: arriba, derecha, abajo e izquierda.
movimientos = [(-1, 0), (0, 1), (1, 0), (0, -1)]


def vecinos(posicion):
    fila, columna = posicion
    return [(fila + df, columna + dc) for df, dc in movimientos]


def buscar_inicio(mapa):
    if not mapa or not mapa[0] or any(len(f) != len(mapa[0]) for f in mapa):
        raise ValueError("El mapa debe ser rectangular y no estar vacio.")
    if any(celda not in "#.SG" for fila in mapa for celda in fila):
        raise ValueError("Solo se admiten los simbolos #, ., S y G.")
    if sum(fila.count("S") for fila in mapa) != 1 or sum(fila.count("G") for fila in mapa) != 1:
        raise ValueError("El mapa debe tener una S y una G.")
    for fila in range(len(mapa)):
        for columna in range(len(mapa[0])):
            if mapa[fila][columna] == "S":
                return (fila, columna)


def percibir(mapa, posicion):
    # El sensor solo entrega la celda actual y sus cuatro vecinas.
    percepciones = {}
    for fila, columna in [posicion] + vecinos(posicion):
        if 0 <= fila < len(mapa) and 0 <= columna < len(mapa[0]):
            percepciones[(fila, columna)] = mapa[fila][columna]
    return percepciones


def buscar_camino(conocido, inicio, objetivos):
    # BFS: la cola FIFO permite buscar el objetivo mas cercano.
    cola = deque([inicio])
    padres = {inicio: None}

    while cola:
        actual = cola.popleft()
        if actual in objetivos:
            camino = []
            while actual is not None:
                camino.append(actual)
                actual = padres[actual]
            camino.reverse()
            return camino

        for vecino in vecinos(actual):
            if conocido.get(vecino) in (".", "S", "G") and vecino not in padres:
                padres[vecino] = actual
                cola.append(vecino)
    return []


def ejecutar_agente(mapa, tipo, semilla=None):
    # Esta funcion simula el entorno y coordina las decisiones del agente.
    if tipo not in ("deterministico", "aleatorio"):
        raise ValueError("Tipo de agente desconocido.")
    inicio = buscar_inicio(mapa)
    posicion = inicio
    conocido = {}
    visitados = set()
    recorrido = [inicio]
    pila = [inicio]
    azar = random.Random(semilla)
    limite = (len(mapa) * len(mapa[0])) ** 2
    tiempo_inicio = time.perf_counter()

    while True:
        conocido.update(percibir(mapa, posicion))
        visitados.add(posicion)

        if conocido[posicion] == "G":
            estado = "Meta alcanzada"
            break

        # Las decisiones usan solo la memoria; no consultan el mapa completo.
        if tipo == "deterministico":
            objetivos = {p for p in conocido if conocido[p] == "G"}
            if not objetivos:
                objetivos = {p for p in conocido
                             if conocido[p] != "#" and p not in visitados}
            camino = buscar_camino(conocido, posicion, objetivos)
            if not camino:
                estado = "Sin ruta: se agoto la zona accesible"
                break
            siguiente = camino[1]
        else:
            opciones = [p for p in vecinos(posicion)
                        if conocido.get(p) in (".", "S", "G")
                        and p not in visitados]
            if opciones:
                siguiente = azar.choice(opciones)
                pila.append(siguiente)
            elif len(pila) > 1:
                pila.pop()  # Callejon sin salida: regresar por la pila LIFO.
                siguiente = pila[-1]
            else:
                estado = "Sin ruta: se agoto la zona accesible"
                break

        if len(recorrido) - 1 >= limite:
            estado = "Limite preventivo alcanzado"
            break
        posicion = siguiente
        recorrido.append(posicion)

    tiempo_ms = (time.perf_counter() - tiempo_inicio) * 1000
    metas = {p for p in conocido if conocido[p] == "G"}
    ruta = buscar_camino(conocido, inicio, metas)
    return {"estado": estado, "recorrido": recorrido, "visitados": visitados,
            "conocido": conocido, "ruta": ruta, "tiempo_ms": tiempo_ms}


def mostrar_resultado(nombre, resultado, filas, columnas):
    print("\n" + nombre.upper())
    print("Estado:", resultado["estado"])
    print("Movimientos:", len(resultado["recorrido"]) - 1)
    print("Celdas distintas visitadas:", len(resultado["visitados"]))
    print("Revisitas:", len(resultado["recorrido"]) - len(resultado["visitados"]))
    print(f"Tiempo del bucle: {resultado['tiempo_ms']:.4f} ms")
    print("Recorrido (fila, columna):")
    print(" -> ".join(str(p) for p in resultado["recorrido"]))
    if resultado["ruta"]:
        print("Ruta minima en el mapa descubierto:", len(resultado["ruta"]) - 1, "pasos")
        print(" -> ".join(str(p) for p in resultado["ruta"]))

    print("\nMapa descubierto: ? = desconocido, * = visitado")
    for fila in range(filas):
        linea = []
        for columna in range(columnas):
            posicion = (fila, columna)
            celda = resultado["conocido"].get(posicion, "?")
            if posicion in resultado["visitados"] and celda not in ("S", "G"):
                celda = "*"
            linea.append(celda)
        print(" ".join(linea))


def main():
    print("PRACTICA: DOS AGENTES EN UNA GRILLA 2D")
    print("Cada agente ve su celda y las cuatro vecinas.")
    print("El mapa completo mostrado aqui es solo para el observador:")
    for fila in mapa:
        print(" ".join(fila))

    while True:
        entrada = input("\nSemilla aleatoria (7 para repetir; Enter para variar): ").strip()
        try:
            semilla = int(entrada) if entrada else None
            break
        except ValueError:
            print("Escribe un numero entero o pulsa Enter.")

    deterministico = ejecutar_agente(mapa, "deterministico")
    aleatorio = ejecutar_agente(mapa, "aleatorio", semilla)
    mostrar_resultado("Agente deterministico con BFS", deterministico, len(mapa), len(mapa[0]))
    mostrar_resultado("Agente aleatorio con memoria", aleatorio, len(mapa), len(mapa[0]))

    print("\nCOMPARACION FINAL")
    print(f"{'Agente':<18} {'Movimientos':>12} {'Visitados':>10} {'Tiempo (ms)':>13}")
    for nombre, resultado in [("Deterministico", deterministico), ("Aleatorio", aleatorio)]:
        print(f"{nombre:<18} {len(resultado['recorrido']) - 1:>12} "
              f"{len(resultado['visitados']):>10} {resultado['tiempo_ms']:>13.4f}")
    print("\nLa ruta minima descubierta se calcula despues de explorar.")
    print("No garantiza el minimo global si todavia hay celdas desconocidas.")


if __name__ == "__main__":
    main()
