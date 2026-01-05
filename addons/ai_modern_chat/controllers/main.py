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
                    context.append("DATOS DE INVENTARIO (ERP):\n" + "\n".join(lines))

            if any(w in p_lower for w in ['venta', 'pedido']):
                orders = request.env['sale.order'].sudo().search([('state','in',['sale','done'])], limit=5, order='date_order desc')
                if orders:
                    lines = [f"- {o.name}: ${o.amount_total} ({o.partner_id.name})" for o in orders]
                    context.append("ÚLTIMAS VENTAS:\n" + "\n".join(lines))
                    
        except Exception as e:
            _logger.warning(f"Error RAG Standard: {e}")

        return "\n\n".join(context)

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
            f"Tienes acceso a una Base de Conocimiento de productos y al ERP en tiempo real.\n\n"
            f"=== DATOS ENCONTRADOS PARA ESTA CONSULTA ===\n{odoo_data}\n\n"
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