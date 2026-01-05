import os

# ==============================================================================
# 1. ACTUALIZAR MANIFESTO
# ==============================================================================
manifest_fix = """
{
    'name': 'Odoo AI Copilot Pro',
    'version': '18.0.2.1.0',
    'category': 'Productivity/Artificial Intelligence',
    'summary': 'Chatbot Premium con RAG y Base de Conocimiento Estructurada',
    'description': \"\"\"
        Módulo Profesional de IA para Odoo 18.
        - Diseño UI/UX Moderno.
        - RAG Avanzado: Ventas, Contactos, Inventario.
        - Base de Conocimiento Estructurada (Importable desde Excel).
        - Multi-proveedor: OpenAI, Groq, Google Gemini.
    \"\"\",
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
"""

# ==============================================================================
# 2. NUEVO MODELO: BASE DE CONOCIMIENTO
# ==============================================================================
knowledge_model_content = """
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
        return f"TEMA: {self.name}\\n- INSTRUCCIONES: {self.instructions or 'N/A'}\\n- RECOMENDACIONES: {self.recommendations or 'N/A'}\\n- PRECAUCIONES: {self.precautions or 'N/A'}"
"""

# ==============================================================================
# 3. SEGURIDAD (CSV)
# ==============================================================================
security_csv_content = """id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
access_ai_knowledge_base,ai.knowledge.base,model_ai_knowledge_base,base.group_user,1,1,1,1
"""

# ==============================================================================
# 4. INIT MODELS
# ==============================================================================
init_models_fix = """
from . import res_config_settings
from . import knowledge_base
"""

# ==============================================================================
# 5. NUEVA VISTA XML (CORREGIDA PARA ODOO 18: TREE -> LIST)
# ==============================================================================
# IMPORTANTE: Odoo 18 eliminó la etiqueta <tree>. Usamos <list>.
knowledge_view_content = """
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <!-- VISTA FORMULARIO -->
    <record id="view_ai_knowledge_form" model="ir.ui.view">
        <field name="name">ai.knowledge.base.form</field>
        <field name="model">ai.knowledge.base</field>
        <field name="arch" type="xml">
            <form string="Artículo de Conocimiento">
                <sheet>
                    <div class="oe_title">
                        <label for="name" class="oe_edit_only"/>
                        <h1><field name="name" placeholder="Ej: Tratamiento Capilar X"/></h1>
                    </div>
                    <group>
                        <group string="Detalles de Uso">
                            <field name="instructions" placeholder="Paso 1: Aplicar sobre cabello húmedo..."/>
                            <field name="recommendations" placeholder="Usar dos veces por semana..."/>
                        </group>
                        <group string="Seguridad">
                            <field name="precautions" placeholder="Evitar contacto con los ojos..."/>
                            <field name="active" widget="boolean_toggle"/>
                        </group>
                    </group>
                </sheet>
            </form>
        </field>
    </record>

    <!-- VISTA LISTA (Corrección: <list> en lugar de <tree>) -->
    <record id="view_ai_knowledge_list" model="ir.ui.view">
        <field name="name">ai.knowledge.base.list</field>
        <field name="model">ai.knowledge.base</field>
        <field name="arch" type="xml">
            <list string="Base de Conocimiento IA">
                <field name="name"/>
                <field name="instructions" optional="show"/>
                <field name="recommendations" optional="hide"/>
                <field name="precautions" optional="hide"/>
            </list>
        </field>
    </record>

    <!-- ACCIÓN DE VENTANA (Corrección: view_mode='list,form') -->
    <record id="action_ai_knowledge_base" model="ir.actions.act_window">
        <field name="name">Base de Conocimiento IA</field>
        <field name="res_model">ai.knowledge.base</field>
        <field name="view_mode">list,form</field>
        <field name="help" type="html">
          <p class="o_view_nocontent_smiling_face">
            Crear primer registro de conocimiento
          </p><p>
            Aquí puedes definir instrucciones detalladas por producto.
            Usa el botón "Importar" para subir tu Excel masivo.
          </p>
        </field>
    </record>

    <!-- MENÚ -->
    <menuitem id="menu_ai_knowledge_base"
              name="Base de Conocimiento"
              parent="menu_ai_chat_root"
              action="action_ai_knowledge_base"
              sequence="20"/>
</odoo>
"""

# ==============================================================================
# 6. CONTROLLER
# ==============================================================================
controller_fix = """
from odoo import http
from odoo.http import request
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class AIChatController(http.Controller):
    
    def _get_dynamic_odoo_data(self, prompt):
        context = []
        p_lower = prompt.lower()
        
        # 1. BÚSQUEDA EN BASE DE CONOCIMIENTO
        try:
            keywords = [w for w in p_lower.split() if len(w) > 3]
            domain = []
            
            if keywords:
                domain = ['|'] * (len(keywords) - 1) + [('name', 'ilike', k) for k in keywords]
                domain = ['&', ('active', '=', True)] + domain
                
                kb_records = request.env['ai.knowledge.base'].sudo().search(domain, limit=3)
                
                if kb_records:
                    context.append("=== BASE DE CONOCIMIENTO ESPECÍFICA ENCONTRADA ===")
                    for kb in kb_records:
                        context.append(kb.get_context_str())
        except Exception as e:
            _logger.warning(f"Error buscando KB: {e}")

        # 2. BÚSQUEDA RAG ESTÁNDAR
        try:
            if any(w in p_lower for w in ['stock', 'inventario', 'producto', 'precio', 'costo']):
                products = request.env['product.product'].sudo().search([('detailed_type', 'in', ['product', 'consu'])], limit=5)
                if products:
                    lines = [f"- {p.name}: Stock {p.qty_available}, Precio ${p.list_price}" for p in products]
                    context.append("DATOS DE INVENTARIO (ERP):\\n" + "\\n".join(lines))

            if any(w in p_lower for w in ['venta', 'pedido']):
                orders = request.env['sale.order'].sudo().search([('state','in',['sale','done'])], limit=5, order='date_order desc')
                if orders:
                    lines = [f"- {o.name}: ${o.amount_total} ({o.partner_id.name})" for o in orders]
                    context.append("ÚLTIMAS VENTAS:\\n" + "\\n".join(lines))
                    
        except Exception as e:
            _logger.warning(f"Error RAG Standard: {e}")

        return "\\n\\n".join(context)

    @http.route('/ai_chat/send', type='json', auth='user')
    def send_message(self, message_content):
        ICP = request.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('ai_modern_chat.api_key')
        provider = ICP.get_param('ai_modern_chat.provider')
        
        if not api_key:
            return {'status': 'error', 'message': '⚠️ Falta API Key en Ajustes.'}

        odoo_data = self._get_dynamic_odoo_data(message_content)
        
        system_msg = (
            f"Eres el Asistente Experto de Odoo. "
            f"Tienes acceso a una Base de Conocimiento de productos y al ERP en tiempo real.\\n\\n"
            f"=== DATOS ENCONTRADOS PARA ESTA CONSULTA ===\\n{odoo_data}\\n\\n"
            f"Responde basándote en los DATOS ENCONTRADOS. Si hay instrucciones de uso o precauciones específicas, menciónalas."
        )

        try:
            if provider == 'openai':
                res = requests.post('https://api.openai.com/v1/chat/completions', 
                    headers={'Authorization': f'Bearer {api_key}'},
                    json={"model": "gpt-4-turbo", "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": message_content}]},
                    timeout=30)
                if res.status_code == 200:
                    return {'status': 'success', 'content': res.json()['choices'][0]['message']['content']}
                return {'status': 'error', 'message': f"OpenAI Error: {res.text}"}
            
            elif provider == 'groq':
                res = requests.post('https://api.groq.com/openai/v1/chat/completions', 
                    headers={'Authorization': f'Bearer {api_key}'},
                    json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": message_content}]},
                    timeout=30)
                if res.status_code == 200:
                    return {'status': 'success', 'content': res.json()['choices'][0]['message']['content']}
                return {'status': 'error', 'message': f"Groq Error: {res.text}"}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        
        return {'status': 'error', 'message': 'Proveedor no soportado'}
"""

# ==============================================================================
# 7. EJECUCIÓN
# ==============================================================================

files_to_update = {
    "ai_modern_chat/__manifest__.py": manifest_fix,
    "ai_modern_chat/models/__init__.py": init_models_fix,
    "ai_modern_chat/models/knowledge_base.py": knowledge_model_content,
    "ai_modern_chat/security/ir.model.access.csv": security_csv_content,
    "ai_modern_chat/views/knowledge_base_views.xml": knowledge_view_content,
    "ai_modern_chat/controllers/main.py": controller_fix,
}

print("🚀 Actualizando Módulo (Fix Odoo 18 <list> tag)...")

for path, content in files_to_update.items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"✅ Archivo corregido: {path}")

print("\n✨ TODO LISTO")
print("1. Reinicia Odoo: sudo service odoo restart")
print("2. ¡Ahora sí! Dale 'Actualizar' al módulo en Apps.")