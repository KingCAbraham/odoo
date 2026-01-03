# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    # -------------------------
    # Provider
    # -------------------------
    ai_chatbot_modern_provider = fields.Selection(
        selection=[("openai", "OpenAI"), ("groq", "Groq")],
        string="Proveedor",
        default="groq",
        config_parameter="ai_chatbot_modern.provider",
    )

    # -------------------------
    # OpenAI settings
    # -------------------------
    ai_chatbot_modern_openai_api_key = fields.Char(
        string="OpenAI API Key",
        config_parameter="ai_chatbot_modern.openai_api_key",
    )

    ai_chatbot_modern_openai_chat_model = fields.Char(
        string="Modelo de chat (OpenAI)",
        default="gpt-4o-mini",
        config_parameter="ai_chatbot_modern.openai_chat_model",
    )

    ai_chatbot_modern_openai_embed_model = fields.Char(
        string="Modelo de embeddings (OpenAI)",
        default="text-embedding-3-small",
        config_parameter="ai_chatbot_modern.openai_embed_model",
    )

    # -------------------------
    # Groq settings
    # -------------------------
    ai_chatbot_modern_groq_api_key = fields.Char(
        string="Groq API Key",
        config_parameter="ai_chatbot_modern.groq_api_key",
    )

    ai_chatbot_modern_groq_chat_model = fields.Char(
        string="Modelo de chat (Groq)",
        # Pon aquí el modelo que realmente estés usando en Groq
        default="llama-3.1-8b-instant",
        config_parameter="ai_chatbot_modern.groq_chat_model",
    )

    # NOTA IMPORTANTE:
    # Groq normalmente es para chat/completions, y NO siempre ofrece embeddings.
    # Si tu implementación NO usa embeddings de Groq, puedes dejar esto vacío y tu código
    # debe caer a OpenAI embeddings o a un modo "sin RAG embeddings" (según lo que decidamos).
    ai_chatbot_modern_groq_embed_model = fields.Char(
        string="Modelo de embeddings (Groq)",
        default="",
        config_parameter="ai_chatbot_modern.groq_embed_model",
    )

    # -------------------------
    # RAG
    # -------------------------
    ai_chatbot_modern_rag_top_k = fields.Integer(
        string="Top K (RAG)",
        default=5,
        config_parameter="ai_chatbot_modern.rag_top_k",
    )
