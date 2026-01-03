# -*- coding: utf-8 -*-
import re
import hashlib
import numpy as np

from odoo import api, fields, models
from odoo.exceptions import UserError


class ChatbotSession(models.Model):
    _name = "odoo_ai_chatbot.session"
    _description = "Sesión de Chatbot"
    _rec_name = "name"

    name = fields.Char(default="Chat")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    message_ids = fields.One2many("odoo_ai_chatbot.message", "session_id", string="Mensajes")


class ChatbotMessage(models.Model):
    _name = "odoo_ai_chatbot.message"
    _description = "Mensaje de Chatbot"
    _order = "id asc"

    session_id = fields.Many2one("odoo_ai_chatbot.session", required=True, ondelete="cascade")
    role = fields.Selection([("user", "Usuario"), ("assistant", "Asistente")], required=True)
    content = fields.Text(required=True)


class ChatbotRag(models.AbstractModel):
    _name = "odoo_ai_chatbot.rag"
    _description = "Servicios RAG"

    # -------------------------
    # Helpers de configuración
    # -------------------------
    def _get_param(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _get_provider(self):
        return self._get_param("odoo_ai_chatbot.provider", "groq")  # default groq

    def _get_api_key(self, provider):
        key_map = {
            "openai": "odoo_ai_chatbot.openai_api_key",
            "groq": "odoo_ai_chatbot.groq_api_key",
        }
        param_key = key_map.get(provider)
        api_key = self._get_param(param_key) if param_key else None
        if not api_key:
            raise UserError(f"Configura tu {provider.upper()} API Key en Ajustes > Configuración general.")
        return api_key

    def _get_chat_model(self, provider):
        if provider == "openai":
            return self._get_param("odoo_ai_chatbot.openai_chat_model", "gpt-4o-mini")
        if provider == "groq":
            # modelos típicos en Groq: llama-3.1-8b-instant, llama-3.3-70b-versatile, etc.
            return self._get_param("odoo_ai_chatbot.groq_chat_model", "llama-3.1-8b-instant")
        raise UserError("Proveedor desconocido en odoo_ai_chatbot.provider")

    def _get_openai_clients(self):
        # Import lazy (para que no truene si solo usas Groq)
        try:
            from openai import OpenAI
        except Exception:
            raise UserError("Falta dependencia 'openai'. Instala: pip install openai")

        api_key = self._get_api_key("openai")
        client = OpenAI(api_key=api_key)
        return client

    def _get_groq_client(self):
        # Import lazy (para que no truene si solo usas OpenAI)
        try:
            from groq import Groq
        except Exception:
            raise UserError("Falta dependencia 'groq'. Instala: pip install groq")

        api_key = self._get_api_key("groq")
        client = Groq(api_key=api_key)
        return client

    # -------------------------
    # Embeddings (OpenAI remoto / Groq local)
    # -------------------------
    def _stable_hash_embedding(self, text: str, dim: int = 512):
        """
        Embedding local por feature hashing estable.
        - No requiere librerías extra
        - Es estable entre reinicios (no usa hash() de Python)
        """
        text = (text or "").strip().lower()
        if not text:
            return [0.0] * dim

        tokens = re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
        v = np.zeros(dim, dtype=np.float32)

        for tok in tokens:
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h, "big") % dim
            v[idx] += 1.0

        norm = float(np.linalg.norm(v) + 1e-9)
        v = v / norm
        return [float(x) for x in v.tolist()]

    def embed_text(self, text: str):
        provider = self._get_provider()

        # OpenAI embeddings (remoto)
        if provider == "openai":
            client = self._get_openai_clients()
            model = self._get_param("odoo_ai_chatbot.openai_embed_model", "text-embedding-3-small")
            try:
                resp = client.embeddings.create(model=model, input=text)
                emb = resp.data[0].embedding if getattr(resp, "data", None) else None
                if not emb:
                    raise UserError("OpenAI no devolvió embedding.")
                return emb
            except Exception as e:
                s = str(e)
                if "429" in s or "insufficient_quota" in s:
                    raise UserError("OpenAI respondió 429 (sin cuota / sin billing). Revisa tu plan y Billing.")
                if "timeout" in s.lower() or "timed out" in s.lower():
                    raise UserError("Timeout al contactar OpenAI. Intenta de nuevo.")
                raise

        # Groq embeddings (LOCAL)
        if provider == "groq":
            # Groq lo usamos para chat; para RAG hacemos embeddings locales para que funcione siempre.
            return self._stable_hash_embedding(text, dim=512)

        raise UserError("Proveedor desconocido en odoo_ai_chatbot.provider")

    # -------------------------
    # Chat (OpenAI o Groq)
    # -------------------------
    def chat(self, messages):
        provider = self._get_provider()
        model = self._get_chat_model(provider)

        try:
            if provider == "openai":
                client = self._get_openai_clients()
                resp = client.chat.completions.create(model=model, messages=messages)
            elif provider == "groq":
                client = self._get_groq_client()
                resp = client.chat.completions.create(model=model, messages=messages)
            else:
                raise UserError("Proveedor desconocido para chat.")
        except Exception as e:
            s = str(e)
            if "429" in s or "rate" in s.lower():
                raise UserError("El proveedor respondió RateLimit/429. Revisa tu cuota, plan o límites.")
            if "timeout" in s.lower() or "timed out" in s.lower():
                raise UserError("Timeout al contactar el proveedor. Intenta de nuevo.")
            raise

        # Extraer texto de respuesta (forma típica OpenAI/Groq)
        if getattr(resp, "choices", None):
            msg = resp.choices[0].message
            return msg.content if msg and getattr(msg, "content", None) else ""

        # fallback dict
        if isinstance(resp, dict) and resp.get("choices"):
            c = resp["choices"][0]
            if isinstance(c, dict) and c.get("message") and c["message"].get("content"):
                return c["message"]["content"]

        raise UserError("No se pudo obtener texto de respuesta del proveedor.")

    # -------------------------
    # RAG
    # -------------------------
    def _embed_all_chunks(self, document_id):
        Chunk = self.env["odoo_ai_chatbot.document.chunk"]
        chunks = Chunk.search([("document_id", "=", document_id)])
        for ch in chunks:
            if not ch.embedding:
                ch.embedding = self.embed_text(ch.content)

    def retrieve(self, query: str, top_k=5):
        q_emb = self.embed_text(query)
        q = np.array(q_emb, dtype=np.float32)
        q_norm = float(np.linalg.norm(q) + 1e-9)

        Chunk = self.env["odoo_ai_chatbot.document.chunk"]
        chunks = Chunk.search([("document_id.active", "=", True)])
        scored = []

        for ch in chunks:
            if not ch.embedding:
                continue
            v = np.array(ch.embedding, dtype=np.float32)
            if v.shape != q.shape:
                # si por alguna razón cambió dimensión, ignora
                continue
            sim = float(np.dot(q, v) / (q_norm * (float(np.linalg.norm(v)) + 1e-9)))
            scored.append((sim, ch))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def answer_with_rag(self, question: str):
        top_k = int(self._get_param("odoo_ai_chatbot.rag_top_k", 5))
        hits = self.retrieve(question, top_k=top_k)

        context = "\n\n".join([f"- {ch.content}" for _, ch in hits]) if hits else ""

        system = (
            "Eres un asistente dentro de Odoo. "
            "Responde SOLO con base en el contexto proporcionado. "
            "Si no está en el contexto, responde: "
            "'No tengo esa información en los documentos cargados.' "
            "Responde en español, claro y directo."
        )
        user = f"CONTEXTO:\n{context if context else 'SIN CONTEXTO'}\n\nPREGUNTA:\n{question}"

        return self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
