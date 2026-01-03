import base64
import re
from odoo import fields, models
from odoo.exceptions import UserError

def _chunk_text(text: str, chunk_size=900, overlap=120):
    """
    Divide el texto en fragmentos (chunks) de tamaño fijo con solapamiento.
    """
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
    _name = "ai_chatbot_modern.document"
    _description = "Documento para RAG"
    _rec_name = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    file = fields.Binary(string="Archivo", attachment=True, required=True)
    filename = fields.Char(string="Nombre de archivo")
    chunk_ids = fields.One2many("ai_chatbot_modern.document.chunk",
                                "document_id",
                                string="Chunks")
    def toggle_active(self):
        for rec in self:
            rec.active = not rec.active


    def action_index(self):
        """
        Extrae texto, genera chunks y crea embeddings para todos los chunks.
        """
        self.ensure_one()
        text = self._extract_text()
        chunks = _chunk_text(text)
        if not chunks:
            raise UserError(
                "No se pudo extraer texto. Sube un archivo TXT o PDF con texto seleccionable.")

        # Elimina chunks previos
        self.chunk_ids.unlink()

        # Crea nuevos chunks
        Chunk = self.env["ai_chatbot_modern.document.chunk"].sudo()
        for idx, ch in enumerate(chunks, start=1):
            Chunk.create({
                "document_id": self.id,
                "sequence": idx,
                "content": ch,
            })

        # Genera embeddings (según proveedor)
        self.env["ai_chatbot_modern.rag"].sudo()._embed_all_chunks(self.id)
        return True

    def _extract_text(self):
        """
        Extrae texto de archivos TXT o PDF. Lanza UserError para formatos no soportados.
        """
        self.ensure_one()
        raw = base64.b64decode(self.file or b"")
        name = (self.filename or "").lower().strip()

        # TXT
        if name.endswith(".txt"):
            try:
                return raw.decode("utf-8", errors="ignore")
            except Exception:
                return raw.decode("latin-1", errors="ignore")

        # PDF
        if name.endswith(".pdf"):
            try:
                from pypdf import PdfReader
            except Exception:
                raise UserError("Falta pypdf. Instala: pip install pypdf")

            import io
            reader = PdfReader(io.BytesIO(raw))
            text_parts = []
            for page in reader.pages:
                text_parts.append(page.extract_text() or "")
            return "\n".join(text_parts).strip()


        raise UserError("Formato no soportado. Usa TXT o PDF.")

class ChatbotDocumentChunk(models.Model):
    _name = "ai_chatbot_modern.document.chunk"
    _description = "Fragmento de documento"
    _order = "sequence asc, id asc"

    document_id = fields.Many2one("ai_chatbot_modern.document", required=True, ondelete="cascade")
    sequence = fields.Integer(default=1)
    content = fields.Text(required=True)
    embedding = fields.Json(string="Embedding")
