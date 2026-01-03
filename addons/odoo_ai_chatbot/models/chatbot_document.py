# models/chatbot_document.py
# ------------------------------------------------------------
# Documents + chunking + indexing for RAG
# Supports: TXT, PDF (text-selectable)
# ------------------------------------------------------------

import base64
import re
from odoo import fields, models
from odoo.exceptions import UserError


def _chunk_text(text: str, chunk_size=900, overlap=120):
    text = re.sub(r"\s+", " ", (text or "")).strip()
    if not text:
        return []
    chunks = []
    i = 0
    while i < len(text):
        chunks.append(text[i:i + chunk_size])
        i += max(1, chunk_size - overlap)
    return chunks


class ChatbotDocument(models.Model):
    _name = "odoo_ai_chatbot.document"
    _description = "Documento para RAG"
    _rec_name = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    file = fields.Binary(string="Archivo", attachment=True, required=True)
    filename = fields.Char(string="Nombre de archivo")

    chunk_ids = fields.One2many("odoo_ai_chatbot.document.chunk", "document_id", string="Chunks")

    def action_index(self):
        """
        1) Extract text
        2) Chunk it
        3) Store chunks
        4) Try to create embeddings (best-effort; Groq may fallback to lexical later)
        """
        self.ensure_one()

        text = self._extract_text()
        chunks = _chunk_text(text)

        if not chunks:
            raise UserError("No pude extraer texto. Sube TXT o PDF con texto seleccionable.")

        # Recreate chunks
        self.chunk_ids.unlink()

        Chunk = self.env["odoo_ai_chatbot.document.chunk"].sudo()
        for idx, ch in enumerate(chunks, start=1):
            Chunk.create({
                "document_id": self.id,
                "sequence": idx,
                "content": ch,
            })

        # Create embeddings (best-effort; may be skipped if embeddings unavailable)
        self.env["odoo_ai_chatbot.rag"].sudo()._embed_all_chunks(self.id)
        return True

    def _extract_text(self):
        self.ensure_one()
        raw = base64.b64decode(self.file or b"")
        name = (self.filename or "").lower().strip()

        if name.endswith(".txt"):
            try:
                return raw.decode("utf-8", errors="ignore")
            except Exception:
                return raw.decode("latin-1", errors="ignore")

        if name.endswith(".pdf"):
            try:
                from pdfminer.high_level import extract_text
            except Exception:
                raise UserError("Falta pdfminer.six. Instálalo en tu venv: pip install pdfminer.six")

            import tempfile
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as f:
                f.write(raw)
                f.flush()
                return extract_text(f.name) or ""

        raise UserError("Formato no soportado. Usa TXT o PDF.")


class ChatbotDocumentChunk(models.Model):
    _name = "odoo_ai_chatbot.document.chunk"
    _description = "Chunk de documento"

    document_id = fields.Many2one("odoo_ai_chatbot.document", required=True, ondelete="cascade")
    sequence = fields.Integer(default=1)
    content = fields.Text(required=True)

    # stores list[float] when available (OpenAI embeddings),
    # or stays empty when embeddings are unavailable (Groq fallback lexical).
    embedding = fields.Json(string="Embedding")
