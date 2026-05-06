"""
core/calculos.py
================
Módulo de lógica de negocio para cálculos eléctricos basados en NOM-001-SEDE-2012.

Sin dependencias de UI. Sin efectos secundarios. Testeable de forma aislada.
Cada función recibe parámetros tipados y devuelve un dict estructurado con:
  - resultado(s) numérico(s)
  - unidad
  - cumple: bool o None si no aplica
  - articulos_citados: list[str]
  - detalle: str con el desarrollo del cálculo
  - advertencias: list[str] para condiciones límite
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Optional

# ==============================================================================
# CONSTANTES TÉCNICAS
# ==============================================================================

# Tabla 310-15(b)(16) — Ampacidad base a 75°C, conductor en conduit, aire 30°C
# Cobre THW / THHN (base 75°C)
AMPACIDADES_COBRE_75: dict[str, int] = {
    "14": 20,  "12": 25,  "10": 35,  "8": 50,
    "6": 65,   "4": 85,   "3": 100,  "2": 115,
    "1": 130,  "1/0": 150,"2/0": 175,"3/0": 200,
    "4/0": 230,"250": 255,"300": 285,"350": 310,
    "400": 335,"500": 380,"600": 420,"750": 475,
    "1000": 545,
}

# Aluminio: aprox 80% de cobre para misma temperatura
FACTOR_ALUMINIO_AMPACIDAD: float = 0.80

# Tabla 310-15(b)(2)(b) — Factores de corrección por temperatura ambiente
# Clave: temperatura límite inferior del rango, Valor: factor multiplicador (base 75°C)
FT_TEMPERATURA_75C: dict[int, float] = {
    10: 1.20, 16: 1.15, 21: 1.11, 26: 1.05, 31: 1.00,
    36: 0.94, 41: 0.88, 46: 0.82, 51: 0.75, 56: 0.67,
    61: 0.58, 66: 0.33,
}

# Tabla 310-15(b)(3)(a) — Factor de ajuste por número de conductores portadores
FA_CONDUCTORES: dict[int, float] = {
    1: 1.00, 2: 1.00, 3: 1.00, 4: 0.80, 5: 0.80,
    6: 0.80, 7: 0.70, 8: 0.70, 9: 0.70, 10: 0.50,
    20: 0.45, 30: 0.40, 40: 0.35, 41: 0.35,
}

# Tabla 9 NOM-001-SEDE-2012 — Resistencia e Impedancia por calibre
# Estructura: calibre -> conduit -> {R: ohm/km, X: ohm/km}
TABLA_9: dict[str, dict[str, dict[str, float]]] = {
    "14": {"PVC": {"R": 10.20, "X": 0.190}, "Aluminio": {"R": 10.20, "X": 0.190}, "Acero": {"R": 10.20, "X": 0.240}},
    "12": {"PVC": {"R": 6.60,  "X": 0.177}, "Aluminio": {"R": 6.60,  "X": 0.177}, "Acero": {"R": 6.60,  "X": 0.223}},
    "10": {"PVC": {"R": 3.90,  "X": 0.164}, "Aluminio": {"R": 3.90,  "X": 0.164}, "Acero": {"R": 3.90,  "X": 0.207}},
    "8":  {"PVC": {"R": 2.56,  "X": 0.171}, "Aluminio": {"R": 2.56,  "X": 0.171}, "Acero": {"R": 2.56,  "X": 0.213}},
    "6":  {"PVC": {"R": 1.61,  "X": 0.167}, "Aluminio": {"R": 1.61,  "X": 0.167}, "Acero": {"R": 1.61,  "X": 0.210}},
    "4":  {"PVC": {"R": 1.02,  "X": 0.157}, "Aluminio": {"R": 1.02,  "X": 0.157}, "Acero": {"R": 1.02,  "X": 0.197}},
    "3":  {"PVC": {"R": 0.820, "X": 0.154}, "Aluminio": {"R": 0.820, "X": 0.154}, "Acero": {"R": 0.820, "X": 0.194}},
    "2":  {"PVC": {"R": 0.620, "X": 0.148}, "Aluminio": {"R": 0.660, "X": 0.148}, "Acero": {"R": 0.660, "X": 0.187}},
    "1":  {"PVC": {"R": 0.490, "X": 0.151}, "Aluminio": {"R": 0.520, "X": 0.151}, "Acero": {"R": 0.520, "X": 0.187}},
    "1/0":{"PVC": {"R": 0.390, "X": 0.144}, "Aluminio": {"R": 0.430, "X": 0.144}, "Acero": {"R": 0.390, "X": 0.180}},
    "2/0":{"PVC": {"R": 0.330, "X": 0.141}, "Aluminio": {"R": 0.330, "X": 0.141}, "Acero": {"R": 0.330, "X": 0.177}},
    "3/0":{"PVC": {"R": 0.253, "X": 0.138}, "Aluminio": {"R": 0.269, "X": 0.138}, "Acero": {"R": 0.259, "X": 0.171}},
    "4/0":{"PVC": {"R": 0.203, "X": 0.135}, "Aluminio": {"R": 0.220, "X": 0.135}, "Acero": {"R": 0.207, "X": 0.167}},
    "250":{"PVC": {"R": 0.171, "X": 0.135}, "Aluminio": {"R": 0.187, "X": 0.135}, "Acero": {"R": 0.177, "X": 0.171}},
    "300":{"PVC": {"R": 0.144, "X": 0.135}, "Aluminio": {"R": 0.161, "X": 0.135}, "Acero": {"R": 0.148, "X": 0.167}},
    "350":{"PVC": {"R": 0.125, "X": 0.131}, "Aluminio": {"R": 0.141, "X": 0.131}, "Acero": {"R": 0.128, "X": 0.164}},
    "400":{"PVC": {"R": 0.108, "X": 0.131}, "Aluminio": {"R": 0.125, "X": 0.131}, "Acero": {"R": 0.115, "X": 0.161}},
    "500":{"PVC": {"R": 0.089, "X": 0.128}, "Aluminio": {"R": 0.105, "X": 0.128}, "Acero": {"R": 0.095, "X": 0.157}},
    "600":{"PVC": {"R": 0.075, "X": 0.128}, "Aluminio": {"R": 0.092, "X": 0.128}, "Acero": {"R": 0.082, "X": 0.157}},
    "750":{"PVC": {"R": 0.062, "X": 0.125}, "Aluminio": {"R": 0.079, "X": 0.125}, "Acero": {"R": 0.069, "X": 0.157}},
    "1000":{"PVC":{"R": 0.049, "X": 0.121}, "Aluminio": {"R": 0.062, "X": 0.121}, "Acero": {"R": 0.059, "X": 0.151}},
}

# Factor de resistencia para conductor de aluminio relativo al cobre (cuando no hay dato directo)
FACTOR_R_ALUMINIO: float = 1.62

# Calibres en orden ascendente de capacidad
CALIBRES_ORDENADOS: list[str] = [
    "14", "12", "10", "8", "6", "4", "3", "2", "1",
    "1/0", "2/0", "3/0", "4/0",
    "250", "300", "350", "400", "500", "600", "750", "1000",
]

# Valores comerciales de ITM según Art. 240-6
VALORES_ITM: list[int] = [
    15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100,
    110, 125, 150, 175, 200, 225, 250, 300, 350, 400, 450,
    500, 600, 700, 800, 1000, 1200, 1600, 2000,
]

# Capacidades interruptivas comerciales en kA
KAIC_COMERCIALES: list[int] = [10, 14, 22, 25, 35, 42, 65, 100, 150, 200]

# Factores de demanda por tipo de inmueble (referencia Art. 220)
FACTORES_DEMANDA: dict[str, float] = {
    "Vivienda unifamiliar": 0.35,
    "Departamento":         0.38,
    "Oficina":              0.75,
    "Local comercial":      0.80,
    "Industria ligera":     0.70,
    "Industria pesada":     0.85,
    "Hospital":             0.80,
    "Escuela":              0.75,
    "Almacén":              0.60,
}

# Potencias comerciales de transformadores en kVA
POTENCIAS_TRANSFORMADOR_STD: list[float] = [
    15, 30, 45, 75, 112.5, 150, 225, 300, 500,
    750, 1000, 1250, 1500, 2000, 2500,
]


# ==============================================================================
# DATACLASS DE RESULTADO
# ==============================================================================

@dataclass
class ResultadoCalculo:
    """
    Resultado estructurado de cualquier cálculo del módulo.
    Viaja de core/ → services/ → ui/ sin pérdida de información.
    """
    tipo: str                                    # identificador del cálculo
    valores: dict[str, float | str]             # resultados numéricos clave
    unidades: dict[str, str]                    # unidad de cada valor
    cumple: Optional[bool]                      # None si no hay límite normativo
    limite_normativo: Optional[str]             # descripción del límite
    articulos_citados: list[str] = field(default_factory=list)
    detalle: str = ""                           # desarrollo paso a paso
    advertencias: list[str] = field(default_factory=list)


# ==============================================================================
# FUNCIONES AUXILIARES INTERNAS
# ==============================================================================

def _validar_positivo(valor: float, nombre: str) -> None:
    """Lanza ValueError si el valor no es mayor que cero."""
    if valor <= 0:
        raise ValueError(f"'{nombre}' debe ser mayor que cero. Recibido: {valor}")


def _validar_rango(valor: float, minimo: float, maximo: float, nombre: str) -> None:
    """Lanza ValueError si el valor está fuera del rango válido."""
    if not (minimo <= valor <= maximo):
        raise ValueError(
            f"'{nombre}' debe estar entre {minimo} y {maximo}. Recibido: {valor}"
        )


def _obtener_rx(material: str, conduit: str, calibre: str) -> tuple[float, float]:
    """
    Devuelve (R, X) en Ω/km para el calibre y conduit dados.
    Para aluminio aplica FACTOR_R_ALUMINIO sobre el valor de cobre si no hay dato propio.

    Args:
        material: "cobre" | "aluminio"
        conduit:  "PVC" | "Aluminio" | "Acero"
        calibre:  AWG o kcmil como string

    Returns:
        Tupla (R, X) en Ω/km

    Raises:
        ValueError: si el calibre o conduit no existe en la Tabla 9
    """
    if calibre not in TABLA_9:
        raise ValueError(f"Calibre '{calibre}' no encontrado en Tabla 9.")
    if conduit not in TABLA_9[calibre]:
        raise ValueError(f"Conduit '{conduit}' no válido. Use: PVC, Aluminio, Acero.")

    datos = TABLA_9[calibre][conduit]
    R_base = datos["R"]
    X = datos["X"]

    if material == "aluminio":
        R = round(R_base * FACTOR_R_ALUMINIO, 4)
    elif material == "cobre":
        R = R_base
    else:
        raise ValueError(f"Material '{material}' no válido. Use: cobre, aluminio.")

    return R, X


def _factor_temperatura(temp_ambiente: float) -> float:
    """
    Devuelve el factor de corrección por temperatura para conductores a 75°C.
    Tabla 310-15(b)(2)(b).

    Args:
        temp_ambiente: temperatura ambiente en °C

    Returns:
        Factor FT (multiplicador sobre ampacidad base)
    """
    factor = 1.0
    for temp_limite in sorted(FT_TEMPERATURA_75C.keys()):
        if temp_ambiente >= temp_limite:
            factor = FT_TEMPERATURA_75C[temp_limite]
        else:
            break
    return factor


def _factor_agrupamiento(num_conductores: int) -> float:
    """
    Devuelve el factor de ajuste por agrupamiento de conductores.
    Tabla 310-15(b)(3)(a).

    Args:
        num_conductores: número de conductores portadores de corriente en la canalización

    Returns:
        Factor FA (multiplicador sobre ampacidad base)
    """
    umbrales = sorted(FA_CONDUCTORES.keys())
    factor = FA_CONDUCTORES[umbrales[-1]]
    for umbral in umbrales:
        if num_conductores <= umbral:
            factor = FA_CONDUCTORES[umbral]
            break
    return factor


def _siguiente_itm(corriente_minima: float) -> Optional[int]:
    """
    Devuelve el siguiente valor comercial de ITM ≥ corriente_minima.
    Art. 240-6.

    Returns:
        Valor en amperios o None si supera el máximo disponible.
    """
    return next((v for v in VALORES_ITM if v >= corriente_minima), None)


def _siguiente_kaic(icc_ka: float) -> int:
    """
    Devuelve la capacidad interruptiva comercial mínima ≥ icc_ka.
    Si supera todos los valores, devuelve el máximo.
    """
    return next((k for k in KAIC_COMERCIALES if k >= icc_ka), KAIC_COMERCIALES[-1])


# ==============================================================================
# 1. CAÍDA DE TENSIÓN
# ==============================================================================

def calcular_caida_tension(
    tipo_circuito: str,
    material: str,
    conduit: str,
    calibre: str,
    longitud_m: float,
    corriente_a: float,
    voltaje_v: float,
    factor_potencia: float,
    conductores_por_fase: int = 1,
) -> ResultadoCalculo:
    """
    Calcula la caída de tensión según la Tabla 9 de la NOM-001-SEDE-2012.

    Fórmula: e = k × (I / Cf) × L[km] × (R × cos φ + X × sin φ)
    Donde k = √3 para trifásico, k = 2 para monofásico.

    Args:
        tipo_circuito:       "Trifásico" | "Monofásico 2 hilos" | "Monofásico 3 hilos"
        material:            "cobre" | "aluminio"
        conduit:             "PVC" | "Aluminio" | "Acero"
        calibre:             AWG o kcmil como string (ej: "10", "1/0", "250")
        longitud_m:          Longitud del circuito en metros
        corriente_a:         Corriente de carga en amperios
        voltaje_v:           Voltaje línea-línea en voltios
        factor_potencia:     cos φ (0.01 a 1.0)
        conductores_por_fase: Número de conductores en paralelo por fase (default 1)

    Returns:
        ResultadoCalculo con caida_v, caida_pct, R, X y evaluación normativa.

    Raises:
        ValueError: si algún parámetro está fuera de rango o es inválido.
    """
    # --- Validaciones ---
    _validar_positivo(longitud_m, "longitud_m")
    _validar_positivo(corriente_a, "corriente_a")
    _validar_positivo(voltaje_v, "voltaje_v")
    _validar_rango(factor_potencia, 0.01, 1.0, "factor_potencia")
    if conductores_por_fase < 1:
        raise ValueError("'conductores_por_fase' debe ser al menos 1.")
    if tipo_circuito not in ("Trifásico", "Monofásico 2 hilos", "Monofásico 3 hilos"):
        raise ValueError(f"tipo_circuito '{tipo_circuito}' no reconocido.")

    # --- Parámetros de cálculo ---
    R, X = _obtener_rx(material, conduit, calibre)
    cos_phi = factor_potencia
    sin_phi = math.sqrt(max(0.0, 1.0 - cos_phi ** 2))
    I_conductor = corriente_a / conductores_por_fase
    L_km = longitud_m / 1000.0
    k = math.sqrt(3) if tipo_circuito == "Trifásico" else 2.0

    # --- Cálculo principal ---
    caida_v = k * I_conductor * L_km * (R * cos_phi + X * sin_phi)
    caida_pct = (caida_v / voltaje_v) * 100.0

    # --- Evaluación normativa ---
    # Art. 210-19(a)(1): ≤ 3% en circuito derivado
    # Art. 215-2(a)(3):  ≤ 5% acumulado (alimentador + circuito)
    limite_3 = caida_pct <= 3.0
    limite_5 = caida_pct <= 5.0
    cumple = limite_3

    advertencias: list[str] = []
    if not limite_3 and limite_5:
        advertencias.append(
            f"Caída ({caida_pct:.2f}%) excede el 3% del circuito derivado. "
            "Verificar que la caída acumulada (alimentador + circuito) no supere el 5%."
        )
    if not limite_5:
        advertencias.append(
            f"Caída ({caida_pct:.2f}%) excede el 5% total permitido. "
            "Aumentar calibre o reducir longitud es obligatorio."
        )

    detalle = (
        f"k={k:.4f} | I_cond={I_conductor:.3f} A | L={L_km:.4f} km\n"
        f"R={R:.4f} Ω/km | X={X:.4f} Ω/km\n"
        f"cos φ={cos_phi:.3f} | sin φ={sin_phi:.3f}\n"
        f"e = {k:.4f} × {I_conductor:.3f} × {L_km:.4f} × "
        f"({R:.4f}×{cos_phi:.3f} + {X:.4f}×{sin_phi:.3f})\n"
        f"e = {caida_v:.4f} V → {caida_pct:.3f}%"
    )

    return ResultadoCalculo(
        tipo="caida_tension",
        valores={
            "caida_v": round(caida_v, 4),
            "caida_pct": round(caida_pct, 3),
            "R_ohm_km": R,
            "X_ohm_km": X,
            "k": round(k, 4),
            "I_conductor_a": round(I_conductor, 3),
        },
        unidades={
            "caida_v": "V",
            "caida_pct": "%",
            "R_ohm_km": "Ω/km",
            "X_ohm_km": "Ω/km",
            "k": "—",
            "I_conductor_a": "A",
        },
        cumple=cumple,
        limite_normativo="≤ 3% circuito derivado | ≤ 5% total (Art. 210-19, Art. 215-2)",
        articulos_citados=["art210-19", "art215-2", "tab9"],
        detalle=detalle,
        advertencias=advertencias,
    )


# ==============================================================================
# 2. SELECCIÓN DE CALIBRE
# ==============================================================================

def seleccionar_calibre(
    corriente_carga_a: float,
    longitud_m: float,
    voltaje_v: float,
    tipo_circuito: str,
    material: str,
    conduit: str,
    temp_ambiente_c: float = 30.0,
    num_conductores_canaliz: int = 3,
    factor_potencia: float = 0.85,
    caida_max_pct: float = 3.0,
    conductores_por_fase: int = 1,
) -> ResultadoCalculo:
    """
    Selecciona el calibre mínimo que satisface simultáneamente:
    1. Ampacidad corregida ≥ corriente de carga (Tabla 310-15(b)(16))
    2. Caída de tensión ≤ caida_max_pct (Tabla 9)

    El calibre final es el mayor de los dos requerimientos.

    Args:
        corriente_carga_a:      Corriente de diseño en amperios
        longitud_m:             Longitud del circuito en metros
        voltaje_v:              Voltaje línea-línea en voltios
        tipo_circuito:          "Trifásico" | "Monofásico 2 hilos" | "Monofásico 3 hilos"
        material:               "cobre" | "aluminio"
        conduit:                "PVC" | "Aluminio" | "Acero"
        temp_ambiente_c:        Temperatura ambiente en °C (default 30)
        num_conductores_canaliz: Conductores portadores en la canalización (default 3)
        factor_potencia:        cos φ (default 0.85)
        caida_max_pct:          Límite de caída de tensión en % (default 3.0)
        conductores_por_fase:   Conductores en paralelo por fase (default 1)

    Returns:
        ResultadoCalculo con:
            calibre_ampacidad: calibre mínimo por corriente
            calibre_caida:     calibre mínimo por caída de tensión
            calibre_final:     el mayor de los dos (el que se instala)
            ampacidad_corregida: capacidad real del calibre final
            caida_pct_final:   caída real con el calibre final

    Raises:
        ValueError: si ningún calibre estándar satisface los requerimientos.
    """
    # --- Validaciones ---
    _validar_positivo(corriente_carga_a, "corriente_carga_a")
    _validar_positivo(longitud_m, "longitud_m")
    _validar_positivo(voltaje_v, "voltaje_v")
    _validar_rango(factor_potencia, 0.01, 1.0, "factor_potencia")
    _validar_rango(caida_max_pct, 0.1, 10.0, "caida_max_pct")

    FT = _factor_temperatura(temp_ambiente_c)
    FA = _factor_agrupamiento(num_conductores_canaliz)
    factor_correccion = FT * FA

    # --- Paso 1: Calibre mínimo por ampacidad ---
    ampacidades = (
        AMPACIDADES_COBRE_75
        if material == "cobre"
        else {k: int(v * FACTOR_ALUMINIO_AMPACIDAD) for k, v in AMPACIDADES_COBRE_75.items()}
    )

    corriente_requerida = corriente_carga_a / factor_correccion
    calibre_por_ampacidad: Optional[str] = None
    for cal in CALIBRES_ORDENADOS:
        if ampacidades[cal] >= corriente_requerida:
            calibre_por_ampacidad = cal
            break

    if calibre_por_ampacidad is None:
        raise ValueError(
            f"Ningún calibre estándar soporta {corriente_requerida:.1f} A "
            f"(corriente requerida con FT={FT:.2f}, FA={FA:.2f}). "
            "Considere conductores en paralelo por fase."
        )

    # --- Paso 2: Calibre mínimo por caída de tensión ---
    idx_inicio = CALIBRES_ORDENADOS.index(calibre_por_ampacidad)
    calibre_por_caida: Optional[str] = None
    caida_final_pct: float = 0.0

    for cal in CALIBRES_ORDENADOS[idx_inicio:]:
        try:
            resultado_caida = calcular_caida_tension(
                tipo_circuito=tipo_circuito,
                material=material,
                conduit=conduit,
                calibre=cal,
                longitud_m=longitud_m,
                corriente_a=corriente_carga_a,
                voltaje_v=voltaje_v,
                factor_potencia=factor_potencia,
                conductores_por_fase=conductores_por_fase,
            )
            caida_pct = resultado_caida.valores["caida_pct"]
            if caida_pct <= caida_max_pct:
                calibre_por_caida = cal
                caida_final_pct = caida_pct
                break
        except ValueError:
            continue

    if calibre_por_caida is None:
        raise ValueError(
            f"Ningún calibre estándar cumple la caída máxima de {caida_max_pct}% "
            f"para {corriente_carga_a} A en {longitud_m} m. "
            "Considere aumentar voltaje o usar conductores en paralelo."
        )

    # --- Paso 3: Calibre final (el más restrictivo) ---
    idx_amp = CALIBRES_ORDENADOS.index(calibre_por_ampacidad)
    idx_cai = CALIBRES_ORDENADOS.index(calibre_por_caida)
    calibre_final = CALIBRES_ORDENADOS[max(idx_amp, idx_cai)]

    ampacidad_base = ampacidades[calibre_final]
    ampacidad_corregida = ampacidad_base * factor_correccion

    advertencias: list[str] = []
    if calibre_por_caida != calibre_por_ampacidad:
        advertencias.append(
            f"La caída de tensión exige un calibre mayor ({calibre_por_caida}) "
            f"que el requerido por ampacidad ({calibre_por_ampacidad})."
        )
    if FT < 1.0:
        advertencias.append(
            f"Factor temperatura {FT:.2f} aplicado para {temp_ambiente_c}°C. "
            "Ampacidad reducida respecto a tabla base."
        )
    if FA < 1.0:
        advertencias.append(
            f"Factor agrupamiento {FA:.2f} aplicado para {num_conductores_canaliz} "
            "conductores en canalización."
        )

    detalle = (
        f"FT (temp {temp_ambiente_c}°C) = {FT:.2f} | "
        f"FA ({num_conductores_canaliz} cond.) = {FA:.2f}\n"
        f"Corriente requerida = {corriente_carga_a:.1f} / {factor_correccion:.2f} "
        f"= {corriente_requerida:.1f} A\n"
        f"Calibre por ampacidad: {calibre_por_ampacidad} "
        f"({ampacidades[calibre_por_ampacidad]} A base)\n"
        f"Calibre por caída ({caida_max_pct}%): {calibre_por_caida} "
        f"(caída = {caida_final_pct:.2f}%)\n"
        f"Calibre final instalado: {calibre_final} "
        f"(ampacidad corregida = {ampacidad_corregida:.1f} A)"
    )

    return ResultadoCalculo(
        tipo="seleccion_calibre",
        valores={
            "calibre_ampacidad": calibre_por_ampacidad,
            "calibre_caida": calibre_por_caida,
            "calibre_final": calibre_final,
            "ampacidad_base_a": float(ampacidad_base),
            "ampacidad_corregida_a": round(ampacidad_corregida, 2),
            "FT": FT,
            "FA": FA,
            "corriente_requerida_a": round(corriente_requerida, 2),
            "caida_pct_final": round(caida_final_pct, 3),
        },
        unidades={
            "calibre_final": "AWG/kcmil",
            "ampacidad_corregida_a": "A",
            "corriente_requerida_a": "A",
            "caida_pct_final": "%",
            "FT": "—",
            "FA": "—",
        },
        cumple=True,
        limite_normativo=(
            f"Ampacidad ≥ corriente de carga | Caída ≤ {caida_max_pct}% "
            "(Art. 310, Tabla 310-15(b)(16), Art. 210-19)"
        ),
        articulos_citados=["art310", "tab310-15b16", "tab310-15b2b", "tab310-15b3a", "art210-19"],
        detalle=detalle,
        advertencias=advertencias,
    )


# ==============================================================================
# 3. CÁLCULO DE CARGAS
# ==============================================================================

def calcular_cargas(
    tipo_inmueble: str,
    area_m2: float,
    carga_calefaccion_w: float = 0.0,
    carga_agua_w: float = 0.0,
    carga_estufa_w: float = 0.0,
    carga_motores_w: float = 0.0,
    carga_aire_w: float = 0.0,
    carga_otros_w: float = 0.0,
    voltaje_v: float = 220.0,
    factor_potencia: float = 0.90,
    factor_demanda_override: Optional[float] = None,
) -> ResultadoCalculo:
    """
    Calcula la carga total y demanda máxima según Art. 220 de la NOM-001-SEDE-2012.

    Proceso:
      1. Alumbrado: área × 33 VA/m² (Art. 220-12)
      2. Contactos: estimación por área, 180 VA/salida (Art. 220-14)
      3. Circuitos especiales vivienda: 2 × 1500 VA + 1500 VA lavandería (Art. 220-52)
      4. Cargas específicas (equipos fijos) a plena carga
      5. Demanda = carga_total × factor_demanda (Art. 220-42, 220-54, 220-55)
      6. Corriente estimada = demanda_va / (voltaje × fp)

    Args:
        tipo_inmueble:          Clave de FACTORES_DEMANDA (ej: "Vivienda unifamiliar")
        area_m2:                Superficie construida en m²
        carga_calefaccion_w:    Calefacción / HVAC en W
        carga_agua_w:           Calentador de agua en W
        carga_estufa_w:         Estufa/horno en W
        carga_motores_w:        Motores (suma total) en W
        carga_aire_w:           Aire acondicionado en W
        carga_otros_w:          Otros equipos especiales en W
        voltaje_v:              Voltaje para estimación de corriente (default 220 V)
        factor_potencia:        cos φ para conversión VA → A (default 0.90)
        factor_demanda_override: Si se provee, sobreescribe el factor de FACTORES_DEMANDA

    Returns:
        ResultadoCalculo con desglose completo de cargas y corriente estimada.

    Raises:
        ValueError: si tipo_inmueble no está registrado y no se provee override.
    """
    # --- Validaciones ---
    _validar_positivo(area_m2, "area_m2")
    _validar_positivo(voltaje_v, "voltaje_v")
    _validar_rango(factor_potencia, 0.01, 1.0, "factor_potencia")

    es_vivienda = tipo_inmueble in ("Vivienda unifamiliar", "Departamento")

    if factor_demanda_override is not None:
        _validar_rango(factor_demanda_override, 0.01, 1.0, "factor_demanda_override")
        fd = factor_demanda_override
    elif tipo_inmueble in FACTORES_DEMANDA:
        fd = FACTORES_DEMANDA[tipo_inmueble]
    else:
        raise ValueError(
            f"tipo_inmueble '{tipo_inmueble}' no registrado. "
            f"Use factor_demanda_override o uno de: {list(FACTORES_DEMANDA.keys())}"
        )

    # --- Cálculo de cargas base ---
    # Art. 220-12: 33 VA/m² para viviendas, locales generales
    alumbrado_va = area_m2 * 33.0

    # Art. 220-14: 180 VA por salida. Estimación: 1 salida cada 30 m²
    num_contactos = max(2, int(area_m2 / 30))
    contactos_va = num_contactos * 180.0

    # Art. 220-52: circuitos especiales solo para viviendas
    # 2 circuitos pequeños aparatos × 1500 VA + 1 circuito lavandería × 1500 VA
    especiales_va = 4500.0 if es_vivienda else 0.0

    # Cargas fijas a plena potencia (sin factor de demanda individual)
    cargas_fijas_w = (
        carga_calefaccion_w
        + carga_agua_w
        + carga_estufa_w
        + carga_motores_w
        + carga_aire_w
        + carga_otros_w
    )

    # Para motores: 125% del motor mayor + 100% demás (simplificado: se aplica 125% al total)
    # El usuario debe pasar la carga correcta si hay motores identificados individualmente
    carga_total_va = alumbrado_va + contactos_va + especiales_va + cargas_fijas_w

    # --- Demanda máxima ---
    demanda_va = carga_total_va * fd
    demanda_kva = demanda_va / 1000.0

    # --- Corriente estimada ---
    corriente_estimada_a = demanda_va / (voltaje_v * factor_potencia)

    advertencias: list[str] = []
    if carga_motores_w > 0:
        advertencias.append(
            "Para motores: verificar Art. 430 — aplicar 125% al motor de mayor potencia "
            "y 100% a los demás. El cálculo actual suma el total sin distinción."
        )
    if not es_vivienda and especiales_va == 0:
        advertencias.append(
            "Circuitos especiales de vivienda no aplicados. "
            "Verificar si el inmueble requiere circuitos dedicados adicionales (Art. 220-52)."
        )

    detalle = (
        f"Tipo: {tipo_inmueble} | Área: {area_m2} m²\n"
        f"Alumbrado (33 VA/m²): {alumbrado_va:,.1f} VA\n"
        f"Contactos ({num_contactos} × 180 VA): {contactos_va:,.1f} VA\n"
        f"Circuitos especiales vivienda: {especiales_va:,.1f} VA\n"
        f"Cargas fijas: {cargas_fijas_w:,.1f} W\n"
        f"Carga total sin FD: {carga_total_va:,.1f} VA\n"
        f"Factor de demanda ({tipo_inmueble}): {fd*100:.0f}%\n"
        f"Demanda máxima: {demanda_va:,.1f} VA = {demanda_kva:.2f} kVA\n"
        f"Corriente estimada ({voltaje_v}V, FP={factor_potencia}): {corriente_estimada_a:.1f} A"
    )

    return ResultadoCalculo(
        tipo="calculo_cargas",
        valores={
            "alumbrado_va": round(alumbrado_va, 1),
            "contactos_va": round(contactos_va, 1),
            "especiales_va": especiales_va,
            "cargas_fijas_w": round(cargas_fijas_w, 1),
            "carga_total_va": round(carga_total_va, 1),
            "factor_demanda": fd,
            "demanda_va": round(demanda_va, 1),
            "demanda_kva": round(demanda_kva, 3),
            "corriente_estimada_a": round(corriente_estimada_a, 2),
            "num_contactos": float(num_contactos),
        },
        unidades={
            "alumbrado_va": "VA",
            "contactos_va": "VA",
            "especiales_va": "VA",
            "cargas_fijas_w": "W",
            "carga_total_va": "VA",
            "factor_demanda": "—",
            "demanda_va": "VA",
            "demanda_kva": "kVA",
            "corriente_estimada_a": "A",
            "num_contactos": "uds",
        },
        cumple=None,
        limite_normativo=None,
        articulos_citados=["art220", "art220-12", "art220-14", "art220-52",
                           "tab220-42", "tab220-54", "tab220-55"],
        detalle=detalle,
        advertencias=advertencias,
    )


# ==============================================================================
# 4. SELECCIÓN DE PROTECCIONES
# ==============================================================================

def seleccionar_proteccion(
    tipo_carga: str,
    corriente_carga_a: float,
    icc_disponible_ka: float,
    ampacidad_conductor_a: Optional[float] = None,
) -> ResultadoCalculo:
    """
    Selecciona el interruptor termomagnético (ITM) según Art. 240 y Art. 430.

    Criterios de selección:
      - Cargas generales continuas: In ≤ 1.25 × Ic (Art. 210-20, 215-3)
      - Motores:                    In ≤ 1.5 × Im  (Art. 430-52, Tabla 430-52)
      - Transformadores:            Coordinación según Art. 450-3

    También verifica coordinación con el conductor si se provee su ampacidad.

    Args:
        tipo_carga:             "General" | "Motor" | "Transformador"
        corriente_carga_a:      Corriente nominal de la carga en amperios
        icc_disponible_ka:      Corriente de cortocircuito disponible en kA
        ampacidad_conductor_a:  Ampacidad corregida del conductor (opcional).
                                Si se provee, verifica que In ≤ ampacidad_conductor.

    Returns:
        ResultadoCalculo con itm_a, kaic_ka y verificación de coordinación.

    Raises:
        ValueError: si tipo_carga no es válido o corrientes son inválidas.
    """
    _validar_positivo(corriente_carga_a, "corriente_carga_a")
    _validar_positivo(icc_disponible_ka, "icc_disponible_ka")

    tipos_validos = ("General", "Motor", "Transformador")
    if tipo_carga not in tipos_validos:
        raise ValueError(f"tipo_carga '{tipo_carga}' no válido. Use: {tipos_validos}")

    # --- Factor multiplicador según tipo ---
    if tipo_carga == "Motor":
        factor = 1.5
        criterio = "In ≤ 1.5 × Im (Art. 430-52, Tabla 430-52)"
        arts = ["art430-31", "art430-52", "art240-6"]
    elif tipo_carga == "Transformador":
        factor = 1.25
        criterio = "Protección primaria: In ≤ 1.25 × I_prim (Art. 450-3)"
        arts = ["art450-3", "art240", "art240-6"]
    else:
        factor = 1.25
        criterio = "In ≤ 1.25 × Ic para cargas continuas (Art. 210-20, 215-3)"
        arts = ["art240", "art240-6", "art210-19"]

    corriente_minima = corriente_carga_a * factor
    itm_a = _siguiente_itm(corriente_minima)
    kaic_ka = _siguiente_kaic(icc_disponible_ka)

    if itm_a is None:
        raise ValueError(
            f"No existe ITM estándar para {corriente_minima:.1f} A. "
            "Consulte soluciones con múltiples interruptores en paralelo."
        )

    advertencias: list[str] = []

    # Verificación de coordinación con el conductor
    coordinacion_ok: Optional[bool] = None
    if ampacidad_conductor_a is not None:
        _validar_positivo(ampacidad_conductor_a, "ampacidad_conductor_a")
        coordinacion_ok = itm_a <= ampacidad_conductor_a
        if not coordinacion_ok:
            advertencias.append(
                f"El ITM seleccionado ({itm_a} A) supera la ampacidad del conductor "
                f"({ampacidad_conductor_a:.1f} A). Aumentar calibre del conductor "
                "o reducir el ITM. Art. 240-4."
            )
            arts.append("art240")

    detalle = (
        f"Tipo de carga: {tipo_carga}\n"
        f"Corriente de carga: {corriente_carga_a:.1f} A\n"
        f"Factor multiplicador: {factor}\n"
        f"Corriente mínima ITM: {corriente_carga_a:.1f} × {factor} = {corriente_minima:.1f} A\n"
        f"ITM seleccionado: {itm_a} A (siguiente valor comercial ≥ {corriente_minima:.1f} A)\n"
        f"kAIC requerido: {icc_disponible_ka:.1f} kA → seleccionado: {kaic_ka} kA\n"
        f"Criterio: {criterio}"
    )
    if ampacidad_conductor_a:
        detalle += f"\nCoordinación con conductor ({ampacidad_conductor_a:.1f} A): "
        detalle += "✓ OK" if coordinacion_ok else "✗ FALLA — revisar"

    return ResultadoCalculo(
        tipo="seleccion_proteccion",
        valores={
            "itm_a": float(itm_a),
            "kaic_ka": float(kaic_ka),
            "factor_multiplicador": factor,
            "corriente_minima_itm_a": round(corriente_minima, 2),
            "coordinacion_conductor": float(coordinacion_ok) if coordinacion_ok is not None else -1.0,
        },
        unidades={
            "itm_a": "A",
            "kaic_ka": "kA",
            "corriente_minima_itm_a": "A",
        },
        cumple=coordinacion_ok if coordinacion_ok is not None else True,
        limite_normativo=criterio,
        articulos_citados=arts,
        detalle=detalle,
        advertencias=advertencias,
    )


# ==============================================================================
# 5. DIMENSIONAMIENTO DE TRANSFORMADOR
# ==============================================================================

def dimensionar_transformador(
    carga_demandada_kva: float,
    voltaje_primario_v: float,
    voltaje_secundario_v: float,
    sistema: str,
    factor_crecimiento: float = 0.20,
) -> ResultadoCalculo:
    """
    Dimensiona el transformador y calcula corrientes nominales de primario y secundario.

    Selección de potencia comercial: siguiente estándar ≥ carga_demandada × (1 + factor_crecimiento).

    Args:
        carga_demandada_kva:  Carga demandada total en kVA
        voltaje_primario_v:   Tensión del lado de alta (V)
        voltaje_secundario_v: Tensión del lado de baja (V)
        sistema:              "Trifásico" | "Monofásico"
        factor_crecimiento:   Margen de reserva (default 0.20 = 20%)

    Returns:
        ResultadoCalculo con potencia seleccionada, corrientes y protecciones.

    Raises:
        ValueError: si la carga supera la mayor potencia estándar disponible.
    """
    _validar_positivo(carga_demandada_kva, "carga_demandada_kva")
    _validar_positivo(voltaje_primario_v, "voltaje_primario_v")
    _validar_positivo(voltaje_secundario_v, "voltaje_secundario_v")
    _validar_rango(factor_crecimiento, 0.0, 2.0, "factor_crecimiento")

    if sistema not in ("Trifásico", "Monofásico"):
        raise ValueError(f"sistema '{sistema}' no válido. Use: Trifásico, Monofásico.")

    carga_con_reserva = carga_demandada_kva * (1.0 + factor_crecimiento)
    potencia_std = next(
        (p for p in POTENCIAS_TRANSFORMADOR_STD if p >= carga_con_reserva), None
    )

    if potencia_std is None:
        raise ValueError(
            f"La carga requerida ({carga_con_reserva:.1f} kVA) supera la mayor potencia "
            f"estándar ({POTENCIAS_TRANSFORMADOR_STD[-1]} kVA). "
            "Considere dos transformadores en paralelo."
        )

    sqrt3 = math.sqrt(3)
    if sistema == "Trifásico":
        I_prim = (potencia_std * 1000.0) / (sqrt3 * voltaje_primario_v)
        I_sec = (potencia_std * 1000.0) / (sqrt3 * voltaje_secundario_v)
    else:
        I_prim = (potencia_std * 1000.0) / voltaje_primario_v
        I_sec = (potencia_std * 1000.0) / voltaje_secundario_v

    # Protección primaria máxima: Art. 450-3 — no mayor al 125% de I_prim para ≥ 9A
    prot_primaria_max = I_prim * 1.25
    itm_primario = _siguiente_itm(prot_primaria_max)

    advertencias: list[str] = []
    if potencia_std > carga_con_reserva * 1.5:
        advertencias.append(
            f"El transformador seleccionado ({potencia_std} kVA) supera en más del 50% "
            f"la carga requerida ({carga_con_reserva:.1f} kVA). "
            "Verificar si es el tamaño estándar inmediatamente superior disponible."
        )

    detalle = (
        f"Carga demandada: {carga_demandada_kva:.1f} kVA\n"
        f"Factor de crecimiento: {factor_crecimiento*100:.0f}%\n"
        f"Carga con reserva: {carga_con_reserva:.1f} kVA\n"
        f"Potencia comercial seleccionada: {potencia_std} kVA\n"
        f"Sistema: {sistema}\n"
        f"Corriente primario ({voltaje_primario_v} V): {I_prim:.2f} A\n"
        f"Corriente secundario ({voltaje_secundario_v} V): {I_sec:.2f} A\n"
        f"Protección primaria máxima (125%): {prot_primaria_max:.1f} A → ITM: {itm_primario} A"
    )

    return ResultadoCalculo(
        tipo="transformador",
        valores={
            "potencia_kva": potencia_std,
            "carga_con_reserva_kva": round(carga_con_reserva, 2),
            "I_primario_a": round(I_prim, 2),
            "I_secundario_a": round(I_sec, 2),
            "prot_primaria_max_a": round(prot_primaria_max, 2),
            "itm_primario_a": float(itm_primario) if itm_primario else 0.0,
        },
        unidades={
            "potencia_kva": "kVA",
            "carga_con_reserva_kva": "kVA",
            "I_primario_a": "A",
            "I_secundario_a": "A",
            "prot_primaria_max_a": "A",
            "itm_primario_a": "A",
        },
        cumple=True,
        limite_normativo="Art. 450 — Transformadores | Art. 450-3 — Protección primaria",
        articulos_citados=["art450", "art450-3", "art240", "art240-6"],
        detalle=detalle,
        advertencias=advertencias,
    )


# ==============================================================================
# 6. PUESTA A TIERRA
# ==============================================================================

def calcular_puesta_tierra(
    voltaje_linea_neutro_v: float,
    resistencia_tierra_ohm: float,
    material_conductor: str,
    corriente_alimentador_a: Optional[float] = None,
) -> ResultadoCalculo:
    """
    Evalúa el sistema de puesta a tierra y determina el calibre mínimo del
    conductor de tierra según Tabla 250-122 y Tabla 250-66.

    Args:
        voltaje_linea_neutro_v:   Voltaje fase-neutro en V (ej: 127 V para 220V trifásico)
        resistencia_tierra_ohm:   Resistencia medida del sistema de tierra en Ω
        material_conductor:       "Cobre" | "Aluminio"
        corriente_alimentador_a:  Corriente del alimentador en A (para Tabla 250-122).
                                  Si no se provee, se usa la corriente de falla estimada.

    Returns:
        ResultadoCalculo con corriente de falla, evaluación de resistencia y calibre.

    Raises:
        ValueError: si resistencia es cero o material no válido.
    """
    _validar_positivo(voltaje_linea_neutro_v, "voltaje_linea_neutro_v")
    _validar_positivo(resistencia_tierra_ohm, "resistencia_tierra_ohm")

    if material_conductor not in ("Cobre", "Aluminio"):
        raise ValueError(f"material_conductor '{material_conductor}' no válido. Use: Cobre, Aluminio.")

    # Corriente de falla estimada: V / R_tierra
    I_falla = voltaje_linea_neutro_v / resistencia_tierra_ohm

    # Referencia Tabla 250-122 — calibre de conductor de tierra por corriente del alimentador
    # Simplificado: se usa la corriente de falla estimada como referencia
    corriente_ref = corriente_alimentador_a if corriente_alimentador_a else I_falla

    # Tabla 250-122 simplificada (cobre)
    TABLA_250_122_COBRE: list[tuple[float, str]] = [
        (15,   "14 AWG (2.08 mm²)"),
        (20,   "12 AWG (3.31 mm²)"),
        (60,   "10 AWG (5.26 mm²)"),
        (100,  "8 AWG (8.37 mm²)"),
        (200,  "6 AWG (13.3 mm²)"),
        (300,  "4 AWG (21.2 mm²)"),
        (400,  "3 AWG (26.7 mm²)"),
        (500,  "2 AWG (33.6 mm²)"),
        (600,  "1 AWG (42.4 mm²)"),
        (800,  "1/0 AWG (53.5 mm²)"),
        (1000, "2/0 AWG (67.4 mm²)"),
        (1200, "3/0 AWG (85.0 mm²)"),
        (1600, "4/0 AWG (107 mm²)"),
        (2000, "250 kcmil (127 mm²)"),
        (float("inf"), "300 kcmil o mayor"),
    ]

    # Para aluminio: dos calibres más arriba aprox.
    TABLA_250_122_ALUM: list[tuple[float, str]] = [
        (15,   "12 AWG (3.31 mm²)"),
        (20,   "10 AWG (5.26 mm²)"),
        (60,   "8 AWG (8.37 mm²)"),
        (100,  "6 AWG (13.3 mm²)"),
        (200,  "4 AWG (21.2 mm²)"),
        (300,  "2 AWG (33.6 mm²)"),
        (400,  "1 AWG (42.4 mm²)"),
        (500,  "1/0 AWG (53.5 mm²)"),
        (600,  "2/0 AWG (67.4 mm²)"),
        (800,  "3/0 AWG (85.0 mm²)"),
        (1000, "4/0 AWG (107 mm²)"),
        (1200, "250 kcmil (127 mm²)"),
        (float("inf"), "350 kcmil o mayor"),
    ]

    tabla = TABLA_250_122_COBRE if material_conductor == "Cobre" else TABLA_250_122_ALUM
    calibre_tierra = next(cal for lim, cal in tabla if corriente_ref <= lim)

    # Evaluación normativa
    # Art. 250: ≤ 25 Ω máximo absoluto, ≤ 5 Ω recomendado
    cumple_recomendado = resistencia_tierra_ohm <= 5.0
    cumple_normativo = resistencia_tierra_ohm <= 25.0

    advertencias: list[str] = []
    if not cumple_recomendado and cumple_normativo:
        advertencias.append(
            f"Resistencia ({resistencia_tierra_ohm} Ω) supera el valor recomendado (5 Ω). "
            "Instalar electrodos adicionales en paralelo. Art. 250-52."
        )
    if not cumple_normativo:
        advertencias.append(
            f"Resistencia ({resistencia_tierra_ohm} Ω) SUPERA el máximo normativo (25 Ω). "
            "Sistema fuera de norma. Art. 250."
        )

    detalle = (
        f"Voltaje línea-neutro: {voltaje_linea_neutro_v} V\n"
        f"Resistencia de tierra: {resistencia_tierra_ohm} Ω\n"
        f"Corriente de falla estimada: {voltaje_linea_neutro_v} / {resistencia_tierra_ohm} "
        f"= {I_falla:.1f} A\n"
        f"Corriente de referencia para calibre: {corriente_ref:.1f} A\n"
        f"Material: {material_conductor}\n"
        f"Calibre mínimo conductor de tierra: {calibre_tierra}\n"
        f"Resistencia ≤ 5 Ω (recomendado): {'✓' if cumple_recomendado else '✗'}\n"
        f"Resistencia ≤ 25 Ω (normativo): {'✓' if cumple_normativo else '✗'}"
    )

    return ResultadoCalculo(
        tipo="puesta_tierra",
        valores={
            "I_falla_a": round(I_falla, 2),
            "resistencia_ohm": resistencia_tierra_ohm,
            "calibre_tierra": calibre_tierra,
            "cumple_recomendado": float(cumple_recomendado),
            "cumple_normativo": float(cumple_normativo),
        },
        unidades={
            "I_falla_a": "A",
            "resistencia_ohm": "Ω",
            "calibre_tierra": "AWG/kcmil",
        },
        cumple=cumple_normativo,
        limite_normativo="≤ 5 Ω recomendado | ≤ 25 Ω máximo (Art. 250, Art. 250-50, Art. 250-52)",
        articulos_citados=["art250", "art250-50", "art250-52", "tabla250-66", "tab250-1133"],
        detalle=detalle,
        advertencias=advertencias,
    )
