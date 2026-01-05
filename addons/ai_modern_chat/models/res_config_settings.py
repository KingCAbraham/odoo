from odoo import fields, models, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider = fields.Selection([
        ('openai', 'OpenAI (GPT-4)'),
        ('google', 'Google Gemini'),
        ('groq', 'Groq (Llama 3 - Rápido)')
    ], string="Proveedor IA", config_parameter='ai_modern_chat.provider', default='openai')
    
    ai_api_key = fields.Char(string="API Key", config_parameter='ai_modern_chat.api_key')
    ai_license_key = fields.Char(string="Licencia de Activación", config_parameter='ai_modern_chat.license_key')
    
    # CORRECCIÓN: Campo Text sin 'config_parameter' automático (causa error en Odoo).
    # Lo gestionamos manualmente con get_values/set_values.
    ai_knowledge_base = fields.Text(
        string="Base de Conocimiento Global", 
        help="Pega aquí el contenido de tus PDFs, manuales de productos o reglas de negocio."
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ICP = self.env['ir.config_parameter'].sudo()
        res.update(
            ai_knowledge_base=ICP.get_param('ai_modern_chat.knowledge_base', default=""),
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('ai_modern_chat.knowledge_base', self.ai_knowledge_base or "")