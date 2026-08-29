"""Chatbot RAG para el analista.

Base de conocimiento: documentos de política en `rag/politicas/`. Pipeline:
chunking -> recuperación (TF-IDF como baseline local; embeddings + índice
vectorial en la versión final) -> respuesta del LLM anclada al contexto y con
cita de la sección.

Fallback explícito: si ningún fragmento es relevante, el asistente lo dice y no
inventa.
"""

from __future__ import annotations

import re
from pathlib import Path

from casino_ia.config import LLM, RAG_DOCS

_SYS = """Eres un asistente para analistas de un casino. Respondes SOLO con la
información de los fragmentos de política que se te pasan. Cita la sección.
Si la respuesta no está en los fragmentos, di exactamente:
"No encuentro esa información en las políticas cargadas." No inventes.
"""


def _trocear(texto: str, fuente: str) -> list[dict]:
    bloques = re.split(r"\n(?=#{1,3}\s)", texto)
    return [{"fuente": fuente, "texto": b.strip()} for b in bloques if b.strip()]


class AsistentePoliticas:
    def __init__(self, carpeta: Path | None = None):
        self.carpeta = carpeta or RAG_DOCS
        self.chunks: list[dict] = []
        for md in sorted(self.carpeta.glob("*.md")):
            self.chunks.extend(_trocear(md.read_text(encoding="utf-8"), md.name))
        self._fit()

    def _fit(self):
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer

            self._vec = TfidfVectorizer(strip_accents="unicode")
            self._mat = self._vec.fit_transform([c["texto"] for c in self.chunks]) if self.chunks else None
        except Exception:  # pragma: no cover
            self._vec = self._mat = None

    def recuperar(self, pregunta: str, k: int = 3) -> list[dict]:
        if not self.chunks:
            return []
        if self._mat is None:
            palabras = set(pregunta.lower().split())
            puntuados = sorted(
                self.chunks,
                key=lambda c: len(palabras & set(c["texto"].lower().split())),
                reverse=True,
            )
            return puntuados[:k]
        from sklearn.metrics.pairwise import cosine_similarity

        sims = cosine_similarity(self._vec.transform([pregunta]), self._mat)[0]
        idx = sims.argsort()[::-1][:k]
        return [self.chunks[i] | {"score": round(float(sims[i]), 3)} for i in idx if sims[i] > 0.05]

    def responder(self, pregunta: str) -> dict:
        contexto = self.recuperar(pregunta)
        if not contexto:
            return {"respuesta": "No encuentro esa información en las políticas cargadas.", "fuentes": []}

        bloque = "\n\n---\n\n".join(f"[{c['fuente']}]\n{c['texto']}" for c in contexto)
        if not LLM.enabled:
            return {
                "respuesta": (
                    "Fragmentos de política relevantes (respuesta del LLM no disponible "
                    "sin ANTHROPIC_API_KEY):\n\n" + bloque
                ),
                "fuentes": [c["fuente"] for c in contexto],
            }
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=LLM.api_key)
            msg = client.messages.create(
                model=LLM.model,
                max_tokens=LLM.max_tokens,
                system=_SYS,
                messages=[{"role": "user", "content": f"Fragmentos:\n{bloque}\n\nPregunta: {pregunta}"}],
            )
            return {"respuesta": msg.content[0].text, "fuentes": [c["fuente"] for c in contexto]}
        except Exception:  # noqa: BLE001
            return {"respuesta": bloque, "fuentes": [c["fuente"] for c in contexto]}
