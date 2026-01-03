{
    "name": "AI Chatbot Modern",
    "version": "1.0.0",
    "category": "Tools",
    "summary": "Chatbot inteligente con documentos (PDF/TXT) usando RAG y configuración minimalista",
    "depends": ["base", "web", "base_setup"],
    "data": [
        "security/ir.model.access.csv",

        # Vistas/menús
        "views/documents_views.xml",
        "views/chat_menu.xml",
        "views/settings_views.xml",
    ],
    "installable": True,
    "application": True,
}
