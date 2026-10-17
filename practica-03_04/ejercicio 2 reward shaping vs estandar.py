import random
import numpy as np
from typing import Tuple


class EntornoGridworldEstocastico:
    def __init__(self, reward_shaping: bool = False):
        self.filas = 4
        self.columnas = 4
        self.n_estados = 16
        self.n_acciones = 4  # 0: izquierda, 1: abajo, 2: derecha, 3: arriba
        self.agujeros = {5, 7, 11, 12}
        self.meta = 15
        self.estado_actual = 0
        self.reward_shaping = reward_shaping

    def reset(self) -> int:
        self.estado_actual = 0
        return self.estado_actual

    def step(self, accion: int) -> Tuple[int, float, bool]:
        if random.random() >= (1.0 / 3.0):
            accion = (accion + random.choice([-1, 1])) % 4

        r, c = divmod(self.estado_actual, self.columnas)
        if accion == 0:
            c = max(0, c - 1)
        elif accion == 1:
            r = min(self.filas - 1, r + 1)
        elif accion == 2:
            c = min(self.columnas - 1, c + 1)
        elif accion == 3:
            r = max(0, r - 1)

        nuevo_estado = r * self.columnas + c
        self.estado_actual = nuevo_estado

        terminado = False
        if nuevo_estado in self.agujeros:
            terminado = True
            recompensa = -1.0 if self.reward_shaping else 0.0
        elif nuevo_estado == self.meta:
            terminado = True
            recompensa = 1.0
        else:
            recompensa = -0.01 if self.reward_shaping else 0.0

        return nuevo_estado, recompensa, terminado


def entrenar_q_learning(
    env, episodios=5000, alpha=0.2, gamma=0.95, max_pasos=100, semilla=None
):

    if semilla is not None:
        random.seed(semilla)
        np.random.seed(semilla)

    q_table = np.zeros((env.n_estados, env.n_acciones))
    epsilon = 1.0
    epsilon_min = 0.01
    decaimiento = 0.995
    exitos_bloque = 0
    tasas_exito = []

    for ep in range(1, episodios + 1):
        state = env.reset()
        done = False
        exito = False

        for _ in range(max_pasos):
            if random.random() < epsilon:
                action = random.randint(0, env.n_acciones - 1)
            else:
                mejores = np.flatnonzero(q_table[state] == np.max(q_table[state]))
                action = int(random.choice(mejores.tolist()))

            next_state, reward, done = env.step(action)

            if done:
                td_target = reward
                if next_state == env.meta:
                    exito = True
            else:
                td_target = reward + gamma * np.max(q_table[next_state, :])

            td_error = td_target - q_table[state, action]
            q_table[state, action] += alpha * td_error
            state = next_state

            if done:
                break

        exitos_bloque += int(exito)
        epsilon = max(epsilon_min, epsilon * decaimiento)

        if ep % 100 == 0:
            tasa = exitos_bloque / 100.0
            tasas_exito.append(tasa)
            print(
                f"Episodios {ep - 99:4d}-{ep:4d}: "
                f"éxito medio = {tasa:.1%}; epsilon = {epsilon:.3f}"
            )
            exitos_bloque = 0

    return q_table, tasas_exito


if __name__ == "__main__":
    print("ejercicio 2: aprendisaje con refuerzo normal vs reward shaping")

    print("\nrefuerzo normal")
    env_estandar = EntornoGridworldEstocastico(reward_shaping=False)
    q_estandar, tasas_estandar = entrenar_q_learning(env_estandar, episodios=2000, semilla=10)

    print("\n refuerzo con reward shaping")
    env_shaping = EntornoGridworldEstocastico(reward_shaping=True)
    q_shaping, tasas_shaping = entrenar_q_learning(env_shaping, episodios=2000, semilla=10)

    print("\nTabla Q refuerzo estandar:", np.round(q_estandar[0, :], 3))
    print("Tabla Q refuerzo reward shaping:", np.round(q_shaping[0, :], 3))

    print("\nResumen de exito por bloques de 100 episodios:")
    print("Estandar:", [round(t * 100, 1) for t in tasas_estandar], "%")
    print("Reward Shaping:", [round(t * 100, 1) for t in tasas_shaping], "%")
