import fitz
import re
from pathlib import Path
import json

# ==============================
# CONFIGURACIÓN
# ==============================
CARPETA = Path(r"C:\Users\Fulanito\Documents\Programa NOM exito\Programa")
IGNORE_HASTA = 20  # páginas del índice


# ==============================
# DETECTAR PDF
# ==============================
def detectar_pdf():
    pdfs = list(CARPETA.glob("*.pdf"))
    if not pdfs:
        raise Exception("No se encontró ningún PDF en la carpeta")
    return pdfs[0]


# ==============================
# NORMALIZAR CLAVE
# ==============================
def normalizar(valor, tipo):
    valor = valor.lower()
    valor = re.sub(r"\(([a-z0-9]+)\)", r"\1", valor)
    valor = valor.replace(" ", "").replace(".", "")
    return f"{tipo}{valor}"


# ==============================
# ESCANEAR PDF
# ==============================
def escanear(pdf_path):
    doc = fitz.open(pdf_path)
    mapa = {}

    for i in range(len(doc)):
        pagina = doc.load_page(i)
        texto = pagina.get_text("text")

        lineas = texto.split("\n")

        for linea in lineas:
            l = linea.strip()

            if not l:
                continue

            # ======================
            # ARTÍCULOS (corregido)
            # ======================
            match_art = re.match(
                r"^ART[ÍI]CULO\s+(\d{2,3}(?:-\d+)?)",
                l,
                re.IGNORECASE
            )

            if match_art:
                # ignorar índice
                if i < IGNORE_HASTA:
                    continue

                # validar encabezado real
                if not l.upper().startswith("ART"):
                    continue

                clave = normalizar(match_art.group(1), "art")

                if clave not in mapa:
                    mapa[clave] = i

                continue

            # ======================
            # TABLAS (ya funciona)
            # ======================
            match_tab = re.match(
                r"^Tabla\s+([\d\-]+(?:\([a-z0-9]+\))*)",
                l,
                re.IGNORECASE
            )

            if match_tab:
                clave = normalizar(match_tab.group(1), "tab")

                if clave not in mapa:
                    mapa[clave] = i

    doc.close()
    return mapa


# ==============================
# GUARDAR RESULTADOS
# ==============================
def guardar(mapa):
    ruta_py = CARPETA / "mapa_generado.py"
    ruta_json = CARPETA / "mapa_generado.json"

    # Python
    with open(ruta_py, "w", encoding="utf-8") as f:
        f.write("MAPA = {\n")
        for k, v in sorted(mapa.items()):
            f.write(f'    "{k}": {v},\n')
        f.write("}\n")

    # JSON (página base 1)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump({k: v + 1 for k, v in mapa.items()}, f, indent=2)

    print("Archivos generados:")
    print(ruta_py)
    print(ruta_json)


# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    pdf = detectar_pdf()
    print("PDF encontrado:", pdf.name)

    mapa = escanear(str(pdf))

    print("Total detectado:", len(mapa))

    guardar(mapa)