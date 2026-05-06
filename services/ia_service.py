"""
services/ia_service.py
======================
Stub — funciones de IA eliminadas a petición del usuario.
El proyecto funciona completamente sin dependencias de inteligencia artificial.
"""

from typing import Any


class RespuestaIA:
    """Respuesta estructurada del servicio de IA (deshabilitado)."""
    def __init__(self, texto: str = "", tipo: str = "", tokens_usados: int = 0,
                 exito: bool = False, error: str = "", metadata: Any = None):
        self.texto = texto
        self.tipo = tipo
        self.tokens_usados = tokens_usados
        self.exito = exito
        self.error = error
        self.metadata = metadata or {}

    def __bool__(self) -> bool:
        return self.exito and bool(self.texto)


class IAService:
    """Servicio de IA técnica (deshabilitado)."""
    def __init__(self, max_tokens: int = 1500) -> None:
        pass

    def generar_explicacion(self, *args, **kwargs) -> RespuestaIA:
        return RespuestaIA(exito=False, error="Función de IA deshabilitada.")

    def generar_diagnostico(self, *args, **kwargs) -> RespuestaIA:
        return RespuestaIA(exito=False, error="Función de IA deshabilitada.")

    def generar_memoria(self, *args, **kwargs) -> RespuestaIA:
        return RespuestaIA(exito=False, error="Función de IA deshabilitada.")

    def consulta_normativa(self, *args, **kwargs) -> RespuestaIA:
        return RespuestaIA(exito=False, error="Función de IA deshabilitada.")


def resultado_a_dict(resultado: Any) -> dict[str, Any]:
    """Convierte un ResultadoCalculo a dict (stub)."""
    return {}


def resumen_a_dict(resumen: Any) -> dict[str, Any]:
    """Convierte un ResumenEvaluacion a dict (stub)."""
    return {}
