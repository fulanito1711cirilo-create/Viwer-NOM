"""
services/pdf_service.py
=======================
Servicio de visualización de PDF para la NOM-001-SEDE-2012.

Sin dependencias de Streamlit. Usa PyMuPDF (fitz) para renderizar páginas.
"""

from typing import Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from PIL import Image
except ImportError:
    Image = None


class ArchivoInvalidoError(Exception):
    """El archivo subido no es un PDF válido."""
    pass


class PDFNoCaregadoError(Exception):
    """No hay PDF cargado en memoria."""
    pass


class ArticuloNoEncontradoError(Exception):
    """El artículo solicitado no está en el mapa."""
    pass


class PaginaRenderizada:
    def __init__(self, imagen: Any):
        self.imagen = imagen


class PDFService:
    def __init__(self, mapa_articulos: Optional[dict[str, int]] = None, cache_paginas: int = 25):
        if fitz is None:
            raise ImportError("PyMuPDF no está instalado. Ejecuta: pip install PyMuPDF")
        self._doc: Optional[Any] = None
        self._total_paginas: int = 0
        self._mapa = mapa_articulos or {}
        self._cache_size = cache_paginas
        self._cache: dict[int, PaginaRenderizada] = {}

    @property
    def esta_cargado(self) -> bool:
        return self._doc is not None

    @property
    def total_paginas(self) -> int:
        return self._total_paginas

    def cargar_desde_bytes(self, contenido: bytes) -> "PDFService":
        try:
            self._doc = fitz.open(stream=contenido, filetype="pdf")
            self._total_paginas = len(self._doc)
            self._cache.clear()
            return self
        except Exception as e:
            raise ArchivoInvalidoError(f"No se pudo cargar el PDF: {e}")

    def tiene_articulo(self, clave: str) -> bool:
        return clave.lower() in self._mapa

    def pagina_de_articulo(self, clave: str) -> int:
        clave = clave.lower()
        if clave not in self._mapa:
            raise ArticuloNoEncontradoError(f"Artículo '{clave}' no encontrado en el mapa.")
        pagina = self._mapa[clave]
        return max(0, min(pagina, self._total_paginas - 1)) if self._total_paginas > 0 else 0

    def pagina_anterior(self, pagina: int) -> int:
        return max(0, pagina - 1)

    def pagina_siguiente(self, pagina: int) -> int:
        return min(self._total_paginas - 1, pagina + 1) if self._total_paginas > 0 else 0

    def articulos_en_pagina(self, pagina: int) -> list[str]:
        if not self._mapa:
            return []
        return [k for k, v in self._mapa.items() if v == pagina]

    def renderizar_pagina(self, pagina: int, zoom: float = 2.0) -> PaginaRenderizada:
        if self._doc is None:
            raise PDFNoCaregadoError("No hay PDF cargado.")
        if pagina < 0 or pagina >= self._total_paginas:
            raise PDFNoCaregadoError(f"Página {pagina} fuera de rango.")

        if pagina in self._cache:
            return self._cache[pagina]

        page = self._doc.load_page(pagina)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)

        if Image is not None:
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        else:
            img = pix.tobytes("png")

        resultado = PaginaRenderizada(imagen=img)

        if len(self._cache) >= self._cache_size:
            self._cache.clear()
        self._cache[pagina] = resultado
        return resultado
