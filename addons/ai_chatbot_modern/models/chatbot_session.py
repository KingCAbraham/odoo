# -*- coding: utf-8 -*-
import re
import hashlib
from odoo import api, fields, models
from odoo.exceptions import UserError


class ChatbotSession(models.Model):
    _name = "ai_chatbot_modern.session"
    _description = "Sesión de Chatbot"
    _rec_name = "name"

    name = fields.Char(default="Chat")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company, required=True)
    message_ids = fields.One2many("ai_chatbot_modern.message", "session_id", string="Mensajes")

    # ---------------------------------------------------------------------
    # RPC para el Frontend (JS Client Action)
    # ---------------------------------------------------------------------
    @api.model
    def get_or_create_session(self):
        """Devuelve una sesión por usuario/compañía (crea si no existe)."""
        sess = self.search(
            [("user_id", "=", self.env.user.id), ("company_id", "=", self.env.company.id)],
            limit=1,
            order="id desc",
        )
        if not sess:
            sess = self.create({
                "name": "Chat",
                "user_id": self.env.user.id,
                "company_id": self.env.company.id,
            })
        return sess.id

    def rpc_get_messages(self, session_id=None):
        """Devuelve historial de mensajes para pintar el chat."""
        if session_id:
            sess = self.browse(int(session_id)).exists()
        else:
            self.ensure_one()
            sess = self

        if not sess:
            return []

        # Seguridad básica: solo dueño o admin
        if sess.user_id.id != self.env.user.id and not self.env.user.has_group("base.group_system"):
            raise UserError("No tienes permiso para ver esta sesión.")

        return [
            {"role": m.role, "content": m.content}
            for m in sess.message_ids.sorted("id")
        ]

    @api.model
    def rpc_send_message(self, session_id, content):
        """Guarda mensaje del usuario, ejecuta RAG y guarda respuesta."""
        content = (content or "").strip()
        if not content:
            return {"answer": ""}

        sess = self.browse(int(session_id)).exists()
        if not sess:
            raise UserError("Sesión no encontrada.")

        # Seguridad básica: solo dueño o admin
        if sess.user_id.id != self.env.user.id and not self.env.user.has_group("base.group_system"):
            raise UserError("No tienes permiso para usar esta sesión.")

        # Mensaje del usuario
        self.env["ai_chatbot_modern.message"].create({
            "session_id": sess.id,
            "role": "user",
            "content": content,
        })

        # Respuesta con RAG
        answer = self.env["ai_chatbot_modern.rag"].answer_with_rag(content)

        # Mensaje del asistente
        self.env["ai_chatbot_modern.message"].create({
            "session_id": sess.id,
            "role": "assistant",
            "content": answer,
        })

        return {"answer": answer}


class ChatbotMessage(models.Model):
    _name = "ai_chatbot_modern.message"
    _description = "Mensaje de Chatbot"
    _order = "id asc"

    session_id = fields.Many2one("ai_chatbot_modern.session", required=True, ondelete="cascade")
    role = fields.Selection([("user", "Usuario"), ("assistant", "Asistente")], required=True)
    content = fields.Text(required=True)


class ChatbotRag(models.AbstractModel):
    _name = "ai_chatbot_modern.rag"
    _description = "Servicios RAG para AI Chatbot Modern"

    # ---------------------------------------------------------------------
    # Helpers config
    # ---------------------------------------------------------------------
    def _get_param(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _get_provider(self):
        # openai | groq
        return (self._get_param("ai_chatbot_modern.provider", "groq") or "groq").strip()

    def _get_api_key(self, provider: str):
        key_map = {
            "openai": "ai_chatbot_modern.openai_api_key",
            "groq": "ai_chatbot_modern.groq_api_key",
        }
        param = key_map.get(provider)
        api_key = (self._get_param(param) if param else None) or ""
        api_key = api_key.strip()
        if not api_key:
            raise UserError(f"Configura tu {provider.upper()} API Key en Ajustes > Configuración general.")
        return api_key

    def _get_chat_model(self, provider: str):
        if provider == "openai":
            return self._get_param("ai_chatbot_modern.openai_chat_model", "gpt-4o-mini")
        if provider == "groq":
            return self._get_param("ai_chatbot_modern.groq_chat_model", "llama-3.1-8b-instant")
        raise UserError("Proveedor desconocido en AI Chatbot Modern")

    # ---------------------------------------------------------------------
    # Clients
    # ---------------------------------------------------------------------
    def _get_openai_client(self):
        try:
            from openai import OpenAI
        except Exception:
            raise UserError("Falta dependencia 'openai'. Instala: pip install openai")
        return OpenAI(api_key=self._get_api_key("openai"))

    def _get_groq_client(self):
        try:
            from groq import Groq
        except Exception:
            raise UserError("Falta dependencia 'groq'. Instala: pip install groq")
        return Groq(api_key=self._get_api_key("groq"))

    # ---------------------------------------------------------------------
    # Embeddings
    # ---------------------------------------------------------------------
    def _stable_hash_embedding(self, text: str, dim: int = 512):
        """
        Embedding local (fallback) por hashing estable.
        Sirve para RAG cuando el proveedor NO da embeddings (Groq).
        """
        text = (text or "").strip().lower()
        if not text:
            return [0.0] * dim

        tokens = re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)
        vec = [0.0] * dim

        for tok in tokens:
            h = hashlib.blake2b(tok.encode("utf-8"), digest_size=8).digest()
            idx = int.from_bytes(h, "big") % dim
            vec[idx] += 1.0

        norm = sum(x * x for x in vec) ** 0.5
        if norm < 1e-9:
            return vec
        return [x / norm for x in vec]

    def embed_text(self, text: str):
        provider = self._get_provider()

        if provider == "openai":
            client = self._get_openai_client()
            model = self._get_param("ai_chatbot_modern.openai_embed_model", "text-embedding-3-small")
            try:
                resp = client.embeddings.create(model=model, input=text)
                emb = None
                if getattr(resp, "data", None):
                    emb = resp.data[0].embedding
                if not emb:
                    raise UserError("OpenAI no devolvió embedding.")
                return emb
            except Exception as e:
                s = str(e)
                if "429" in s or "insufficient_quota" in s or "RateLimit" in s:
                    raise UserError("OpenAI respondió 429 (sin cuota / sin billing). Revisa Billing / Plan.")
                raise UserError(f"Error al generar embedding con OpenAI: {e}")

        if provider == "groq":
            return self._stable_hash_embedding(text, dim=512)

        raise UserError("Proveedor desconocido en AI Chatbot Modern")

    # ---------------------------------------------------------------------
    # Chat
    # ---------------------------------------------------------------------
    def chat(self, messages):
        provider = self._get_provider()
        model = self._get_chat_model(provider)

        try:
            if provider == "openai":
                client = self._get_openai_client()
                resp = client.chat.completions.create(model=model, messages=messages)
            elif provider == "groq":
                client = self._get_groq_client()
                resp = client.chat.completions.create(model=model, messages=messages)
            else:
                raise UserError("Proveedor desconocido en AI Chatbot Modern")
        except Exception as e:
            s = str(e)
            if "401" in s or "invalid_api_key" in s or "Unauthorized" in s:
                raise UserError(f"API Key inválida para {provider.upper()} (401).")
            if "429" in s or "RateLimit" in s:
                raise UserError(f"{provider.upper()} respondió 429 (rate limit/cuota). Intenta luego.")
            raise UserError(f"Error al invocar el modelo ({provider}): {e}")

        if getattr(resp, "choices", None):
            msg = resp.choices[0].message
            return (msg.content or "").strip() if msg else ""
        if isinstance(resp, dict) and resp.get("choices"):
            c = resp["choices"][0]
            if isinstance(c, dict) and c.get("message") and c["message"].get("content"):
                return (c["message"]["content"] or "").strip()

        raise UserError("No se pudo obtener texto de respuesta del proveedor.")

    # ---------------------------------------------------------------------
    # RAG
    # ---------------------------------------------------------------------
    def _cosine(self, a, b):
        if not a or not b or len(a) != len(b):
            return None
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(y * y for y in b) ** 0.5
        denom = (na * nb) + 1e-9
        return float(dot / denom)

    def retrieve(self, query: str, top_k=5):
        q_emb = self.embed_text(query)

        Chunk = self.env["ai_chatbot_modern.document.chunk"]
        chunks = Chunk.search([("document_id.active", "=", True)])

        scored = []
        for ch in chunks:
            if not ch.embedding:
                continue
            sim = self._cosine(q_emb, ch.embedding)
            if sim is None:
                continue
            scored.append((sim, ch))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def answer_with_rag(self, question: str):
        top_k = int(self._get_param("ai_chatbot_modern.rag_top_k", 5))
        hits = self.retrieve(question, top_k=top_k)

        if not hits:
            return "No tengo esa información en los documentos cargados."

        context = "\n\n".join([f"- {ch.content}" for _, ch in hits])

        system = (
            "Eres un asistente dentro de Odoo. "
            "Responde SOLO con base en el contexto proporcionado. "
            "Si no está en el contexto, responde exactamente: "
            "'No tengo esa información en los documentos cargados.' "
            "Responde en español, claro y directo."
        )
        user = f"CONTEXTO:\n{context}\n\nPREGUNTA:\n{question}"

        return self.chat([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
