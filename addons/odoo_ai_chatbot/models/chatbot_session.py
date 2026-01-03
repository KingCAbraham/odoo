# models/chatbot_session.py
# ------------------------------------------------------------
# Chat sessions + RAG service for Odoo AI Chatbot
# - OpenAI: embeddings + vector RAG
# - Groq: chat; embeddings optional; if not available -> lexical RAG fallback
# ------------------------------------------------------------

import json
import re
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


class _EmbeddingsUnavailable(Exception):
    """Internal exception used to trigger lexical fallback."""
    pass


class ChatbotRag(models.AbstractModel):
    _name = "odoo_ai_chatbot.rag"
    _description = "Servicios RAG"

    # -------------------------
    # Settings / Params
    # -------------------------
    def _get_param(self, key, default=None):
        return self.env["ir.config_parameter"].sudo().get_param(key, default)

    def _get_provider(self):
        """
        Priority:
        1) If odoo_ai_chatbot.provider is set to openai/groq, use it.
        2) Else autodetect by API key prefix:
           - Groq keys usually start with "gsk_"
        3) Else default to openai
        """
        p = (self._get_param("odoo_ai_chatbot.provider", "") or "").strip().lower()
        if p in ("openai", "groq"):
            return p

        openai_key = self._get_param("odoo_ai_chatbot.openai_api_key", "") or ""
        groq_key = self._get_param("odoo_ai_chatbot.groq_api_key", "") or ""

        # If user pasted Groq key into the OpenAI field
        if openai_key.startswith("gsk_"):
            return "groq"
        if groq_key.startswith("gsk_"):
            return "groq"

        # If only groq key exists, assume groq
        if groq_key and not openai_key:
            return "groq"

        return "openai"

    def _get_api_key(self, provider: str) -> str:
        """
        Reads API key from system params.

        - OpenAI: odoo_ai_chatbot.openai_api_key
        - Groq : odoo_ai_chatbot.groq_api_key
          (but also accepts Groq key accidentally stored in openai_api_key)
        """
        openai_key = self._get_param("odoo_ai_chatbot.openai_api_key", "") or ""
        groq_key = self._get_param("odoo_ai_chatbot.groq_api_key", "") or ""

        if provider == "groq":
            api_key = groq_key or openai_key
        else:
            api_key = openai_key

        if not api_key:
            raise UserError(
                f"Configura tu API Key en Ajustes > Configuración general. (Proveedor: {provider.upper()})"
            )
        return api_key

    # -------------------------
    # Clients
    # -------------------------
    def _get_client(self):
        provider = self._get_provider()
        api_key = self._get_api_key(provider)

        if provider == "openai":
            try:
                from openai import OpenAI
            except Exception:
                raise UserError("Falta dependencia 'openai'. Instala en tu venv: pip install openai")
            return OpenAI(api_key=api_key), provider

        if provider == "groq":
            try:
                from groq import Groq
            except Exception:
                raise UserError("Falta dependencia 'groq'. Instala en tu venv: pip install groq")
            return Groq(api_key=api_key), provider

        raise UserError("Proveedor desconocido. Usa odoo_ai_chatbot.provider = openai | groq")

    # -------------------------
    # Helpers
    # -------------------------
    def _tokenize(self, text: str):
        return re.findall(r"[a-z0-9áéíóúñ]+", (text or "").lower())

    def _cosine_sim(self, q_vec, v_vec) -> float:
        q = np.array(q_vec, dtype=np.float32)
        v = np.array(v_vec, dtype=np.float32)
        q_norm = np.linalg.norm(q) + 1e-9
        v_norm = np.linalg.norm(v) + 1e-9
        return float(np.dot(q, v) / (q_norm * v_norm))

    def _ensure_list_embedding(self, emb):
        """Ensure embedding becomes a python list[float] or raise."""
        if emb is None:
            raise ValueError("Embedding is None")

        if isinstance(emb, list):
            return emb

        if isinstance(emb, str):
            # could be JSON string
            try:
                loaded = json.loads(emb)
                if isinstance(loaded, list):
                    return loaded
            except Exception:
                pass

        raise ValueError("Embedding is not a list/json-list")

    # -------------------------
    # Embeddings
    # -------------------------
    def embed_text(self, text: str):
        """
        Returns embedding as list[float].
        - OpenAI: uses client.embeddings.create
        - Groq : tries embeddings if SDK supports; otherwise raises _EmbeddingsUnavailable
        """
        client, provider = self._get_client()

        if provider == "openai":
            model = self._get_param("odoo_ai_chatbot.openai_embed_model", "text-embedding-3-small")
            try:
                resp = client.embeddings.create(model=model, input=text)
                emb = resp.data[0].embedding
                return self._ensure_list_embedding(emb)
            except Exception as e:
                name = e.__class__.__name__
                msg = str(e)
                if "RateLimit" in name or "429" in msg or "insufficient_quota" in msg:
                    raise UserError("OpenAI respondió 429 (sin cuota / sin billing). Revisa tu plan y Billing.")
                raise UserError(f"Error generando embedding con OpenAI: {msg}")

        # Groq path
        # Many setups will NOT have embeddings; we must not crash the app -> trigger fallback.
        if not hasattr(client, "embeddings"):
            raise _EmbeddingsUnavailable("Groq SDK no expone embeddings en este entorno.")

        model = self._get_param("odoo_ai_chatbot.groq_embed_model", "") or ""
        if not model:
            # If user didn't configure an embeddings model for groq, fallback.
            raise _EmbeddingsUnavailable(
                "No hay modelo de embeddings configurado para Groq (odoo_ai_chatbot.groq_embed_model)."
            )

        try:
            # Some clients expect input as list
            resp = client.embeddings.create(model=model, input=[text])
            emb = None
            if getattr(resp, "data", None):
                emb = resp.data[0].embedding
            elif isinstance(resp, dict) and resp.get("data"):
                emb = resp["data"][0].get("embedding")
            return self._ensure_list_embedding(emb)
        except Exception as e:
            # If embeddings fail for any reason, fallback (don’t crash chat)
            raise _EmbeddingsUnavailable(f"Embeddings Groq no disponibles / error: {e}")

    def _embed_all_chunks(self, document_id: int):
        """
        Index-time embedding creation.
        - OpenAI: computes embeddings
        - Groq : best-effort; if unavailable, leaves embeddings empty (lexical fallback will still work)
        """
        Chunk = self.env["odoo_ai_chatbot.document.chunk"].sudo()
        chunks = Chunk.search([("document_id", "=", document_id)])

        # Compute embeddings only if possible; do not crash on Groq.
        for ch in chunks:
            if ch.embedding:
                continue
            try:
                ch.embedding = self.embed_text(ch.content or "")
            except _EmbeddingsUnavailable:
                # Leave empty; retrieval will fallback to lexical
                continue
            except UserError:
                # For OpenAI quota/billing etc, bubble up so user knows.
                raise
            except Exception as e:
                # Don’t hard crash: give a readable message.
                raise UserError(f"No se pudieron generar embeddings para chunks: {e}")

    # -------------------------
    # Retrieval
    # -------------------------
    def _retrieve_lexical(self, query: str, top_k=5):
        """
        Simple keyword overlap retrieval:
        counts matched tokens and returns top_k chunks.
        This is the fallback when embeddings are unavailable.
        """
        tokens = set(self._tokenize(query))
        if not tokens:
            return []

        Chunk = self.env["odoo_ai_chatbot.document.chunk"].sudo()
        # limit for performance
        chunks = Chunk.search([("document_id.active", "=", True)], limit=800)

        scored = []
        for ch in chunks:
            text = ch.content or ""
            dtokens = self._tokenize(text)
            if not dtokens:
                continue
            score = sum(1 for t in dtokens if t in tokens)
            if score > 0:
                scored.append((float(score), ch))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def _retrieve_vector(self, query_emb, top_k=5):
        Chunk = self.env["odoo_ai_chatbot.document.chunk"].sudo()
        chunks = Chunk.search([("document_id.active", "=", True)])

        scored = []
        for ch in chunks:
            if not ch.embedding:
                continue
            try:
                v = self._ensure_list_embedding(ch.embedding)
                sim = self._cosine_sim(query_emb, v)
                scored.append((sim, ch))
            except Exception:
                continue

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[:top_k]

    def retrieve(self, query: str, top_k=5):
        """
        Tries vector retrieval; if embeddings are unavailable or yield no hits,
        fallback to lexical retrieval.
        """
        try:
            q_emb = self.embed_text(query)
            hits = self._retrieve_vector(q_emb, top_k=top_k)
            if hits:
                return hits
        except _EmbeddingsUnavailable:
            pass

        # Fallback lexical
        return self._retrieve_lexical(query, top_k=top_k)

    # -------------------------
    # Chat (LLM)
    # -------------------------
    def chat(self, messages):
        client, provider = self._get_client()

        if provider == "openai":
            model = self._get_param("odoo_ai_chatbot.openai_chat_model", "gpt-4o-mini")
        else:
            # Set a safe default, but user should configure it in settings
            model = self._get_param("odoo_ai_chatbot.groq_chat_model", "llama-3.1-8b-instant")

        try:
            resp = client.chat.completions.create(model=model, messages=messages)

            # Extract text (works for OpenAI-like responses)
            if getattr(resp, "choices", None):
                choice = resp.choices[0]
                if getattr(choice, "message", None) and getattr(choice.message, "content", None):
                    return choice.message.content
                if getattr(choice, "text", None):
                    return choice.text

            if isinstance(resp, dict) and resp.get("choices"):
                c = resp["choices"][0]
                if isinstance(c, dict):
                    if "message" in c and isinstance(c["message"], dict) and c["message"].get("content"):
                        return c["message"]["content"]
                    if c.get("text"):
                        return c["text"]

            raise UserError("No se pudo obtener texto de respuesta del proveedor de IA.")
        except Exception as e:
            msg = str(e)
            if "401" in msg or "Unauthorized" in msg:
                raise UserError("API Key inválida o sin permisos.")
            if "RateLimit" in e.__class__.__name__ or "429" in msg:
                raise UserError("El proveedor respondió 429 (rate limit / cuota). Revisa tu plan o espera un momento.")
            raise UserError(f"Error llamando al modelo ({provider}): {msg}")

    # -------------------------
    # RAG Answer
    # -------------------------
    def answer_with_rag(self, question: str):
        top_k = int(self._get_param("odoo_ai_chatbot.rag_top_k", 5))
        hits = self.retrieve(question, top_k=top_k)

        # show some chunk context
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
