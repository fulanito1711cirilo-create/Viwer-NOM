"""
app.py
======
Capa de presentación de NOM Viewer — Asistente Técnico NOM-001-SEDE-2012.

Responsabilidad exclusiva:
  - Capturar inputs del usuario
  - Llamar funciones de core/ y services/
  - Presentar ResultadoCalculo y ResumenEvaluacion
  - Gestionar navegación y estado de sesión
  - Acumular y exportar resultados por elemento eléctrico

No contiene: fórmulas, validaciones técnicas, reglas normativas, lógica de negocio.
"""

import streamlit as st
import re
from collections import defaultdict

# Importaciones de core/calculos (sin las constantes que no existen)
from core.calculos import (
    calcular_caida_tension,
    calcular_cargas,
    calcular_puesta_tierra,
    dimensionar_transformador,
    seleccionar_calibre,
    seleccionar_proteccion,
    ResultadoCalculo,
    CALIBRES_ORDENADOS,
    FACTORES_DEMANDA,
)
from core.reglas import (
    Categoria,
    Severidad,
    evaluar_y_formatear,
    REGLAS_NOM_001,
)
from services.pdf_service import (
    PDFService,
    ArticuloNoEncontradoError,
    ArchivoInvalidoError,
    PDFNoCaregadoError as PDFNoCargadoError,
)

# -----------------------------------------------------------------------------
# Constantes locales
# -----------------------------------------------------------------------------
CAIDA_TENSION_MAX_PCT = 3.0
RESISTENCIA_TIERRA_MAX_OHM = 5.0

# -----------------------------------------------------------------------------
# MAPA COMPLETO (fallback si no existe el módulo config)
# -----------------------------------------------------------------------------
try:
    from config.normas.nom_001_sede_2012 import MAPA
except ImportError:
    MAPA: dict[str, int] =  {
    "art110": 27,
    "art200": 42,
    "art210": 45,
    "art215": 60,
    "art220": 63,
    "art220-10": 78,
    "art225": 76,
    "art230": 85,
    "art240": 99,
    "art250": 85,
    "art280": 159,
    "art285": 161,
    "art300": 164,
    "art310": 180,
    "art312": 217,
    "art314": 222,
    "art320": 233,
    "art322": 236,
    "art324": 237,
    "art326": 240,
    "art328": 242,
    "art330": 242,
    "art332": 245,
    "art334": 247,
    "art336": 251,
    "art338": 252,
    "art340": 213,
    "art342": 255,
    "art344": 257,
    "art348": 260,
    "art350": 262,
    "art352": 264,
    "art353": 267,
    "art354": 269,
    "art355": 264,
    "art356": 275,
    "art358": 277,
    "art360": 279,
    "art362": 281,
    "art364": 283,
    "art366": 285,
    "art368": 288,
    "art370": 292,
    "art372": 293,
    "art374": 295,
    "art376": 296,
    "art378": 298,
    "art380": 300,
    "art382": 301,
    "art384": 303,
    "art386": 305,
    "art388": 306,
    "art390": 308,
    "art392": 309,
    "art394": 319,
    "art396": 320,
    "art398": 322,
    "art399": 325,
    "art400": 327,
    "art402": 338,
    "art404": 341,
    "art406": 347,
    "art408": 352,
    "art409": 357,
    "art410": 360,
    "art411": 374,
    "art422": 375,
    "art424": 382,
    "art426": 394,
    "art427": 398,
    "art430": 402,
    "art440": 443,
    "art445": 452,
    "art450": 454,
    "art455": 464,
    "art460": 466,
    "art470": 469,
    "art480": 470,
    "art490": 471,
    "art500": 480,
    "art501": 490,
    "art502": 504,
    "art503": 511,
    "art504": 515,
    "art505": 520,
    "art506": 539,
    "art510": 548,
    "art511": 548,
    "art513": 552,
    "art514": 555,
    "art515": 560,
    "art516": 566,
    "art517": 575,
    "art518": 605,
    "art520": 608,
    "art522": 620,
    "art525": 622,
    "art530": 625,
    "art540": 631,
    "art545": 632,
    "art547": 634,
    "art550": 637,
    "art551": 651,
    "art552": 668,
    "art553": 681,
    "art555": 682,
    "art590": 688,
    "art600": 697,
    "art604": 700,
    "art605": 702,
    "art610": 703,
    "art620": 711,
    "art625": 551,
    "art626": 730,
    "art630": 736,
    "art640": 740,
    "art645": 746,
    "art647": 751,
    "art650": 753,
    "art660": 754,
    "art665": 756,
    "art668": 760,
    "art669": 762,
    "art670": 763,
    "art675": 764,
    "art680": 768,
    "art682": 789,
    "art685": 791,
    "art690": 792,
    "art692": 812,
    "art694": 815,
    "art695": 824,
    "art700": 597,
    "art701": 840,
    "art702": 728,
    "art705": 846,
    "art720": 852,
    "art725": 853,
    "art727": 865,
    "art760": 869,
    "art770": 753,
    "art800": 891,
    "art810": 907,
    "art820": 912,
    "art830": 924,
    "art840": 939,
    "art920": 944,
    "art921": 944,
    "art922": 952,
    "art923": 979,
    "art924": 994,
    "tab1": 6,
    "tab10": 7,
    "tab110-26a1": 32,
    "tab110-28": 34,
    "tab110-31": 35,
    "tab110-34a": 38,
    "tab110-34e": 38,
    "tab11a": 7,
    "tab11b": 7,
    "tab12a": 7,
    "tab12b": 7,
    "tab2": 6,
    "tab210-2": 45,
    "tab210-21": 347,
    "tab210-21b2": 347,
    "tab210-21b3": 54,
    "tab210-24": 54,
    "tab220-102": 76,
    "tab220-103": 76,
    "tab220-12": 65,
    "tab220-3": 64,
    "tab220-42": 67,
    "tab220-44": 68,
    "tab220-55": 69,
    "tab220-56": 70,
    "tab220-84": 74,
    "tab220-86": 75,
    "tab220-88": 75,
    "tab225-3": 77,
    "tab225-60": 83,
    "tab225-61": 84,
    "tab230-51c": 91,
    "tab240-3": 100,
    "tab240-4g": 102,
    "tab240-92b": 113,
    "tab250-122": 150,
    "tab250-3": 117,
    "tab250-66": 126,
    "tab3": 1138,
    "tab300-16c": 164,
    "tab300-19a": 175,
    "tab300-5": 168,
    "tab300-50": 179,
    "tab310-104": 214,
    "tab310-104a": 164,
    "tab310-104c": 214,
    "tab310-104d": 214,
    "tab310-104e": 215,
    "tab310-106": 215,
    "tab310-15b16": 189,
    "tab310-15b17": 190,
    "tab310-15b18": 191,
    "tab310-15b19": 191,
    "tab310-15b20": 192,
    "tab310-15b21": 192,
    "tab310-15b2a": 185,
    "tab310-15b2b": 185,
    "tab310-15b3a": 186,
    "tab310-15b3c": 187,
    "tab310-15b7": 187,
    "tab310-60c4": 196,
    "tab310-60c67": 196,
    "tab310-60c68": 197,
    "tab310-60c69": 197,
    "tab310-60c70": 198,
    "tab310-60c72": 199,
    "tab310-60c73": 199,
    "tab310-60c74": 200,
    "tab310-60c75": 200,
    "tab310-60c76": 201,
    "tab310-60c77": 202,
    "tab310-60c78": 203,
    "tab310-60c79": 204,
    "tab310-60c80": 205,
    "tab310-60c81": 206,
    "tab310-60c82": 207,
    "tab310-60c83": 208,
    "tab310-60c84": 209,
    "tab310-60c85": 210,
    "tab310-60c86": 211,
    "tab312-6": 219,
    "tab314-16a": 223,
    "tab314-16b": 224,
    "tab326-112": 241,
    "tab326-116": 241,
    "tab326-24": 240,
    "tab326-80": 241,
    "tab344-30": 259,
    "tab348-22": 261,
    "tab352-30": 266,
    "tab352-44": 266,
    "tab354-24": 270,
    "tab355-30": 273,
    "tab355-44": 274,
    "tab360-24a": 280,
    "tab360-24b": 280,
    "tab384-22": 304,
    "tab392-10": 310,
    "tab392-22": 315,
    "tab392-22a": 312,
    "tab392-22a5": 314,
    "tab392-22a6": 314,
    "tab392-60": 316,
    "tab396-10a": 321,
    "tab4": 7,
    "tab400-4": 328,
    "tab400-5a1": 334,
    "tab400-5a2": 334,
    "tab400-5a3": 335,
    "tab402-3": 338,
    "tab402-5": 340,
    "tab408-5": 354,
    "tab409-3": 358,
    "tab430-10": 408,
    "tab430-10b": 408,
    "tab430-12": 409,
    "tab430-12c1": 411,
    "tab430-12c2": 411,
    "tab430-22": 412,
    "tab430-22e": 414,
    "tab430-23c": 414,
    "tab430-247": 440,
    "tab430-248": 440,
    "tab430-249": 441,
    "tab430-250": 441,
    "tab430-251a": 442,
    "tab430-251b": 442,
    "tab430-29": 415,
    "tab430-37": 419,
    "tab430-5": 404,
    "tab430-52": 421,
    "tab430-7": 406,
    "tab430-72": 426,
    "tab430-7b": 406,
    "tab430-97": 431,
    "tab440-3d": 444,
    "tab450-3a": 455,
    "tab450-3b": 456,
    "tab490-24": 475,
    "tab5": 7,
    "tab500-8c": 489,
    "tab500-8d2": 490,
    "tab504-10": 517,
    "tab505-7": 525,
    "tab505-9": 529,
    "tab505-9c": 526,
    "tab505-9c24": 528,
    "tab505-9d1": 529,
    "tab506-9c23": 544,
    "tab514-3b1": 556,
    "tab514-3b2": 558,
    "tab515-2": 1034,
    "tab515-3": 561,
    "tab520-44": 613,
    "tab522-22": 622,
    "tab530-19a": 629,
    "tab550-31": 649,
    "tab551-73a": 666,
    "tab552-10e1": 670,
    "tab555-12": 684,
    "tab610-14a": 705,
    "tab610-14b": 706,
    "tab610-14d": 706,
    "tab610-14e": 707,
    "tab620-14": 715,
    "tab625-29d1": 729,
    "tab625-29d2": 729,
    "tab630-11a": 737,
    "tab630-31a2": 738,
    "tab645-5": 749,
    "tab680-10": 771,
    "tab680-3": 769,
    "tab680-8": 770,
    "tab685-3": 791,
    "tab690-31c": 804,
    "tab690-7": 798,
    "tab705-3": 846,
    "tab725-154g": 863,
    "tab725-179": 865,
    "tab760-154d": 876,
    "tab760-179i": 878,
    "tab770-154a": 887,
    "tab770-154b": 888,
    "tab770-179": 889,
    "tab8": 7,
    "tab800-154a": 903,
    "tab800-154b": 903,
    "tab800-179": 906,
    "tab810-16a": 908,
    "tab810-52": 911,
    "tab820-154a": 923,
    "tab820-154b": 922,
    "tab820-179": 923,
    "tab830-15": 925,
    "tab830-154a": 937,
    "tab830-154b": 937,
    "tab830-47": 929,
    "tab9": 1010,
    "tab921-25": 951,
    "tab922-10": 956,
    "tab922-12a1": 958,
    "tab922-12a2": 958,
    "tab922-13a": 959,
    "tab922-15a": 960,
    "tab922-19e": 962,
    "tab922-21": 964,
    "tab922-22a": 965,
    "tab922-31e2": 966,
    "tab922-33": 967,
    "tab922-41": 968,
    "tab922-43": 968,
    "tab922-54": 970,
    "tab922-55": 971,
    "tab922-83": 974,
    "tab922-84": 974,
    "tab922-84a": 975,
    "tab922-93": 976,
    "tab922-93b1": 977,
    "tab922-94": 978,
    "tab923-11": 989,
    "tab923-12b": 989,
    "tab923-3f1": 981,
    "tab923-5a": 984,
    "tab924-5": 995,
    "art210-19": 51,
    "art210-20": 52,
    "art215-2": 61,
    "art215-3": 62,
    "art220-12": 64,
    "art220-14": 65,
    "art220-18": 67,
    "art220-44": 68,
    "art220-52": 68,
    "art220-54": 69,
    "art220-55": 69,
    "art220-56": 70,
    "art220-87": 75,
    "art240-4": 101,
    "art240-6": 103,
    "art250-50": 120,
    "art250-52": 121,
    "art250-53": 122,
    "art430-24": 413,
    "art430-25": 414,
    "art430-26": 414,
    "art430-31": 416,
    "art430-32": 416,
    "art430-47": 418,
    "art430-52": 421,
    "art430-102": 431,
    "art440-6": 445,
    "art450-2": 455,
    "art450-3": 455,
    "art450-9": 456,
    "art450-11": 460,
    "art450-13": 457,
    "art450-14": 457,
    "art450-21": 458,
    "art690-7": 796,
    "art690-8": 796,
    "art690-9": 797,
    "art690-14": 800,
    "art690-31": 805,
    "art695-7": 831,
    "art700-5": 600,
    "art700-10": 602,
    "art700-12": 603,
    "art702-4": 729,
    "art702-5": 730,
    "art110-14": 30,
    "art110-26": 32,
    "cap9tablas": 1001,
    "art110-31": 35,
}

# Fallback para REGLAS_NOM_001
if not REGLAS_NOM_001:
    st.warning("⚠️ No se cargaron reglas de validación (REGLAS_NOM_001 vacío). La validación no evaluará nada.")

# ==============================================================================
# CONFIGURACIÓN GLOBAL
# ==============================================================================

st.set_page_config(
    page_title="NOM Viewer — NOM-001-SEDE-2012",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# ESTADO DE SESIÓN
# ==============================================================================

_ESTADO_DEFAULTS: dict = {
    "vista":            "manual",
    "pagina_pdf":       0,
    "zoom_pdf":         2.0,
    "pdf_bytes":        None,
    "resultados":       {},
    "datos_evaluacion": {},
    "elementos":        {},
}


def _init_estado() -> None:
    for clave, valor in _ESTADO_DEFAULTS.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


_init_estado()


# ==============================================================================
# SERVICIO PDF
# ==============================================================================

@st.cache_resource
def _obtener_pdf_service() -> PDFService:
    return PDFService(mapa_articulos=MAPA, cache_paginas=25)


_svc = _obtener_pdf_service()


def _navegar_articulo(clave: str) -> None:
    if _svc.esta_cargado:
        if _svc.tiene_articulo(clave):
            st.session_state.pagina_pdf = _svc.pagina_de_articulo(clave)
            st.session_state.zoom_pdf = 2.0
        else:
            st.toast(f"Artículo '{clave}' no encontrado en la NOM", icon="⚠️")
            return
    st.session_state.vista = "visor"
    st.rerun()


# ==============================================================================
# CSS
# ==============================================================================

st.markdown("""
<style>
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
:root {
    --c-bg: #0f1117; --c-surface: #1a1d27; --c-border: #2a2d3e;
    --c-accent: #f5c518; --c-accent2: #3d8ef5; --c-error: #e85555;
    --c-warn: #f5a623; --c-ok: #52c77a; --c-text: #e2e4ed; --c-muted: #8b8fa8;
}
.card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: 6px; padding: 16px 20px; margin-bottom: 12px; }
.card-accent { border-left: 3px solid var(--c-accent); }
.card-error  { border-left: 3px solid var(--c-error);  background: #1f1518; }
.card-warn   { border-left: 3px solid var(--c-warn);   background: #1f1a12; }
.card-ok     { border-left: 3px solid var(--c-ok);     background: #121f16; }
.formula { background: #0a0c14; border: 1px solid var(--c-border); border-radius: 4px; padding: 10px 14px; font-family: 'IBM Plex Mono', monospace; font-size: 0.88rem; color: var(--c-accent); margin: 8px 0; }
.art-tag { display: inline-block; background: #1a2235; border: 1px solid var(--c-accent2); border-radius: 3px; padding: 2px 7px; font-size: 0.78rem; color: var(--c-accent2); font-family: monospace; margin: 2px 3px; }
.big-val { font-size: 2.2rem; font-weight: 600; font-family: monospace; color: var(--c-accent); line-height: 1.1; }
.big-label { font-size: 0.78rem; color: var(--c-muted); text-transform: uppercase; letter-spacing: 0.08em; }
.sec-header { font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.12em; color: var(--c-muted); border-bottom: 1px solid var(--c-border); padding-bottom: 6px; margin: 20px 0 12px 0; }
.badge-ok   { color: var(--c-ok);    font-weight: 600; }
.badge-err  { color: var(--c-error); font-weight: 600; }
.badge-warn { color: var(--c-warn);  font-weight: 600; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# COMPONENTES REUTILIZABLES
# ==============================================================================

_contador_botones = 0


def _comp_resultado(resultado: ResultadoCalculo) -> None:
    cumple = resultado.cumple
    cls = "card-ok" if cumple is True else ("card-error" if cumple is False else "card")

    items = list(resultado.valores.items())
    val_principal = items[0][1] if items else "—"
    unidad_principal = resultado.unidades.get(items[0][0], "") if items else ""

    if isinstance(val_principal, float):
        val_str = f"{val_principal:.3g}"
    elif isinstance(val_principal, str):
        val_str = val_principal
    else:
        val_str = str(val_principal)

    if cumple is True:
        estado_html = '<span class="badge-ok">✓ CUMPLE</span>'
    elif cumple is False:
        estado_html = '<span class="badge-err">✗ NO CUMPLE</span>'
    else:
        estado_html = ""

    st.markdown(f"""
    <div class="card {cls}">
        <div class="big-val">{val_str}
            <span style="font-size:1rem;color:var(--c-muted)">{unidad_principal}</span>
        </div>
        <div class="big-label">
            {resultado.tipo.replace("_"," ").title()} {estado_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    limite = getattr(resultado, 'limite_normativo', '')
    if limite:
        st.caption(f"📏 {limite}")

    articulos = getattr(resultado, 'articulos_citados', [])
    if articulos:
        arts_html = " ".join(f'<span class="art-tag">{a}</span>' for a in articulos)
        st.markdown(arts_html, unsafe_allow_html=True)

    for adv in resultado.advertencias:
        st.warning(adv)

    with st.expander("Detalle del cálculo"):
        st.code(resultado.detalle, language=None)


def _comp_boton_articulo(label: str, clave: str, key_suffix: str = "") -> None:
    global _contador_botones
    _contador_botones += 1
    key = f"art_{clave}_{key_suffix}_{_contador_botones}"
    if st.button(f"📄 {label}", key=key, help=f"Ver {clave} en la NOM"):
        _navegar_articulo(clave)


def _comp_guardar_en_elemento(nombre_el: str, resultado: ResultadoCalculo) -> None:
    if nombre_el.strip():
        elementos = st.session_state.elementos
        if nombre_el not in elementos:
            elementos[nombre_el] = []
        elementos[nombre_el].append(resultado)
        st.session_state.resultados[resultado.tipo] = resultado
        st.session_state.datos_evaluacion.update(resultado.valores)
        st.toast(f"✓ Cálculo '{resultado.tipo.replace('_',' ').title()}' añadido a '{nombre_el}'", icon="✅")
    else:
        st.error("Debes especificar un nombre para el elemento eléctrico.")


def _comp_separador(titulo: str) -> None:
    st.markdown(f'<div class="sec-header">{titulo}</div>', unsafe_allow_html=True)


# ==============================================================================
# SIDEBAR
# ==============================================================================

with st.sidebar:
    st.markdown("## ⚡ NOM Viewer")
    st.caption("NOM-001-SEDE-2012 — Asistente Técnico")
    st.divider()

    st.markdown('<div class="sec-header">Archivo NOM</div>', unsafe_allow_html=True)
    pdf_upload = st.file_uploader(
        "Sube la NOM-001-SEDE-2012.pdf", type=["pdf"],
        help="Descárgalo gratis desde el DOF o gob.mx",
        label_visibility="collapsed",
    )

    if pdf_upload:
        contenido = pdf_upload.read()
        if contenido != st.session_state.pdf_bytes:
            st.session_state.pdf_bytes = contenido
            try:
                meta = _svc.cargar_desde_bytes(contenido)
                st.session_state.pagina_pdf = 0
                st.success(f"✓ {meta.total_paginas} páginas cargadas")
            except ArchivoInvalidoError as e:
                st.error(str(e))
    elif _svc.esta_cargado:
        st.caption(f"✓ {_svc.total_paginas} páginas en memoria")
    else:
        st.info("Sube el PDF para activar el Visor NOM")

    st.divider()

    # ==========================================================================
    # ENLACES ÚTILES (añadidos)
    # ==========================================================================
    st.markdown('<div class="sec-header">🌐 Enlaces útiles</div>', unsafe_allow_html=True)
    
    # Botón para retroalimentación (Google Forms)
    st.link_button(
        "📝 Formulario de retroalimentación",
        "https://docs.google.com/forms/d/e/1FAIpQLSckNJrFWfLzLyAl2qAxSwr7HLRo8QVfvjOT8-Rjia5qwN_aSg/viewform?usp=header",
        help="Abre el formulario para enviar comentarios, reportar errores o sugerir mejoras.",
        use_container_width=True,
    )
    
    # Botón para descargar la NOM en PDF (Google Drive)
    st.link_button(
        "📥 Descargar NOM-001-SEDE-2012 (PDF)",
        "https://drive.google.com/file/d/1pD823-cEUWY1tPMqJYO96YQxuE9v3FgX/view?usp=sharing",
        help="Descarga el PDF oficial de la NOM-001-SEDE-2012 (desde Google Drive). Luego súbelo en la sección 'Archivo NOM' para usar el visor.",
        use_container_width=True,
    )
    
    st.caption("Recuerda: después de descargar el PDF, súbelo arriba para habilitar el visor completo.")
    st.divider()
    # ==========================================================================

    opciones = {
        "📘 Manual": "manual",
        "📄 Visor NOM": "visor",
        "🧮 Calculadoras": "calculadoras",
        "✅ Validación": "validacion",
        "📋 Resultados Acumulados": "resultados",
    }
    vista_actual = st.session_state.vista
    idx_actual = list(opciones.values()).index(vista_actual) if vista_actual in opciones.values() else 0

    seleccion = st.radio(
        "Sección", list(opciones.keys()),
        index=idx_actual, label_visibility="collapsed",
    )
    nueva_vista = opciones[seleccion]
    if nueva_vista != st.session_state.vista:
        st.session_state.vista = nueva_vista
        st.rerun()

    st.divider()

    st.markdown('<div class="sec-header">Ir a artículo</div>', unsafe_allow_html=True)
    art_buscar = st.text_input(
        "Ej: art220-12, tab9",
        label_visibility="collapsed",
        placeholder="art...",
        key="sidebar_art_input",
    )
    if st.button("Buscar", key="sidebar_buscar", use_container_width=True):
        if art_buscar:
            _navegar_articulo(art_buscar.strip().lower())


# ==============================================================================
# VISTA: MANUAL TÉCNICO
# ==============================================================================

def _vista_manual() -> None:
    st.title("📘 Manual Técnico — NOM-001-SEDE-2012")
    st.caption("Referencia estructurada de la memoria técnica de instalaciones eléctricas.")

    secciones = [
        (1, "Portada y datos generales", ["Nombre del proyecto", "Ubicación", "Propietario", "Proyectista", "Fecha"], []),
        (2, "Marco normativo", ["NOM-001-SEDE-2012", "PEC-NOM-001", "Otras NOM aplicables"], []),
        (3, "Descripción del inmueble", ["Tipo de inmueble", "Niveles y superficie", "Uso principal"], []),
        (4, "Condiciones de diseño", ["Altitud y temperatura", "Sistema de suministro", "Nivel de tensión"], []),
        (5, "Cálculo de cargas", ["Inventario de cargas", "Demanda máxima", "Factor de demanda"],
         [("Art. 220", "art220"), ("Art. 220-12", "art220-12"), ("Art. 220-14", "art220-14")]),
        (6, "Alimentadores y conductores", ["Selección de calibre", "Caída de tensión", "Aislamiento", "Identificación"],
         [("Tabla 310-15", "tab310-15b16"), ("Art. 210-19", "art210-19"), ("Tabla 9", "tab9")]),
        (7, "Canalizaciones", ["EMT, IMC, PVC, charolas", "Factor de llenado", "Radios de curvatura"],
         [("Art. 358", "art358"), ("Art. 352", "art352"), ("Art. 392", "art392")]),
        (8, "Protecciones eléctricas", ["ITMs y fusibles", "Coordinación conductor-protección", "kAIC"],
         [("Art. 240", "art240"), ("Art. 240-6", "art240-6"), ("Art. 430", "art430")]),
        (9, "Puesta a tierra", ["Electrodos permitidos", "Conductores de tierra", "Pararrayos y SPDs"],
         [("Art. 250", "art250"), ("Art. 250-52", "art250-52"), ("Tabla 250-66", "tab250-66")]),
        (10, "Tableros eléctricos", ["Diagrama unifilar", "Cuadro de cargas", "Espacios libres"],
         [("Art. 408", "art408")]),
        (11, "Transformadores", ["Potencia y nivel de tensión", "Corriente nominal", "Protecciones"],
         [("Art. 450", "art450"), ("Art. 450-3", "art450-3")]),
        (12, "Sistemas especiales", ["Emergencia", "Bombas contra incendio", "Elevadores"],
         [("Art. 700", "art700"), ("Art. 695", "art695"), ("Art. 620", "art620")]),
        (13, "Diagramas eléctricos", ["Diagrama unifilar", "Planos de distribución"], []),
        (14, "Memorias de cálculo", ["Cargas", "Conductores", "Protecciones", "Caída de tensión"], []),
        (15, "Especificaciones técnicas", ["Materiales", "Normas de calidad", "Métodos de instalación"], []),
        (16, "Conclusiones", ["Cumplimiento normativo", "Firma y cédula profesional"], []),
    ]

    for num, titulo, items, arts in secciones:
        with st.expander(f"{num}. {titulo}", expanded=(num <= 2)):
            for item in items:
                st.markdown(f"- {item}")
            if arts:
                st.markdown("")
                cols = st.columns(len(arts))
                for col, (label, clave) in zip(cols, arts):
                    with col:
                        _comp_boton_articulo(label, clave, key_suffix=f"m{num}")


# ==============================================================================
# VISTA: VISOR NOM
# ==============================================================================

def _construir_indice_jerarquico(mapa: dict[str, int]) -> dict:
    indice = {"articulos": defaultdict(lambda: {"pagina": None, "subs": {}}),
              "tablas": defaultdict(lambda: {"pagina": None, "subs": {}})}
    for clave, pagina in mapa.items():
        if clave.startswith("art"):
            tipo = "articulos"
            match = re.match(r'(art\d+)(?:-(.*))?', clave)
            if match:
                base = match.group(1)
                sub = match.group(2)
                entrada = indice[tipo][base]
                if sub is None:
                    entrada["pagina"] = pagina
                else:
                    entrada["subs"][f"{base}-{sub}"] = {"pagina": pagina}
            else:
                indice[tipo][clave]["pagina"] = pagina
        elif clave.startswith("tab") or clave.startswith("cap"):
            tipo = "tablas"
            match = re.match(r'(tab\d+)(?:-(.*))?', clave)
            if match:
                base = match.group(1)
                sub = match.group(2)
                entrada = indice[tipo][base]
                if sub is None:
                    entrada["pagina"] = pagina
                else:
                    entrada["subs"][f"{base}-{sub}"] = {"pagina": pagina}
            else:
                indice[tipo][clave]["pagina"] = pagina
    for tipo in indice:
        indice[tipo] = dict(indice[tipo])
    return indice


@st.cache_data
def _obtener_indice():
    return _construir_indice_jerarquico(MAPA)


def _filtrar_indice(indice: dict, texto: str) -> dict:
    if not texto:
        return indice
    texto = texto.lower()
    filtrado = {"articulos": {}, "tablas": {}}
    for tipo in ["articulos", "tablas"]:
        for base, info in indice[tipo].items():
            base_match = texto in base.lower()
            subs_filtrados = {}
            for subclave, subinfo in info["subs"].items():
                if texto in subclave.lower() or base_match:
                    subs_filtrados[subclave] = subinfo
            if base_match or subs_filtrados:
                filtrado[tipo][base] = {"pagina": info["pagina"], "subs": subs_filtrados}
    return filtrado


def _renderizar_indice(indice: dict, prefijo: str = "") -> None:
    MAX_SUBS_PARA_BOTONES = 15
    contador = 0
    for tipo, icono in [("articulos", "📜"), ("tablas", "📊")]:
        if indice.get(tipo):
            st.markdown(f"### {icono} {tipo.capitalize()}")
            for base, info in sorted(indice[tipo].items()):
                unique_key = f"{prefijo}_{tipo}_{base}_{contador}"
                contador += 1
                if info["subs"]:
                    with st.expander(f"{base} (pág. {info['pagina']})" if info['pagina'] else base):
                        if info['pagina']:
                            if st.button(f"📄 {base}", key=f"{unique_key}_btn"):
                                _navegar_articulo(base)
                        subs = sorted(info["subs"].items())
                        if len(subs) > MAX_SUBS_PARA_BOTONES:
                            opciones = ["Seleccionar..."] + [subclave for subclave, _ in subs]
                            seleccion = st.selectbox("Ir a subartículo:", opciones, key=f"{unique_key}_sel")
                            if seleccion != "Seleccionar...":
                                _navegar_articulo(seleccion)
                        else:
                            cols = st.columns(3)
                            for idx, (subclave, subinfo) in enumerate(subs):
                                with cols[idx % 3]:
                                    if st.button(subclave, key=f"{unique_key}_sub_{subclave}"):
                                        _navegar_articulo(subclave)
                else:
                    if st.button(f"📄 {base} (pág. {info['pagina']})", key=f"{unique_key}_btn"):
                        _navegar_articulo(base)


def _vista_visor() -> None:
    st.title("📄 Visor NOM-001-SEDE-2012")

    if not _svc.esta_cargado:
        st.warning("⚠️ Sube el PDF en el panel lateral para usar el visor.")
        st.info("Descarga la NOM-001-SEDE-2012 gratuitamente desde el DOF (dof.gob.mx).")
        return

    total = _svc.total_paginas

    c1, c2, c3, c4, c5 = st.columns([1, 1, 3, 1, 1])
    with c1:
        if st.button("⏮", help="Primera página", key="v_prim"):
            st.session_state.pagina_pdf = 0
            st.rerun()
    with c2:
        if st.button("◀", help="Página anterior", key="v_ant"):
            st.session_state.pagina_pdf = _svc.pagina_anterior(st.session_state.pagina_pdf)
            st.rerun()
    with c3:
        pag_input = st.number_input(
            "Ir a página", min_value=1, max_value=total,
            value=st.session_state.pagina_pdf + 1, label_visibility="collapsed",
        )
        if int(pag_input) - 1 != st.session_state.pagina_pdf:
            st.session_state.pagina_pdf = int(pag_input) - 1
            st.rerun()
    with c4:
        if st.button("▶", help="Página siguiente", key="v_sig"):
            st.session_state.pagina_pdf = _svc.pagina_siguiente(st.session_state.pagina_pdf)
            st.rerun()
    with c5:
        if st.button("⏭", help="Última página", key="v_ult"):
            st.session_state.pagina_pdf = total - 1
            st.rerun()

    zoom = st.select_slider(
        "Zoom", options=[0.75, 1.0, 1.5, 2.0, 2.5, 3.0],
        value=st.session_state.zoom_pdf, key="v_zoom",
    )
    st.session_state.zoom_pdf = zoom
    st.caption(f"Página {st.session_state.pagina_pdf + 1} de {total}")

    arts_pagina = _svc.articulos_en_pagina(st.session_state.pagina_pdf)
    if arts_pagina:
        arts_html = " ".join(f'<span class="art-tag">{a}</span>' for a in arts_pagina)
        st.markdown(arts_html, unsafe_allow_html=True)

    try:
        pagina = _svc.renderizar_pagina(st.session_state.pagina_pdf, zoom=zoom)
        st.image(pagina.imagen, use_container_width=True)
    except PDFNoCargadoError:
        st.error("PDF no disponible. Vuelve a subirlo.")
    except Exception as e:
        st.error(f"Error al renderizar: {e}")

    st.divider()

    modo_opciones = {"Navegación Rápida": "rapida", "Índice Completo": "completo"}
    modo_actual = st.radio(
        "Modo de navegación:",
        list(modo_opciones.keys()),
        horizontal=True,
        key="visor_modo_nav",
    )
    st.divider()

    if modo_actual == "Navegación Rápida":
        _comp_separador("Navegación Rápida")
        categorias_nav = {
            "Cargas":             ["art220", "art220-12", "art220-14", "art220-52",
                                   "tab220-12", "tab220-3", "tab220-42"],
            "Conductores":        ["art310", "tab310-15b16", "tab310-15b2b",
                                   "tab310-15b3a", "tab9", "art210-19", "art215-2"],
            "Protecciones":       ["art240", "art240-6", "art240-4",
                                   "art430", "art430-52", "tab430-52"],
            "Tierra":             ["art250", "art250-52", "art250-50",
                                   "tab250-66", "tab250-122", "tab250-3"],
            "Canalizaciones":     ["art358", "art352", "art392", "art342",
                                   "art344", "art366", "cap9tablas"],
            "Transformadores":    ["art450", "art450-3", "art450-2",
                                   "tab450-3a", "tab450-3b"],
            "Motores":            ["art430", "art430-24", "art430-25",
                                   "art430-31", "art430-32", "tab430-10"],
            "Emergencia":         ["art700", "art695", "art620",
                                   "art701", "art702"],
            "Fotovoltaico":       ["art690", "art690-7", "art690-8",
                                   "art690-9", "art690-31", "tab690-7"],
            "Tableros":           ["art408", "art409", "art404",
                                   "art110-26", "tab408-5"],
            "Acometidas":         ["art230", "art225", "art215",
                                   "art215-2", "art215-3"],
            "Areas Clasificadas": ["art500", "art501", "art502",
                                   "art503", "art516"],
        }

        global _contador_botones
        for cat, claves in categorias_nav.items():
            with st.expander(cat):
                cols = st.columns(4)
                for i, clave in enumerate(claves):
                    with cols[i % 4]:
                        _contador_botones += 1
                        key_unica = f"vnav_{clave}_{_contador_botones}"
                        if st.button(clave, key=key_unica, use_container_width=True):
                            _navegar_articulo(clave)
    else:
        _comp_separador("Índice Completo")
        st.caption("Estructura jerárquica de la NOM-001-SEDE-2012 generada desde el MAPA")
        texto_busqueda = st.text_input("🔍 Buscar artículo o tabla (escribe parte de la clave)", key="buscar_indice")
        indice_completo = _obtener_indice()
        indice_mostrado = _filtrar_indice(indice_completo, texto_busqueda)
        _renderizar_indice(indice_mostrado, prefijo="indice")


# ==============================================================================
# VISTA: CALCULADORAS
# ==============================================================================

def _vista_calculadoras() -> None:
    st.title("🧮 Calculadoras Eléctricas")
    st.caption("Resultados con respaldo normativo. Asigna cada cálculo a un elemento del sistema eléctrico.")

    tabs = st.tabs(["Caída de Tensión", "Calibre", "Cargas", "Protecciones", "Transformador", "Puesta a Tierra"])

    # --- Caída de Tensión ---
    with tabs[0]:
        _comp_separador("Caída de Tensión — Tabla 9 NOM-001-SEDE-2012")
        nombre_elem = st.text_input("Nombre del elemento eléctrico", key="elem_cdt", placeholder="Ej. Alimentador principal")
        c1, c2, c3 = st.columns(3)
        with c1:
            cdt_tipo = st.selectbox("Tipo", ["Trifásico","Monofásico 2 hilos","Monofásico 3 hilos"], key="cdt_tipo")
            cdt_mat  = st.selectbox("Material", ["cobre","aluminio"], key="cdt_mat")
        with c2:
            cdt_cond = st.selectbox("Conduit", ["PVC","Aluminio","Acero"], key="cdt_cond")
            cdt_cal  = st.selectbox("Calibre AWG/kcmil", CALIBRES_ORDENADOS, index=5, key="cdt_cal")
        with c3:
            cdt_L  = st.number_input("Longitud (m)",         min_value=0.1, value=50.0,  key="cdt_L")
            cdt_I  = st.number_input("Corriente (A)",        min_value=0.1, value=20.0,  key="cdt_I")
        c4, c5, c6 = st.columns(3)
        with c4: cdt_V  = st.number_input("Voltaje (V)",     min_value=1.0, value=220.0, key="cdt_V")
        with c5: cdt_fp = st.number_input("Factor potencia", min_value=0.01, max_value=1.0, value=0.85, key="cdt_fp")
        with c6: cdt_Cf = st.number_input("Cond. / fase",    min_value=1, value=1, key="cdt_Cf")

        if st.button("Calcular caída", key="btn_cdt", type="primary"):
            try:
                res = calcular_caida_tension(cdt_tipo, cdt_mat, cdt_cond, cdt_cal, cdt_L, cdt_I, cdt_V, cdt_fp, cdt_Cf)
                _comp_guardar_en_elemento(nombre_elem, res)
                _comp_resultado(res)
                c1b, c2b = st.columns(2)
                with c1b: _comp_boton_articulo("Art. 210-19", "art210-19", "cdt_r1")
                with c2b: _comp_boton_articulo("Tabla 9",     "tab9",      "cdt_r2")
            except (ValueError, KeyError) as e:
                st.error(str(e))

    # --- Calibre ---
    with tabs[1]:
        _comp_separador("Selección de Calibre — Ampacidad y Caída de Tensión")
        nombre_elem = st.text_input("Nombre del elemento eléctrico", key="elem_cc", placeholder="Ej. Alimentador principal")
        c1, c2, c3 = st.columns(3)
        with c1:
            cc_tipo  = st.selectbox("Tipo", ["Trifásico","Monofásico 2 hilos","Monofásico 3 hilos"], key="cc_tipo")
            cc_mat   = st.selectbox("Material", ["cobre","aluminio"], key="cc_mat")
        with c2:
            cc_cond  = st.selectbox("Conduit", ["PVC","Aluminio","Acero"], key="cc_cond")
            cc_temp  = st.number_input("Temp. ambiente (°C)", value=30, step=5, key="cc_temp")
        with c3:
            cc_I     = st.number_input("Corriente (A)",   min_value=0.1, value=30.0, key="cc_I")
            cc_L     = st.number_input("Longitud (m)",    min_value=0.1, value=40.0, key="cc_L")
        c4, c5, c6 = st.columns(3)
        with c4: cc_V    = st.number_input("Voltaje (V)",    min_value=1.0, value=220.0, key="cc_V")
        with c5: cc_fp   = st.number_input("Factor potencia",min_value=0.01, max_value=1.0, value=0.85, key="cc_fp")
        with c6: cc_nc   = st.number_input("Cond. en canaliz.", min_value=1, value=3, key="cc_nc")
        cc_caida = st.slider("Caída máxima (%)", 0.5, 5.0, 3.0, 0.5, key="cc_caida")

        if st.button("Seleccionar calibre", key="btn_cc", type="primary"):
            try:
                res = seleccionar_calibre(
                    corriente_carga_a=cc_I, longitud_m=cc_L, voltaje_v=cc_V,
                    tipo_circuito=cc_tipo, material=cc_mat, conduit=cc_cond,
                    temp_ambiente_c=cc_temp, num_conductores_canaliz=cc_nc,
                    factor_potencia=cc_fp, caida_max_pct=cc_caida,
                )
                _comp_guardar_en_elemento(nombre_elem, res)
                _comp_resultado(res)
                c1b, c2b, c3b = st.columns(3)
                with c1b: _comp_boton_articulo("Tabla 310-15(b)(16)", "tab310-15b16", "cc_r1")
                with c2b: _comp_boton_articulo("Art. 310",            "art310",       "cc_r2")
                with c3b: _comp_boton_articulo("Art. 210-19",         "art210-19",    "cc_r3")
            except (ValueError, KeyError) as e:
                st.error(str(e))

    # --- Cargas ---
    with tabs[2]:
        _comp_separador("Cálculo de Cargas — Art. 220")
        nombre_elem = st.text_input("Nombre del elemento eléctrico", key="elem_cg", placeholder="Ej. Tablero principal")
        c1, c2 = st.columns(2)
        with c1:
            cg_tipo = st.selectbox("Tipo de inmueble", list(FACTORES_DEMANDA.keys()), key="cg_tipo")
            cg_area = st.number_input("Superficie (m²)", min_value=1.0, value=100.0, step=10.0, key="cg_area")
        with c2:
            cg_V    = st.number_input("Voltaje (V)",     min_value=1.0, value=220.0, key="cg_V")
            cg_fp   = st.number_input("Factor potencia", min_value=0.01, max_value=1.0, value=0.90, key="cg_fp")
        _comp_separador("Cargas específicas")
        c3, c4, c5 = st.columns(3)
        with c3:
            cg_cal  = st.number_input("Calefacción / HVAC (W)", value=0.0, step=500.0, key="cg_cal")
            cg_agua = st.number_input("Calentador agua (W)",    value=0.0, step=500.0, key="cg_agua")
        with c4:
            cg_est  = st.number_input("Estufa / Horno (W)",     value=0.0, step=500.0, key="cg_est")
            cg_mot  = st.number_input("Motores total (W)",      value=0.0, step=500.0, key="cg_mot")
        with c5:
            cg_aire = st.number_input("Aire acondicionado (W)", value=0.0, step=500.0, key="cg_aire")
            cg_otro = st.number_input("Otros equipos (W)",      value=0.0, step=500.0, key="cg_otro")

        if st.button("Calcular cargas", key="btn_cg", type="primary"):
            try:
                res = calcular_cargas(
                    tipo_inmueble=cg_tipo, area_m2=cg_area,
                    carga_calefaccion_w=cg_cal, carga_agua_w=cg_agua,
                    carga_estufa_w=cg_est, carga_motores_w=cg_mot,
                    carga_aire_w=cg_aire, carga_otros_w=cg_otro,
                    voltaje_v=cg_V, factor_potencia=cg_fp,
                )
                _comp_guardar_en_elemento(nombre_elem, res)
                _comp_resultado(res)
                c1b, c2b, c3b = st.columns(3)
                with c1b: _comp_boton_articulo("Art. 220-12","art220-12","cg_r1")
                with c2b: _comp_boton_articulo("Art. 220-14","art220-14","cg_r2")
                with c3b: _comp_boton_articulo("Art. 220-52","art220-52","cg_r3")
            except (ValueError, KeyError) as e:
                st.error(str(e))

    # --- Protecciones ---
    with tabs[3]:
        _comp_separador("Selección de Protecciones — Art. 240")
        nombre_elem = st.text_input("Nombre del elemento eléctrico", key="elem_pt", placeholder="Ej. Interruptor principal")
        c1, c2 = st.columns(2)
        with c1:
            pt_tipo = st.selectbox("Tipo de carga", ["General","Motor","Transformador"], key="pt_tipo")
            pt_Ic   = st.number_input("Corriente de carga (A)", min_value=0.1, value=30.0, key="pt_Ic")
        with c2:
            pt_icc  = st.number_input("Icc disponible (kA)",   min_value=0.1, value=10.0, key="pt_icc")
            pt_amp  = st.number_input("Ampacidad conductor (A)",min_value=0.0, value=0.0,  key="pt_amp",
                                      help="0 = no verificar coordinación")

        if st.button("Seleccionar protección", key="btn_pt", type="primary"):
            try:
                amp_cond = pt_amp if pt_amp > 0 else None
                res = seleccionar_proteccion(
                    tipo_carga=pt_tipo, corriente_carga_a=pt_Ic,
                    icc_disponible_ka=pt_icc, ampacidad_conductor_a=amp_cond,
                )
                _comp_guardar_en_elemento(nombre_elem, res)
                _comp_resultado(res)
                c1b, c2b = st.columns(2)
                with c1b: _comp_boton_articulo("Art. 240",  "art240",   "pt_r1")
                with c2b: _comp_boton_articulo("Art. 240-6","art240-6", "pt_r2")
            except (ValueError, KeyError) as e:
                st.error(str(e))

    # --- Transformador ---
    with tabs[4]:
        _comp_separador("Dimensionamiento de Transformador — Art. 450")
        nombre_elem = st.text_input("Nombre del elemento eléctrico", key="elem_tr", placeholder="Ej. Transformador T1")
        c1, c2, c3 = st.columns(3)
        with c1:
            tr_carga = st.number_input("Carga demandada (kVA)", min_value=1.0, value=150.0, step=10.0, key="tr_carga")
            tr_fc    = st.number_input("Factor crecimiento (%)",value=20.0, step=5.0, key="tr_fc")
        with c2:
            tr_vprim = st.selectbox("Voltaje primario (V)",  [13200,23000,34500,44000,69000], key="tr_vprim")
            tr_vsec  = st.selectbox("Voltaje secundario (V)",[120,208,220,480], key="tr_vsec")
        with c3:
            tr_sis = st.selectbox("Sistema", ["Trifásico","Monofásico"], key="tr_sis")

        if st.button("Dimensionar transformador", key="btn_tr", type="primary"):
            try:
                res = dimensionar_transformador(
                    carga_demandada_kva=tr_carga,
                    voltaje_primario_v=float(tr_vprim),
                    voltaje_secundario_v=float(tr_vsec),
                    sistema=tr_sis,
                    factor_crecimiento=tr_fc / 100.0,
                )
                _comp_guardar_en_elemento(nombre_elem, res)
                _comp_resultado(res)
                c1b, c2b = st.columns(2)
                with c1b: _comp_boton_articulo("Art. 450",  "art450",   "tr_r1")
                with c2b: _comp_boton_articulo("Art. 450-3","art450-3", "tr_r2")
            except (ValueError, KeyError) as e:
                st.error(str(e))

    # --- Puesta a Tierra ---
    with tabs[5]:
        _comp_separador("Puesta a Tierra — Art. 250")
        nombre_elem = st.text_input("Nombre del elemento eléctrico", key="elem_ptt", placeholder="Ej. Sistema de tierra general")
        c1, c2 = st.columns(2)
        with c1:
            ptt_V    = st.number_input("Voltaje línea-neutro (V)", min_value=1.0, value=127.0, step=10.0, key="ptt_V")
            ptt_R    = st.number_input("Resistencia de tierra (Ω)",min_value=0.1, value=5.0,   step=0.5,  key="ptt_R")
        with c2:
            ptt_mat  = st.selectbox("Material conductor tierra", ["Cobre","Aluminio"], key="ptt_mat")
            ptt_Ialim= st.number_input("Corriente alimentador (A)", min_value=0.0, value=0.0, key="ptt_Ialim",
                                       help="0 = usar corriente de falla estimada")

        if st.button("Calcular tierra", key="btn_ptt", type="primary"):
            try:
                Ialim = ptt_Ialim if ptt_Ialim > 0 else None
                res = calcular_puesta_tierra(
                    voltaje_linea_neutro_v=ptt_V,
                    resistencia_tierra_ohm=ptt_R,
                    material_conductor=ptt_mat,
                    corriente_alimentador_a=Ialim,
                )
                _comp_guardar_en_elemento(nombre_elem, res)
                _comp_resultado(res)
                c1b, c2b, c3b = st.columns(3)
                with c1b: _comp_boton_articulo("Art. 250",     "art250",     "ptt_r1")
                with c2b: _comp_boton_articulo("Art. 250-52",  "art250-52",  "ptt_r2")
                with c3b: _comp_boton_articulo("Tabla 250-66", "tab250-66", "ptt_r3")
            except (ValueError, KeyError) as e:
                st.error(str(e))


# ==============================================================================
# VISTA: VALIDACIÓN NORMATIVA (por elemento)
# ==============================================================================

def _vista_validacion() -> None:
    st.title("✅ Validación Normativa")
    st.caption("Verifica el cumplimiento de la NOM-001-SEDE-2012 para todos los elementos calculados.")

    elementos = st.session_state.elementos

    if not elementos:
        st.info("Aún no hay cálculos acumulados. Ve a **Calculadoras** y asigna los resultados a un elemento eléctrico.")
        return

    if not REGLAS_NOM_001:
        st.error("No se cargaron reglas de validación. Revisa la instalación de core/reglas.py.")
        return

    total_evaluadas = 0
    total_cumplidas = 0
    total_errores = 0
    total_advertencias = 0

    for nombre_el, calculos in elementos.items():
        st.subheader(f"⚡ {nombre_el}")
        for i, resultado in enumerate(calculos):
            datos_planos = resultado.valores
            if REGLAS_NOM_001:
                try:
                    resumen = evaluar_y_formatear(datos_planos, REGLAS_NOM_001)
                except Exception as e:
                    st.warning(f"No se pudo evaluar '{resultado.tipo}': {e}")
                    continue
                total_evaluadas += resumen.total_evaluadas
                total_cumplidas += resumen.total_cumplidas
                total_errores += resumen.total_errores
                total_advertencias += resumen.total_advertencias

                estado = "✓ CUMPLE" if resumen.aprobado else "✗ NO CUMPLE"
                st.markdown(f"**{resultado.tipo.replace('_',' ').title()}** — {estado}")
                if not resumen.aprobado:
                    for err in resumen.errores_criticos():
                        st.markdown(f"- ❌ {err.referencia}: {err.mensaje}")
                    for adv in resumen.advertencias_activas():
                        st.markdown(f"- ⚠️ {adv.referencia}: {adv.mensaje}")
            else:
                if resultado.cumple is True:
                    st.markdown(f"**{resultado.tipo.replace('_',' ').title()}** — ✓ CUMPLE")
                elif resultado.cumple is False:
                    st.markdown(f"**{resultado.tipo.replace('_',' ').title()}** — ✗ NO CUMPLE")
                else:
                    st.markdown(f"**{resultado.tipo.replace('_',' ').title()}** — ? Sin evaluar")
            st.markdown("---")

    st.divider()
    st.subheader("Resumen Global de Validación")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Evaluaciones", total_evaluadas)
    col2.metric("Cumplidas", total_cumplidas)
    col3.metric("Errores", total_errores)
    col4.metric("Advertencias", total_advertencias)


# ==============================================================================
# VISTA: RESULTADOS ACUMULADOS
# ==============================================================================

def _vista_resultados_acumulados() -> None:
    st.title("📋 Resultados Acumulados de Cálculo")
    st.caption("Todos los cálculos organizados por elemento eléctrico.")

    elementos = st.session_state.elementos

    if not elementos:
        st.info("No hay resultados acumulados. Ve a **Calculadoras** y asigna cada cálculo a un elemento eléctrico.")
        return

    for nombre_el, calculos in elementos.items():
        with st.expander(f"⚡ {nombre_el} ({len(calculos)} cálculo(s))"):
            for resultado in calculos:
                _comp_resultado(resultado)

    if st.button("📄 Exportar PDF de Resultados", type="primary"):
        try:
            from fpdf import FPDF

            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.set_font("Helvetica", "B", 14)
            pdf.cell(0, 10, "Resultados de Calculo NOM-001-SEDE-2012", 0, 1, "C")
            pdf.ln(5)

            pdf.set_font("Helvetica", "", 10)
            for nombre_el, calculos in elementos.items():
                pdf.set_font("Helvetica", "B", 11)
                pdf.cell(0, 8, nombre_el, 0, 1)
                pdf.set_font("Helvetica", "", 10)
                for res in calculos:
                    tipo = res.tipo.replace("_", " ").title()
                    items = list(res.valores.items())
                    val_principal = items[0][1] if items else "—"
                    unidad = res.unidades.get(items[0][0], "") if items else ""
                    if isinstance(val_principal, float):
                        val_str = f"{val_principal:.3g} {unidad}"
                    else:
                        val_str = f"{val_principal} {unidad}"
                    cumple_str = "Cumple" if res.cumple is True else ("No cumple" if res.cumple is False else "No evaluado")
                    linea = f"{tipo}: {val_str} — {cumple_str}"
                    pdf.cell(0, 6, _sanitize_text(linea), 0, 1)
                pdf.ln(3)

            salida = pdf.output(dest="S")
            if isinstance(salida, str):
                pdf_bytes = salida.encode("latin-1")
            else:
                pdf_bytes = bytes(salida)

            st.download_button(
                label="⬇ Descargar PDF",
                data=pdf_bytes,
                file_name="Resultados_NOM001.pdf",
                mime="application/pdf",
                key="dl_resultados",
            )
        except ImportError:
            st.error("Instala fpdf2: `pip install fpdf2`")
        except Exception as exc:
            st.error(f"Error al generar PDF: {exc}")


# ==============================================================================
# Función sanitizadora para PDF
# ==============================================================================

def _sanitize_text(text: str) -> str:
    return text.encode('latin-1', errors='replace').decode('latin-1')


# ==============================================================================
# ROUTER PRINCIPAL
# ==============================================================================

_VISTAS = {
    "manual":       _vista_manual,
    "visor":        _vista_visor,
    "calculadoras": _vista_calculadoras,
    "validacion":   _vista_validacion,
    "resultados":   _vista_resultados_acumulados,
}

_VISTAS.get(st.session_state.vista, _vista_manual)()