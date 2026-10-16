"""Semana 03: agente BDI.
"""
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class TelemetriaCluster:
    ciclo: int
    cpu_pct: float
    latencia_ms: float
    alerta_siem: bool
    cuota_agotada: bool = False
    # La plantilla no proporciona una señal para detectar una caída de caché.
    # Agregamos una señal explícita en lugar de deducirla solo de la latencia.
    cache_caida: bool = False


@dataclass
class Deseo:
    nombre: str
    prioridad: int


@dataclass
class PlanBDI:
    nombre: str
    intencion_meta: str
    precondicion: Callable[[Dict[str, Any]], bool]
    cuerpo_acciones: List[str]


SEGURIDAD = "MITIGAR_INTRUSION_SEGURIDAD"
CACHE = "RESTAURAR_SERVICIO_CACHE"
OOM = "PREVENIR_CAIDA_OOM"
SLA = "ESTABILIZAR_RENDIMIENTO_SLA"
PRINCIPAL = "Runbook_Autoescalado_Horizontal"
ALTERNATIVO = "Runbook_Degradacion_Elegante_CircuitBreaker"
# Decisión de diseño: la guía no fija el umbral de latencia del SLA.
UMBRAL_LATENCIA_MS = 200.0


def crear_biblioteca() -> List[PlanBDI]:
    # El orden importa: para SLA se intenta primero el plan principal.
    # Los planes de seguridad, caché y OOM son propuestas para esta simulación.
    return [
        PlanBDI("Runbook_Seguridad", SEGURIDAD,
                lambda b: b["bajo_ataque"],
                ["BLOQUEAR_ORIGEN_MALICIOSO", "AISLAR_SERVICIO_COMPROMETIDO"]),
        PlanBDI("Runbook_Cache", CACHE,
                lambda b: b["cache_caida"],
                ["REINICIAR_SERVICIO_CACHE", "VERIFICAR_SALUD_CACHE"]),
        PlanBDI("Runbook_Prevencion_OOM", OOM,
                lambda b: b["anomalia_fuga_memoria"],
                ["CAPTURAR_DIAGNOSTICO_MEMORIA", "REINICIAR_POD_CONTROLADAMENTE"]),
        PlanBDI(PRINCIPAL, SLA,
                lambda b: not b["cuota_cloud_agotada"],
                ["APROVISIONAR_NODO_REPLICA_K8S", "REBALANCEAR_TRAFICO_INGRESS"]),
        PlanBDI(ALTERNATIVO, SLA,
                lambda b: True,
                ["ACTIVAR_CIRCUIT_BREAKER_RECOMENDACIONES",
                 "HABILITAR_RESPUESTA_ESTATICA_CDN"]),
    ]


class AgenteBDI_Estudiante:
    def __init__(self):
        self.creencias: Dict[str, Any] = {
            "historial_cpu": [],
            "anomalia_fuga_memoria": False,
            "bajo_ataque": False,
            "cuota_cloud_agotada": False,
            "cache_caida": False,
            "cpu_pct": 0.0,
            "latencia_ms": 0.0,
            "plan_fallido": None,
        }
        self.intencion_actual: Optional[Deseo] = None
        self.plan_activo: Optional[PlanBDI] = None
        self.cola_acciones: List[str] = []
        self.biblioteca = crear_biblioteca()

    def brf(self, p: TelemetriaCluster) -> None:
        """Actualizar las creencias con la percepción y aplicar la deducción."""
        b = self.creencias
        b["cpu_pct"] = p.cpu_pct
        b["latencia_ms"] = p.latencia_ms
        b["bajo_ataque"] = p.alerta_siem
        b["cuota_cloud_agotada"] = p.cuota_agotada
        b["cache_caida"] = p.cache_caida
        historial = b["historial_cpu"]
        historial.append(p.cpu_pct)
        if len(historial) > 3:
            historial.pop(0)

        b["anomalia_fuga_memoria"] = False
        if len(historial) == 3:
            p1, p2, p3 = historial
            # aumento > 15 puntos porcentuales en
            # CADA intervalo, suponiendo ciclos consecutivos y equidistantes.
            b["anomalia_fuga_memoria"] = (
                p1 < p2 < p3 and p2 - p1 > 15.0 and p3 - p2 > 15.0
            )
        # La creencia se recalcula: no queda activada indefinidamente.

    def options(self) -> Dict[str, Deseo]:
        """Generar deseos; varios pueden estar activos simultáneamente."""
        b = self.creencias
        opciones = {}
        if b["bajo_ataque"]:
            opciones[SEGURIDAD] = Deseo(SEGURIDAD, 100)
        if b["cache_caida"]:
            opciones[CACHE] = Deseo(CACHE, 80)
        if b["anomalia_fuga_memoria"]:
            opciones[OOM] = Deseo(OOM, 75)
        if b["cpu_pct"] >= 80.0 or b["latencia_ms"] > UMBRAL_LATENCIA_MS:
            opciones[SLA] = Deseo(SLA, 60)
        return opciones

    def filter(self, opciones: Dict[str, Deseo]) -> Optional[Deseo]:
        """Mente abierta: reconsiderar la prioridad en cada ciclo."""
        if not opciones:
            return None
        return max(opciones.values(), key=lambda d: d.prioridad)

    def seleccionar_plan_fallback(
        self, intencion: Deseo, biblioteca: List[PlanBDI]
    ) -> Optional[PlanBDI]:
        for plan in biblioteca:
            if (plan.intencion_meta == intencion.nombre
                    and plan.nombre != self.creencias["plan_fallido"]
                    and plan.precondicion(self.creencias)):
                return plan
        return None

    def deliberar(self, p: TelemetriaCluster) -> None:
        """Percibir, revisar creencias, reconsiderar intención y preparar plan."""
        print(f"\nCiclo {p.ciclo}: CPU={p.cpu_pct:.1f}%, latencia={p.latencia_ms:.1f} ms")
        self.brf(p)
        print("  Historial CPU:", self.creencias["historial_cpu"])
        print("  Anomalía de memoria:", self.creencias["anomalia_fuga_memoria"])

        # Detectar inviabilidad antes de ejecutar la siguiente acción.
        if (self.plan_activo is not None
                and self.plan_activo.nombre == PRINCIPAL
                and self.creencias["cuota_cloud_agotada"]):
            self.creencias["plan_fallido"] = self.plan_activo.nombre
            print("  Plan inviable por cuota agotada:", self.plan_activo.nombre)
            self.plan_activo = None
            self.cola_acciones.clear()
            # No se borra la intención: se buscará otro medio para cumplirla.

        opciones = self.options()
        print("  Deseos:", [(d.nombre, d.prioridad) for d in opciones.values()])
        elegida = self.filter(opciones)
        anterior = self.intencion_actual.nombre if self.intencion_actual else None
        nueva = elegida.nombre if elegida else None

        if nueva != anterior:
            print(f"  Cambio de intención: {anterior} -> {nueva}")
            self.intencion_actual = elegida
            self.plan_activo = None
            self.cola_acciones.clear()
            # El registro del fallo dura todo el compromiso con esa intención,
            # para no reintentar el plan fallido en un bucle.
            self.creencias["plan_fallido"] = None
        elif elegida is not None:
            print("  Se mantiene la intención:", nueva)

        if self.intencion_actual is None:
            print("  Sin objetivos pendientes.")
            return
        if self.plan_activo is None:
            self.plan_activo = self.seleccionar_plan_fallback(
                self.intencion_actual, self.biblioteca
            )
            if self.plan_activo is None:
                print("  No hay plan aplicable; se mantiene la intención.")
                return
            # Copia: no se modifica la lista original de la biblioteca.
            self.cola_acciones = self.plan_activo.cuerpo_acciones.copy()
            print("  Plan seleccionado:", self.plan_activo.nombre)

    def ejecutar_accion(self) -> None:
        """Simular una acción; entre acciones se recibe nueva telemetría."""
        if not self.cola_acciones:
            return
        accion = self.cola_acciones.pop(0)
        print("  Acción simulada:", accion)
        if not self.cola_acciones:
            print("  Plan terminado. Se esperará telemetría para verificar la meta.")
            self.plan_activo = None

    def ciclo(self, p: TelemetriaCluster) -> None:
        self.deliberar(p)
        self.ejecutar_accion()


def main() -> None:
    print("=== EVALUACIÓN EJERCICIO 1: AGENTE BDI ===")
    print("\n--- ESCENARIO 1: inferencia antes del 80% ---")
    agente = AgenteBDI_Estudiante()
    for ciclo, cpu in enumerate([40.0, 58.0, 75.0], start=1):
        agente.ciclo(TelemetriaCluster(ciclo, cpu, 100.0, False))

    print("\n--- ESCENARIO 2: reconsideración ante un ataque ---")
    # La ventana [58, 75, 92] sigue activando OOM; también hay caché caída
    # y CPU crítica. Los cuatro deseos compiten y gana seguridad.
    agente.ciclo(TelemetriaCluster(4, 92.0, 300.0, True, cache_caida=True))

    print("\n--- ESCENARIO 3: cuota agotada durante el plan principal ---")
    agente = AgenteBDI_Estudiante()
    agente.ciclo(TelemetriaCluster(1, 85.0, 300.0, False))
    # La cuota se agota entre acciones; se abandona el resto del plan
    # principal, pero se conserva ESTABILIZAR_RENDIMIENTO_SLA.
    agente.ciclo(TelemetriaCluster(2, 86.0, 310.0, False, True))
    agente.ciclo(TelemetriaCluster(3, 84.0, 280.0, False, True))
    # Esta lectura favorable se proporciona como parte del escenario
    agente.ciclo(TelemetriaCluster(4, 50.0, 100.0, False, True))


if __name__ == "__main__":
    main()