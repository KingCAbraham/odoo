from odoo import models, fields

class AiKnowledgeBase(models.Model):
    _name = 'ai.knowledge.base'
    _description = 'Base de Conocimiento IA'
    _order = 'name'

    name = fields.Char(string="Producto / Tema", required=True, help="Ej: Shampoo para Rizos, Política de Devolución")
    active = fields.Boolean(default=True)
    
    # Columnas estructuradas para importar desde Excel
    instructions = fields.Text(string="Instrucciones de Uso", help="¿Cómo se aplica o utiliza?")
    recommendations = fields.Text(string="Recomendaciones", help="Tips pro, mejores prácticas")
    precautions = fields.Text(string="Precauciones / Contraindicaciones", help="Advertencias de seguridad")
    
    def get_context_str(self):
        return f"TEMA: {self.name}\n- INSTRUCCIONES: {self.instructions or 'N/A'}\n- RECOMENDACIONES: {self.recommendations or 'N/A'}\n- PRECAUCIONES: {self.precautions or 'N/A'}"