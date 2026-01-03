# Settings for the AI chatbot configuration
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    provider = fields.Selection(
        selection=[('openai', 'OpenAI'), ('groq', 'Groq')],
        string="Proveedor",
        default='openai',
        config_parameter="odoo_ai_chatbot.provider",
    )

    openai_api_key = fields.Char(
        string="OpenAI API Key",
        config_parameter="odoo_ai_chatbot.openai_api_key",
    )

    openai_chat_model = fields.Char(
        string="Modelo Chat",
        default="gpt-4o-mini",
        config_parameter="odoo_ai_chatbot.openai_chat_model",
    )

    openai_embed_model = fields.Char(
        string="Modelo Embeddings",
        default="text-embedding-3-small",
        config_parameter="odoo_ai_chatbot.openai_embed_model",
    )

    groq_api_key = fields.Char(
        string="Groq API Key",
        config_parameter="odoo_ai_chatbot.groq_api_key",
    )

    groq_chat_model = fields.Char(
        string="Modelo Chat (Groq)",
        default="openai/gpt-oss-20b",
        config_parameter="odoo_ai_chatbot.groq_chat_model",
    )

    groq_embed_model = fields.Char(
        string="Modelo Embeddings (Groq)",
        default="groq-embed-1",
        config_parameter="odoo_ai_chatbot.groq_embed_model",
    )

    rag_top_k = fields.Integer(
        string="RAG Top K",
        default=5,
        config_parameter="odoo_ai_chatbot.rag_top_k",
    )
