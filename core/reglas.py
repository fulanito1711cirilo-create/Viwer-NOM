"""
core/reglas.py
==============
Motor de validación normativa para la NOM-001-SEDE-2012.

Diseño basado en el patrón Rule Object:
  - Cada regla es una instancia de `Regla` con condición, mensaje y metadata.
  - El motor evalúa una colección de reglas contra un diccionario de datos.
  - Nuevas reglas se agregan sin modificar el motor ni las reglas existentes.
  - Sin dependencias de UI, framework ni estado externo.

Uso básico:
    from core.reglas import evaluar_cumplimiento, REGLAS_NOM_001

    datos = {
        "caida_pct": 3.8,
        "resistencia_tierra_ohm": 6.2,
        "factor_demanda": 0.75,
        "corriente_estimada_a": 45.0,
        "ampacidad_conductor_a": 35.0,
        "itm_a": 50.0,
    }

    resultados = evaluar_cumplimiento(datos, REGLAS_NOM_001)

    for r in resultados:
        print(r.severidad.upper(), "|", r.nombre, "|", r.cumple, "|", r.mensaje)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


# ==============================================================================
# TIPOS BASE
# ==============================================================================

class Severidad(str, Enum):
    """Nivel de impacto de una regla al ser incumplida."""
    ERROR      = "error"       # Instalación fuera de norma. No debe ejecutarse.
    ADVERTENCIA = "advertencia" # Condición límite o recomendación normativa.
    INFO       = "info"        # Observación técnica sin impacto de seguridad.


class Categoria(str, Enum):
    """Agrupación temática de reglas para filtrado y reporte."""
    CONDUCTORES    = "conductores"
    PROTECCIONES   = "protecciones"
    CARGAS         = "cargas"
    TIERRA         = "tierra"
    TRANSFORMADOR  = "transformador"
    GENERAL        = "general"


# ==============================================================================
# DATACLASSES PRINCIPALES
# ==============================================================================

@dataclass(frozen=True)
class Regla:
    """
    Definición inmutable de una regla normativa.

    Attributes:
        nombre:       Identificador único de la regla (snake_case).
        descripcion:  Qué verifica esta regla en lenguaje técnico.
        condicion:    Función pura (datos: dict) -> bool.
                      Debe retornar True cuando la condición de falla se cumple.
                      Es decir: True → no cumple la norma.
        mensaje_falla: Texto devuelto cuando condicion() retorna True.
        mensaje_ok:   Texto devuelto cuando condicion() retorna False.
        articulo:     Clave del artículo en el MAPA (ej: "art210-19").
        referencia:   Texto legible del artículo para reportes (ej: "Art. 210-19").
        severidad:    Impacto si la regla no se cumple.
        categoria:    Agrupación temática.
        aplica_si:    Función opcional (datos: dict) -> bool.
                      Si retorna False, la regla se omite (no es aplicable).
                      Permite reglas condicionales sin modificar la condicion principal.
    """
    nombre: str
    descripcion: str
    condicion: Callable[[dict[str, Any]], bool]
    mensaje_falla: str
    mensaje_ok: str
    articulo: str
    referencia: str
    severidad: Severidad
    categoria: Categoria
    aplica_si: Optional[Callable[[dict[str, Any]], bool]] = None


@dataclass
class ResultadoRegla:
    """
    Resultado de evaluar una regla contra un conjunto de datos.

    Attributes:
        nombre:     Nombre de la regla evaluada.
        cumple:     True si la instalación cumple esta regla.
        mensaje:    Descripción del resultado para el usuario.
        articulo:   Clave del artículo normativo de referencia.
        referencia: Texto legible del artículo.
        severidad:  Severidad de la regla (relevante cuando cumple=False).
        categoria:  Agrupación temática.
        omitida:    True si la regla no aplica a los datos provistos.
        razon_omision: Descripción de por qué se omitió, si aplica.
    """
    nombre: str
    cumple: bool
    mensaje: str
    articulo: str
    referencia: str
    severidad: Severidad
    categoria: Categoria
    omitida: bool = False
    razon_omision: str = ""


@dataclass
class ResumenEvaluacion:
    """
    Agregado de todos los ResultadoRegla de una evaluación completa.

    Attributes:
        resultados:        Lista completa de ResultadoRegla.
        total_evaluadas:   Reglas que se evaluaron (no omitidas).
        total_cumplidas:   Reglas que se cumplen.
        total_errores:     Reglas con severidad ERROR incumplidas.
        total_advertencias: Reglas con severidad ADVERTENCIA incumplidas.
        cumplimiento_pct:  Porcentaje de cumplimiento sobre evaluadas.
        aprobado:          True solo si no hay ningún ERROR incumplido.
    """
    resultados: list[ResultadoRegla] = field(default_factory=list)
    total_evaluadas: int = 0
    total_cumplidas: int = 0
    total_errores: int = 0
    total_advertencias: int = 0
    cumplimiento_pct: float = 0.0
    aprobado: bool = False

    def filtrar(
        self,
        cumple: Optional[bool] = None,
        severidad: Optional[Severidad] = None,
        categoria: Optional[Categoria] = None,
        omitidas: bool = False,
    ) -> list[ResultadoRegla]:
        """
        Filtra resultados por criterios combinables.

        Args:
            cumple:    Si se provee, filtra por estado de cumplimiento.
            severidad: Si se provee, filtra por nivel de severidad.
            categoria: Si se provee, filtra por categoría temática.
            omitidas:  Si True, incluye reglas omitidas en el resultado.

        Returns:
            Lista de ResultadoRegla que satisfacen todos los criterios.
        """
        resultado = self.resultados
        if not omitidas:
            resultado = [r for r in resultado if not r.omitida]
        if cumple is not None:
            resultado = [r for r in resultado if r.cumple == cumple]
        if severidad is not None:
            resultado = [r for r in resultado if r.severidad == severidad]
        if categoria is not None:
            resultado = [r for r in resultado if r.categoria == categoria]
        return resultado

    def errores_criticos(self) -> list[ResultadoRegla]:
        """Atajo: retorna solo las reglas de severidad ERROR que no se cumplen."""
        return self.filtrar(cumple=False, severidad=Severidad.ERROR)

    def advertencias_activas(self) -> list[ResultadoRegla]:
        """Atajo: retorna solo las reglas de ADVERTENCIA que no se cumplen."""
        return self.filtrar(cumple=False, severidad=Severidad.ADVERTENCIA)


# ==============================================================================
# MOTOR DE EVALUACIÓN
# ==============================================================================

def evaluar_cumplimiento(
    datos: dict[str, Any],
    reglas: list[Regla],
) -> ResumenEvaluacion:
    """
    Evalúa una colección de reglas contra un diccionario de datos de cálculo.

    Proceso por regla:
      1. Si la regla tiene `aplica_si` y retorna False → omitir.
      2. Si faltan las claves que la condición necesita → omitir con razón.
      3. Ejecutar condicion(datos): True = falla, False = cumple.
      4. En caso de excepción en condicion() → omitir con razón de error.

    Args:
        datos:  Diccionario con resultados de cálculos. Las claves deben
                coincidir con las que cada regla espera en su condicion().
                Ejemplo de claves estándar:
                  "caida_pct", "resistencia_tierra_ohm", "factor_demanda",
                  "corriente_carga_a", "ampacidad_conductor_a", "itm_a",
                  "caida_pct_alimentador", "icc_ka", "kaic_ka",
                  "potencia_transformador_kva", "carga_demandada_kva"
        reglas: Lista de instancias de Regla a evaluar.

    Returns:
        ResumenEvaluacion con todos los ResultadoRegla y estadísticas.
    """
    resultados: list[ResultadoRegla] = []

    for regla in reglas:
        # --- Paso 1: verificar si la regla aplica ---
        if regla.aplica_si is not None:
            try:
                if not regla.aplica_si(datos):
                    resultados.append(ResultadoRegla(
                        nombre=regla.nombre,
                        cumple=True,
                        mensaje="Regla no aplicable a este tipo de instalación.",
                        articulo=regla.articulo,
                        referencia=regla.referencia,
                        severidad=regla.severidad,
                        categoria=regla.categoria,
                        omitida=True,
                        razon_omision="Condición de aplicabilidad no satisfecha.",
                    ))
                    continue
            except Exception as exc:
                resultados.append(ResultadoRegla(
                    nombre=regla.nombre,
                    cumple=True,
                    mensaje="No se pudo determinar si la regla aplica.",
                    articulo=regla.articulo,
                    referencia=regla.referencia,
                    severidad=regla.severidad,
                    categoria=regla.categoria,
                    omitida=True,
                    razon_omision=f"Error en aplica_si(): {exc}",
                ))
                continue

        # --- Paso 2: ejecutar la condición ---
        try:
            falla = regla.condicion(datos)
        except KeyError as exc:
            resultados.append(ResultadoRegla(
                nombre=regla.nombre,
                cumple=True,
                mensaje="Dato requerido no disponible.",
                articulo=regla.articulo,
                referencia=regla.referencia,
                severidad=regla.severidad,
                categoria=regla.categoria,
                omitida=True,
                razon_omision=f"Clave faltante en datos: {exc}",
            ))
            continue
        except Exception as exc:
            resultados.append(ResultadoRegla(
                nombre=regla.nombre,
                cumple=True,
                mensaje="Error al evaluar la regla.",
                articulo=regla.articulo,
                referencia=regla.referencia,
                severidad=regla.severidad,
                categoria=regla.categoria,
                omitida=True,
                razon_omision=f"Excepción en condicion(): {exc}",
            ))
            continue

        # --- Paso 3: construir resultado ---
        cumple = not falla
        resultados.append(ResultadoRegla(
            nombre=regla.nombre,
            cumple=cumple,
            mensaje=regla.mensaje_ok if cumple else regla.mensaje_falla,
            articulo=regla.articulo,
            referencia=regla.referencia,
            severidad=regla.severidad,
            categoria=regla.categoria,
        ))

    # --- Estadísticas ---
    evaluadas = [r for r in resultados if not r.omitida]
    cumplidas = [r for r in evaluadas if r.cumple]
    errores = [r for r in evaluadas if not r.cumple and r.severidad == Severidad.ERROR]
    advertencias = [r for r in evaluadas if not r.cumple and r.severidad == Severidad.ADVERTENCIA]

    total_ev = len(evaluadas)
    total_cum = len(cumplidas)
    pct = (total_cum / total_ev * 100.0) if total_ev > 0 else 100.0

    return ResumenEvaluacion(
        resultados=resultados,
        total_evaluadas=total_ev,
        total_cumplidas=total_cum,
        total_errores=len(errores),
        total_advertencias=len(advertencias),
        cumplimiento_pct=round(pct, 1),
        aprobado=len(errores) == 0,
    )


# ==============================================================================
# REGLAS NOM-001-SEDE-2012
# ==============================================================================
# Cada regla es inmutable. Para agregar una nueva: instanciar Regla y añadirla
# a REGLAS_NOM_001. No modificar el motor ni las reglas existentes.

REGLAS_NOM_001: list[Regla] = [

    # --------------------------------------------------------------------------
    # CATEGORÍA: CONDUCTORES
    # --------------------------------------------------------------------------

    Regla(
        nombre="caida_tension_circuito_derivado",
        descripcion="La caída de tensión en el circuito derivado no debe exceder el 3%.",
        condicion=lambda d: d["caida_pct"] > 3.0,
        mensaje_falla=(
            "Caída de tensión ({caida_pct:.2f}%) supera el límite del 3% "
            "en circuito derivado. Aumentar calibre o reducir longitud."
        ),
        mensaje_ok="Caída de tensión ({caida_pct:.2f}%) dentro del límite del 3%.",
        articulo="art210-19",
        referencia="Art. 210-19(a)(1)",
        severidad=Severidad.ERROR,
        categoria=Categoria.CONDUCTORES,
    ),

    Regla(
        nombre="caida_tension_total",
        descripcion="La caída de tensión acumulada (alimentador + circuito) no debe exceder el 5%.",
        condicion=lambda d: d.get("caida_pct_total", d["caida_pct"]) > 5.0,
        mensaje_falla=(
            "Caída de tensión total ({caida_pct_total:.2f}%) supera el límite del 5%. "
            "Revisar alimentador y circuito derivado."
        ),
        mensaje_ok="Caída de tensión total ({caida_pct_total:.2f}%) dentro del límite del 5%.",
        articulo="art215-2",
        referencia="Art. 215-2(a)(3)",
        severidad=Severidad.ERROR,
        categoria=Categoria.CONDUCTORES,
    ),

    Regla(
        nombre="caida_tension_alimentador",
        descripcion="La caída de tensión solo en el alimentador no debe exceder el 2% (práctica recomendada).",
        condicion=lambda d: d["caida_pct_alimentador"] > 2.0,
        mensaje_falla=(
            "Caída de tensión en alimentador ({caida_pct_alimentador:.2f}%) "
            "supera el 2% recomendado. Considerar aumento de calibre del alimentador."
        ),
        mensaje_ok="Caída en alimentador ({caida_pct_alimentador:.2f}%) dentro del 2% recomendado.",
        articulo="art215-2",
        referencia="Art. 215-2(a)(3)",
        severidad=Severidad.ADVERTENCIA,
        categoria=Categoria.CONDUCTORES,
        aplica_si=lambda d: "caida_pct_alimentador" in d,
    ),

    Regla(
        nombre="coordinacion_conductor_proteccion",
        descripcion="El ITM no debe superar la ampacidad corregida del conductor que protege.",
        condicion=lambda d: d["itm_a"] > d["ampacidad_conductor_a"],
        mensaje_falla=(
            "ITM ({itm_a} A) supera la ampacidad del conductor ({ampacidad_conductor_a:.1f} A). "
            "Aumentar calibre del conductor o seleccionar ITM menor. Art. 240-4."
        ),
        mensaje_ok=(
            "Coordinación conductor-protección correcta: "
            "ITM ({itm_a} A) ≤ ampacidad ({ampacidad_conductor_a:.1f} A)."
        ),
        articulo="art240",
        referencia="Art. 240-4",
        severidad=Severidad.ERROR,
        categoria=Categoria.CONDUCTORES,
        aplica_si=lambda d: "itm_a" in d and "ampacidad_conductor_a" in d,
    ),

    Regla(
        nombre="temperatura_conductor_compatible",
        descripcion="La temperatura de operación del conductor debe ser compatible con las terminales (75°C máx en borneras estándar).",
        condicion=lambda d: d.get("temp_conductor_c", 75) > 75,
        mensaje_falla=(
            "Temperatura del conductor ({temp_conductor_c}°C) supera 75°C. "
            "Verificar compatibilidad con terminales. Art. 110-14(C)."
        ),
        mensaje_ok="Temperatura del conductor compatible con terminales (≤ 75°C).",
        articulo="Art110.14(C)",
        referencia="Art. 110-14(C)",
        severidad=Severidad.ADVERTENCIA,
        categoria=Categoria.CONDUCTORES,
        aplica_si=lambda d: "temp_conductor_c" in d,
    ),

    # --------------------------------------------------------------------------
    # CATEGORÍA: PROTECCIONES
    # --------------------------------------------------------------------------

    Regla(
        nombre="capacidad_interruptiva_suficiente",
        descripcion="La capacidad interruptiva del ITM debe ser ≥ corriente de cortocircuito disponible.",
        condicion=lambda d: d["kaic_ka"] < d["icc_ka"],
        mensaje_falla=(
            "Capacidad interruptiva ({kaic_ka} kA) insuficiente para la Icc disponible "
            "({icc_ka:.1f} kA). Seleccionar ITM con mayor kAIC."
        ),
        mensaje_ok=(
            "Capacidad interruptiva ({kaic_ka} kA) adecuada para Icc disponible ({icc_ka:.1f} kA)."
        ),
        articulo="art240",
        referencia="Art. 240 — Capacidad interruptiva",
        severidad=Severidad.ERROR,
        categoria=Categoria.PROTECCIONES,
        aplica_si=lambda d: "kaic_ka" in d and "icc_ka" in d,
    ),

    Regla(
        nombre="proteccion_carga_continua",
        descripcion="Para cargas continuas el ITM debe ser ≥ 125% de la corriente de carga.",
        condicion=lambda d: d["itm_a"] < d["corriente_carga_a"] * 1.25,
        mensaje_falla=(
            "ITM ({itm_a} A) menor que el 125% de la corriente de carga "
            "({corriente_carga_a:.1f} × 1.25 = {corriente_minima:.1f} A). Art. 210-20."
        ),
        mensaje_ok=(
            "ITM ({itm_a} A) cumple el 125% de carga continua "
            "({corriente_carga_a:.1f} × 1.25 = {corriente_minima:.1f} A)."
        ),
        articulo="art240",
        referencia="Art. 210-20(A) — Cargas continuas",
        severidad=Severidad.ERROR,
        categoria=Categoria.PROTECCIONES,
        aplica_si=lambda d: d.get("tipo_carga") == "General" and "itm_a" in d and "corriente_carga_a" in d,
    ),

    Regla(
        nombre="proteccion_motor_arranque",
        descripcion="Para motores, la protección contra sobrecorriente no debe exceder el 150% de I_nominal.",
        condicion=lambda d: d["itm_a"] > d["corriente_carga_a"] * 1.5,
        mensaje_falla=(
            "ITM para motor ({itm_a} A) excede el 150% de I_nominal "
            "({corriente_carga_a:.1f} × 1.5 = {corriente_max_motor:.1f} A). Art. 430-52."
        ),
        mensaje_ok=(
            "Protección de motor ({itm_a} A) dentro del 150% de I_nominal "
            "({corriente_carga_a:.1f} × 1.5 = {corriente_max_motor:.1f} A)."
        ),
        articulo="art430-31",
        referencia="Art. 430-52, Tabla 430-52",
        severidad=Severidad.ERROR,
        categoria=Categoria.PROTECCIONES,
        aplica_si=lambda d: d.get("tipo_carga") == "Motor" and "itm_a" in d and "corriente_carga_a" in d,
    ),

    Regla(
        nombre="proteccion_transformador_primario",
        descripcion="La protección primaria del transformador no debe exceder el 125% de I_prim para ≥ 9 A.",
        condicion=lambda d: d["itm_primario_a"] > d["I_primario_a"] * 1.25,
        mensaje_falla=(
            "Protección primaria ({itm_primario_a} A) excede el 125% de I_prim "
            "({I_primario_a:.1f} × 1.25 = {prot_max:.1f} A). Art. 450-3."
        ),
        mensaje_ok=(
            "Protección primaria ({itm_primario_a} A) dentro del 125% de I_prim "
            "({I_primario_a:.1f} A)."
        ),
        articulo="art450-3",
        referencia="Art. 450-3(B)(1)",
        severidad=Severidad.ERROR,
        categoria=Categoria.PROTECCIONES,
        aplica_si=lambda d: "itm_primario_a" in d and "I_primario_a" in d and d.get("I_primario_a", 0) >= 9,
    ),

    # --------------------------------------------------------------------------
    # CATEGORÍA: CARGAS
    # --------------------------------------------------------------------------

    Regla(
        nombre="factor_demanda_en_rango",
        descripcion="El factor de demanda aplicado debe estar entre 0 y 1 (valores normalizados).",
        condicion=lambda d: not (0.0 < d["factor_demanda"] <= 1.0),
        mensaje_falla=(
            "Factor de demanda ({factor_demanda:.3f}) fuera del rango válido (0, 1]. "
            "Verificar el tipo de inmueble y la tabla de factores aplicada."
        ),
        mensaje_ok="Factor de demanda ({factor_demanda:.2f}) en rango válido (0, 1].",
        articulo="art220",
        referencia="Art. 220 — Cálculo de cargas",
        severidad=Severidad.ERROR,
        categoria=Categoria.CARGAS,
    ),

    Regla(
        nombre="alumbrado_minimo_vivienda",
        descripcion="La carga de alumbrado en vivienda debe ser ≥ 33 VA/m² (Art. 220-12).",
        condicion=lambda d: (d["alumbrado_va"] / d["area_m2"]) < 33.0,
        mensaje_falla=(
            "Densidad de alumbrado ({densidad_va_m2:.1f} VA/m²) inferior al mínimo "
            "de 33 VA/m² para vivienda. Art. 220-12."
        ),
        mensaje_ok=(
            "Densidad de alumbrado ({densidad_va_m2:.1f} VA/m²) cumple el mínimo "
            "de 33 VA/m² para vivienda."
        ),
        articulo="art220-12",
        referencia="Art. 220-12",
        severidad=Severidad.ERROR,
        categoria=Categoria.CARGAS,
        aplica_si=lambda d: (
            "alumbrado_va" in d
            and "area_m2" in d
            and d.get("area_m2", 0) > 0
            and d.get("tipo_inmueble", "") in ("Vivienda unifamiliar", "Departamento")
        ),
    ),

    Regla(
        nombre="circuitos_especiales_vivienda",
        descripcion="Viviendas deben incluir circuitos especiales: 2 × 1500 VA + 1 × 1500 VA lavandería (Art. 220-52).",
        condicion=lambda d: d.get("especiales_va", 0) < 4500.0,
        mensaje_falla=(
            "Circuitos especiales de vivienda ({especiales_va:.0f} VA) insuficientes. "
            "Se requieren mínimo 4500 VA (2 × pequeños aparatos + lavandería). Art. 220-52."
        ),
        mensaje_ok=(
            "Circuitos especiales de vivienda ({especiales_va:.0f} VA) "
            "cumplen el mínimo de 4500 VA."
        ),
        articulo="art220-52",
        referencia="Art. 220-52",
        severidad=Severidad.ADVERTENCIA,
        categoria=Categoria.CARGAS,
        aplica_si=lambda d: d.get("tipo_inmueble", "") in ("Vivienda unifamiliar", "Departamento"),
    ),

    Regla(
        nombre="factor_potencia_aceptable",
        descripcion="El factor de potencia del sistema debería ser ≥ 0.90 para evitar penalizaciones CFE.",
        condicion=lambda d: d["factor_potencia"] < 0.90,
        mensaje_falla=(
            "Factor de potencia ({factor_potencia:.3f}) inferior a 0.90. "
            "Considerar corrección con banco de capacitores para evitar penalización tarifaria."
        ),
        mensaje_ok="Factor de potencia ({factor_potencia:.3f}) aceptable (≥ 0.90).",
        articulo="art215",
        referencia="Art. 215 — Recomendación FP ≥ 0.90",
        severidad=Severidad.ADVERTENCIA,
        categoria=Categoria.CARGAS,
        aplica_si=lambda d: "factor_potencia" in d,
    ),

    Regla(
        nombre="carga_motor_factor_125",
        descripcion="La carga del motor mayor debe calcularse al 125% sobre la corriente nominal (Art. 430).",
        condicion=lambda d: d.get("carga_motor_mayor_w", 0) > 0 and d.get("factor_motor_aplicado", 1.25) < 1.25,
        mensaje_falla=(
            "Factor aplicado al motor mayor ({factor_motor_aplicado:.2f}) "
            "inferior al 125% requerido. Art. 430, Art. 220-50."
        ),
        mensaje_ok="Factor del 125% aplicado correctamente al motor mayor.",
        articulo="art430",
        referencia="Art. 430 — Art. 220-50",
        severidad=Severidad.ERROR,
        categoria=Categoria.CARGAS,
        aplica_si=lambda d: "carga_motor_mayor_w" in d and d.get("carga_motor_mayor_w", 0) > 0,
    ),

    # --------------------------------------------------------------------------
    # CATEGORÍA: TIERRA
    # --------------------------------------------------------------------------

    Regla(
        nombre="resistencia_tierra_recomendada",
        descripcion="La resistencia de puesta a tierra debe ser ≤ 5 Ω (valor recomendado por la norma).",
        condicion=lambda d: d["resistencia_tierra_ohm"] > 5.0,
        mensaje_falla=(
            "Resistencia de tierra ({resistencia_tierra_ohm:.2f} Ω) supera el valor "
            "recomendado de 5 Ω. Instalar electrodos adicionales en paralelo. Art. 250-52."
        ),
        mensaje_ok=(
            "Resistencia de tierra ({resistencia_tierra_ohm:.2f} Ω) "
            "dentro del valor recomendado de 5 Ω."
        ),
        articulo="art250-52",
        referencia="Art. 250-52 — Valor recomendado ≤ 5 Ω",
        severidad=Severidad.ADVERTENCIA,
        categoria=Categoria.TIERRA,
    ),

    Regla(
        nombre="resistencia_tierra_normativa",
        descripcion="La resistencia de puesta a tierra no debe exceder 25 Ω (límite absoluto NOM).",
        condicion=lambda d: d["resistencia_tierra_ohm"] > 25.0,
        mensaje_falla=(
            "Resistencia de tierra ({resistencia_tierra_ohm:.2f} Ω) supera el límite "
            "absoluto de 25 Ω. Instalación FUERA DE NORMA. Art. 250."
        ),
        mensaje_ok=(
            "Resistencia de tierra ({resistencia_tierra_ohm:.2f} Ω) "
            "dentro del límite normativo de 25 Ω."
        ),
        articulo="art250",
        referencia="Art. 250 — Límite absoluto ≤ 25 Ω",
        severidad=Severidad.ERROR,
        categoria=Categoria.TIERRA,
    ),

    Regla(
        nombre="profundidad_electrodo_varilla",
        descripcion="Las varillas de tierra deben tener longitud mínima de 2.44 m (8 ft) en contacto con el suelo.",
        condicion=lambda d: d["longitud_electrodo_m"] < 2.44,
        mensaje_falla=(
            "Electrodo ({longitud_electrodo_m:.2f} m) inferior al mínimo de 2.44 m. "
            "Reemplazar o instalar electrodo adicional. Art. 250-52(A)(5)."
        ),
        mensaje_ok=(
            "Longitud del electrodo ({longitud_electrodo_m:.2f} m) "
            "cumple el mínimo de 2.44 m."
        ),
        articulo="art250-52",
        referencia="Art. 250-52(A)(5)",
        severidad=Severidad.ERROR,
        categoria=Categoria.TIERRA,
        aplica_si=lambda d: "longitud_electrodo_m" in d,
    ),

    Regla(
        nombre="separacion_entre_electrodos",
        descripcion="La separación entre electrodos de tierra debe ser ≥ 1.80 m.",
        condicion=lambda d: d["separacion_electrodos_m"] < 1.80,
        mensaje_falla=(
            "Separación entre electrodos ({separacion_electrodos_m:.2f} m) "
            "inferior al mínimo de 1.80 m. Art. 250-53(B)."
        ),
        mensaje_ok=(
            "Separación entre electrodos ({separacion_electrodos_m:.2f} m) "
            "cumple el mínimo de 1.80 m."
        ),
        articulo="art250-52",
        referencia="Art. 250-53(B)",
        severidad=Severidad.ERROR,
        categoria=Categoria.TIERRA,
        aplica_si=lambda d: "separacion_electrodos_m" in d,
    ),

    # --------------------------------------------------------------------------
    # CATEGORÍA: TRANSFORMADOR
    # --------------------------------------------------------------------------

    Regla(
        nombre="reserva_transformador",
        descripcion="El transformador debe tener al menos 15% de reserva sobre la carga demandada.",
        condicion=lambda d: d["potencia_transformador_kva"] < d["carga_demandada_kva"] * 1.15,
        mensaje_falla=(
            "Transformador ({potencia_transformador_kva} kVA) con reserva insuficiente "
            "para la carga demandada ({carga_demandada_kva:.1f} kVA). "
            "Se recomienda al menos 15% de margen. Art. 450."
        ),
        mensaje_ok=(
            "Transformador ({potencia_transformador_kva} kVA) con reserva adecuada "
            "sobre carga demandada ({carga_demandada_kva:.1f} kVA)."
        ),
        articulo="art450",
        referencia="Art. 450 — Reserva mínima recomendada 15%",
        severidad=Severidad.ADVERTENCIA,
        categoria=Categoria.TRANSFORMADOR,
        aplica_si=lambda d: "potencia_transformador_kva" in d and "carga_demandada_kva" in d,
    ),

    Regla(
        nombre="transformador_sobrecargado",
        descripcion="El transformador no debe operar por encima de su potencia nominal.",
        condicion=lambda d: d["carga_demandada_kva"] > d["potencia_transformador_kva"],
        mensaje_falla=(
            "Carga demandada ({carga_demandada_kva:.1f} kVA) supera la potencia nominal "
            "del transformador ({potencia_transformador_kva} kVA). "
            "Instalación en sobrecarga. Art. 450."
        ),
        mensaje_ok=(
            "Carga demandada ({carga_demandada_kva:.1f} kVA) dentro de la potencia "
            "nominal del transformador ({potencia_transformador_kva} kVA)."
        ),
        articulo="art450",
        referencia="Art. 450 — Operación dentro de potencia nominal",
        severidad=Severidad.ERROR,
        categoria=Categoria.TRANSFORMADOR,
        aplica_si=lambda d: "potencia_transformador_kva" in d and "carga_demandada_kva" in d,
    ),

    # --------------------------------------------------------------------------
    # CATEGORÍA: GENERAL
    # --------------------------------------------------------------------------

    Regla(
        nombre="voltaje_nominal_en_rango",
        descripcion="El voltaje nominal del sistema debe ser un valor estándar en México (120, 127, 208, 220, 480 V).",
        condicion=lambda d: d["voltaje_v"] not in (120, 127, 208, 220, 277, 480),
        mensaje_falla=(
            "Voltaje nominal ({voltaje_v} V) no es un valor estándar para México. "
            "Verificar el nivel de tensión del suministro CFE."
        ),
        mensaje_ok="Voltaje nominal ({voltaje_v} V) es un valor estándar para México.",
        articulo="nom001",
        referencia="NOM-001-SEDE-2012 — Tensiones nominales estándar",
        severidad=Severidad.ADVERTENCIA,
        categoria=Categoria.GENERAL,
        aplica_si=lambda d: "voltaje_v" in d,
    ),

    Regla(
        nombre="corriente_no_supera_ampacidad",
        descripcion="La corriente de operación no debe superar la ampacidad corregida del conductor.",
        condicion=lambda d: d["corriente_carga_a"] > d["ampacidad_conductor_a"],
        mensaje_falla=(
            "Corriente de carga ({corriente_carga_a:.1f} A) supera la ampacidad "
            "del conductor ({ampacidad_conductor_a:.1f} A). "
            "Conductor en sobrecarga. Art. 310."
        ),
        mensaje_ok=(
            "Corriente de carga ({corriente_carga_a:.1f} A) dentro de la ampacidad "
            "del conductor ({ampacidad_conductor_a:.1f} A)."
        ),
        articulo="art310",
        referencia="Art. 310 — Ampacidad de conductores",
        severidad=Severidad.ERROR,
        categoria=Categoria.GENERAL,
        aplica_si=lambda d: "corriente_carga_a" in d and "ampacidad_conductor_a" in d,
    ),
]


# ==============================================================================
# FUNCIÓN DE FORMATO DE MENSAJES
# ==============================================================================

def _formatear_mensaje(plantilla: str, datos: dict[str, Any]) -> str:
    """
    Sustituye las variables en la plantilla de mensaje con valores reales de datos.
    También inyecta variables derivadas útiles para los mensajes.

    Derivadas automáticas:
      - caida_pct_total: datos.get("caida_pct_total", datos.get("caida_pct"))
      - densidad_va_m2:  alumbrado_va / area_m2
      - corriente_minima: corriente_carga_a * 1.25
      - corriente_max_motor: corriente_carga_a * 1.5
      - prot_max: I_primario_a * 1.25

    Args:
        plantilla: String con placeholders tipo {nombre_variable:.2f}
        datos:     Diccionario con los valores originales del cálculo.

    Returns:
        Mensaje con variables sustituidas. Si falta una variable, devuelve la plantilla original.
    """
    extendido = dict(datos)

    # Variables derivadas para mensajes
    extendido.setdefault("caida_pct_total", datos.get("caida_pct_total", datos.get("caida_pct", 0.0)))
    if "alumbrado_va" in datos and "area_m2" in datos and datos["area_m2"] > 0:
        extendido.setdefault("densidad_va_m2", datos["alumbrado_va"] / datos["area_m2"])
    if "corriente_carga_a" in datos:
        extendido.setdefault("corriente_minima", datos["corriente_carga_a"] * 1.25)
        extendido.setdefault("corriente_max_motor", datos["corriente_carga_a"] * 1.5)
    if "I_primario_a" in datos:
        extendido.setdefault("prot_max", datos["I_primario_a"] * 1.25)

    try:
        return plantilla.format(**extendido)
    except (KeyError, ValueError):
        return plantilla


def evaluar_y_formatear(
    datos: dict[str, Any],
    reglas: list[Regla] = REGLAS_NOM_001,
) -> ResumenEvaluacion:
    """
    Evalúa las reglas y formatea todos los mensajes con los valores reales.

    Equivalente a evaluar_cumplimiento() pero con mensajes listos para mostrar
    en UI o reportes sin procesamiento adicional.

    Args:
        datos:  Diccionario con resultados de cálculos.
        reglas: Lista de Regla a evaluar (default: REGLAS_NOM_001).

    Returns:
        ResumenEvaluacion con mensajes formateados.
    """
    resumen = evaluar_cumplimiento(datos, reglas)

    for r in resumen.resultados:
        r.mensaje = _formatear_mensaje(r.mensaje, datos)

    return resumen


# ==============================================================================
# UTILIDADES DE CONSULTA
# ==============================================================================

def obtener_reglas_por_categoria(
    categoria: Categoria,
    reglas: list[Regla] = REGLAS_NOM_001,
) -> list[Regla]:
    """Filtra la colección de reglas por categoría temática."""
    return [r for r in reglas if r.categoria == categoria]


def obtener_reglas_por_severidad(
    severidad: Severidad,
    reglas: list[Regla] = REGLAS_NOM_001,
) -> list[Regla]:
    """Filtra la colección de reglas por nivel de severidad."""
    return [r for r in reglas if r.severidad == severidad]


def describir_reglas(reglas: list[Regla] = REGLAS_NOM_001) -> list[dict[str, str]]:
    """
    Devuelve metadata de todas las reglas para documentación o UI de ayuda.
    No evalúa ninguna condición.

    Returns:
        Lista de dicts con nombre, descripcion, referencia, severidad, categoria.
    """
    return [
        {
            "nombre": r.nombre,
            "descripcion": r.descripcion,
            "referencia": r.referencia,
            "severidad": r.severidad.value,
            "categoria": r.categoria.value,
        }
        for r in reglas
    ]


# ==============================================================================
# EJEMPLO DE USO (ejecutar directamente: python core/reglas.py)
# ==============================================================================

if __name__ == "__main__":

    # Datos de ejemplo que representan el resultado de los cálculos de calculos.py
    datos_ejemplo = {
        # Conductores
        "caida_pct":             3.8,    # Excede 3% → ERROR
        "caida_pct_alimentador": 1.5,    # OK
        "caida_pct_total":       4.2,    # OK (< 5%)
        "itm_a":                 50.0,
        "ampacidad_conductor_a": 35.0,   # ITM > ampacidad → ERROR
        "corriente_carga_a":     30.0,
        "tipo_carga":            "General",

        # Protecciones
        "kaic_ka":               10.0,
        "icc_ka":                12.0,   # kAIC insuficiente → ERROR

        # Cargas
        "factor_demanda":        0.75,
        "alumbrado_va":          2900.0,
        "area_m2":               100.0,  # 29 VA/m² < 33 → ERROR en vivienda
        "tipo_inmueble":         "Vivienda unifamiliar",
        "especiales_va":         4500.0,
        "factor_potencia":       0.85,   # < 0.90 → ADVERTENCIA

        # Tierra
        "resistencia_tierra_ohm": 6.5,  # > 5 → ADVERTENCIA, < 25 → OK

        # Transformador
        "potencia_transformador_kva": 150.0,
        "carga_demandada_kva":        140.0,

        # General
        "voltaje_v": 220,
    }

    print("=" * 70)
    print("EVALUACIÓN NOM-001-SEDE-2012")
    print("=" * 70)

    resumen = evaluar_y_formatear(datos_ejemplo)

    print(f"\nReglas evaluadas : {resumen.total_evaluadas}")
    print(f"Cumplidas        : {resumen.total_cumplidas}")
    print(f"Errores          : {resumen.total_errores}")
    print(f"Advertencias     : {resumen.total_advertencias}")
    print(f"Cumplimiento     : {resumen.cumplimiento_pct:.1f}%")
    print(f"Aprobado         : {'✓ SÍ' if resumen.aprobado else '✗ NO'}")

    print("\n--- ERRORES CRÍTICOS ---")
    for r in resumen.errores_criticos():
        print(f"  ✗ [{r.referencia}] {r.nombre}")
        print(f"    {r.mensaje}")

    print("\n--- ADVERTENCIAS ---")
    for r in resumen.advertencias_activas():
        print(f"  ⚠ [{r.referencia}] {r.nombre}")
        print(f"    {r.mensaje}")

    print("\n--- REGLAS OMITIDAS ---")
    for r in resumen.filtrar(omitidas=True):
        if r.omitida:
            print(f"  — {r.nombre}: {r.razon_omision}")
