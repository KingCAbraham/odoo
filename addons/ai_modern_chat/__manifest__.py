{
    'name': 'Odoo AI Copilot Pro',
    'version': '18.0.2.1.0',
    'category': 'Productivity/Artificial Intelligence',
    'summary': 'Chatbot Premium con RAG y Base de Conocimiento Estructurada',
    'description': """
        Módulo Profesional de IA para Odoo 18.
        - Diseño UI/UX Moderno.
        - RAG Avanzado: Ventas, Contactos, Inventario.
        - Base de Conocimiento Estructurada (Importable desde Excel).
        - Multi-proveedor: OpenAI, Groq, Google Gemini.
    """,
    'author': 'Carlos Chavez',
    'license': 'OPL-1',
    'depends': ['base', 'web', 'sale_management', 'contacts', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/ai_chat_action.xml',
        'views/knowledge_base_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_modern_chat/static/src/css/chat_style.css',
            'ai_modern_chat/static/src/js/ai_chat_screen.js',
            'ai_modern_chat/static/src/xml/ai_chat_screen.xml',
        ],
    },
    'installable': True,
    'application': True,
}