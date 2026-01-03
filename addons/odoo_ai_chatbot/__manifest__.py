{
    "name": "AI Chatbot (RAG) - Local",
    "version": "1.0.0",
    "category": "Tools",
    "summary": "Chatbot inteligente con documentos (PDF/TXT) usando RAG",
    "depends": ["base", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/documents_views.xml",
        "views/menus.xml",
        "views/settings_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "odoo_ai_chatbot/static/src/scss/chat.scss",
            "odoo_ai_chatbot/static/src/xml/chat_action.xml",
            "odoo_ai_chatbot/static/src/js/chat_action.js",
        ],
    },
    "external_dependencies": {
        "python": ["openai", "groq"],
    },
    "installable": True,
    "application": True,
}
