import os

# Nombre de la carpeta principal del módulo
MODULE_NAME = "ai_modern_chat"

def create_file(path, content):
    full_path = os.path.join(MODULE_NAME, path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"✅ Archivo creado: {full_path}")

# ==========================================
# 1. MANIFEST Y CONFIGURACIÓN
# ==========================================

manifest_content = """
{
    'name': 'Odoo AI Copilot Pro',
    'version': '18.0.1.0.0',
    'category': 'Productivity/Artificial Intelligence',
    'summary': 'Chatbot Premium con RAG y UI Moderna',
    'description': \"\"\"
        Módulo Profesional de IA para Odoo 18.
        - Diseño UI/UX Moderno (Shadows, Rounded, Gradient).
        - RAG: Contexto inteligente de Ventas y Contactos.
        - Efecto de escritura en tiempo real.
        - Autor: Carlos Chavez.
    \"\"\",
    'author': 'Carlos Chavez',
    'license': 'OPL-1',
    'depends': ['base', 'web', 'sale_management', 'contacts'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/ai_chat_action.xml',
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

init_main_content = """
from . import controllers
from . import models
"""

init_controllers_content = """
from . import main
"""

init_models_content = """
from . import res_config_settings
"""

# ==========================================
# 2. BACKEND (PYTHON) - RAG Y CONTROLADOR
# ==========================================

controller_content = """
from odoo import http
from odoo.http import request
import requests
import json
import logging

_logger = logging.getLogger(__name__)

class AIChatController(http.Controller):
    
    def _get_rag_context(self, prompt):
        context = []
        p_lower = prompt.lower()
        try:
            # RAG VENTAS
            if any(w in p_lower for w in ['venta', 'pedido', 'cotización', 'dinero']):
                orders = request.env['sale.order'].sudo().search([('state','in',['sale','done'])], limit=5, order='date_order desc')
                if orders:
                    lines = [f"- {o.name}: {o.amount_total} {o.currency_id.symbol} -> {o.partner_id.name} ({o.date_order})" for o in orders]
                    context.append("ÚLTIMAS VENTAS:\\n" + "\\n".join(lines))
            
            # RAG CLIENTES
            if any(w in p_lower for w in ['cliente', 'contacto', 'partner']):
                partners = request.env['res.partner'].sudo().search([], limit=5, order='create_date desc')
                if partners:
                    lines = [f"- {p.name} (Email: {p.email}, Tel: {p.phone})" for p in partners]
                    context.append("CLIENTES RECIENTES:\\n" + "\\n".join(lines))
        except Exception as e:
            _logger.error(f"RAG Error: {e}")
        return "\\n\\n".join(context)

    @http.route('/ai_chat/send', type='json', auth='user')
    def send_message(self, message_content):
        ICP = request.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('ai_modern_chat.api_key')
        provider = ICP.get_param('ai_modern_chat.provider')
        
        if not api_key:
            return {'status': 'error', 'message': '⚠️ Falta API Key en Ajustes.'}

        rag_data = self._get_rag_context(message_content)
        system_msg = f"Eres Odoo Copilot (Carlos Chavez Ed.). Usa este contexto de Odoo si es útil:\\n{rag_data}"

        try:
            # OPENAI
            if provider == 'openai':
                res = requests.post('https://api.openai.com/v1/chat/completions', 
                    headers={'Authorization': f'Bearer {api_key}'},
                    json={"model": "gpt-4-turbo", "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": message_content}]},
                    timeout=30)
                if res.status_code == 200:
                    return {'status': 'success', 'content': res.json()['choices'][0]['message']['content']}
                return {'status': 'error', 'message': f"OpenAI Error: {res.text}"}
            
            # GROQ
            elif provider == 'groq':
                res = requests.post('https://api.groq.com/openai/v1/chat/completions', 
                    headers={'Authorization': f'Bearer {api_key}'},
                    json={"model": "llama3-70b-8192", "messages": [{"role": "system", "content": system_msg}, {"role": "user", "content": message_content}]},
                    timeout=30)
                if res.status_code == 200:
                    return {'status': 'success', 'content': res.json()['choices'][0]['message']['content']}
                return {'status': 'error', 'message': f"Groq Error: {res.text}"}

        except Exception as e:
            return {'status': 'error', 'message': str(e)}
        
        return {'status': 'error', 'message': 'Proveedor no soportado'}
"""

model_content = """
from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_provider = fields.Selection([
        ('openai', 'OpenAI (GPT-4)'),
        ('google', 'Google Gemini'),
        ('groq', 'Groq (Llama 3 - Rápido)')
    ], string="Proveedor IA", config_parameter='ai_modern_chat.provider', default='openai')
    
    ai_api_key = fields.Char(string="API Key", config_parameter='ai_modern_chat.api_key')
    ai_license_key = fields.Char(string="Licencia de Activación", config_parameter='ai_modern_chat.license_key')
"""

# ==========================================
# 3. VISTAS XML (BACKEND)
# ==========================================

view_config_content = """
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="res_config_settings_view_form_ai_chat" model="ir.ui.view">
        <field name="name">res.config.settings.view.form.inherit.ai.chat</field>
        <field name="model">res.config.settings</field>
        <field name="inherit_id" ref="base.res_config_settings_view_form"/>
        <field name="arch" type="xml">
            <xpath expr="//form" position="inside">
                <app data-string="Odoo AI Copilot" string="Odoo AI Copilot" name="ai_modern_chat">
                    <block title="Configuración IA">
                        <setting help="Licencia de Carlos Chavez"><field name="ai_license_key" password="True"/></setting>
                        <setting help="Motor de Inteligencia"><field name="ai_provider"/></setting>
                        <setting help="Clave API (sk-...)"><field name="ai_api_key" password="True"/></setting>
                    </block>
                </app>
            </xpath>
        </field>
    </record>
    <record id="action_ai_chat_config" model="ir.actions.act_window">
        <field name="name">Configuración AI</field>
        <field name="res_model">res.config.settings</field>
        <field name="view_mode">form</field>
        <field name="context">{'module' : 'ai_modern_chat'}</field>
    </record>
</odoo>
"""

view_action_content = """
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="action_open_ai_chat_screen" model="ir.actions.client">
        <field name="name">AI Copilot Pro</field>
        <field name="tag">ai_modern_chat.ChatScreen</field>
    </record>
    <menuitem id="menu_ai_chat_root" name="AI Copilot" action="action_open_ai_chat_screen" sequence="1" web_icon="ai_modern_chat,static/description/icon.png"/>
</odoo>
"""

# ==========================================
# 4. FRONTEND (ESTILOS PREMIUM Y JS)
# ==========================================

css_content = """
/* ESTILO PREMIUM */
.o_ai_chat_main {
    background-color: #f3f4f6; /* Gris muy suave */
    height: 100%;
    display: flex;
    flex-direction: column;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

.o_chat_header {
    background: white;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid #e5e7eb;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.o_chat_container {
    max-width: 900px;
    margin: 0 auto;
    width: 100%;
}

.o_chat_bubble {
    padding: 16px 20px;
    border-radius: 18px;
    font-size: 15px;
    line-height: 1.6;
    margin-bottom: 16px;
    position: relative;
    max-width: 85%;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    transition: all 0.2s;
}

.o_chat_bubble.user {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); /* Indigo Gradient */
    color: white;
    align-self: flex-end;
    border-bottom-right-radius: 4px;
    margin-left: auto;
}

.o_chat_bubble.system {
    background-color: white;
    color: #374151; /* Gris oscuro */
    border: 1px solid #e5e7eb;
    align-self: flex-start;
    border-bottom-left-radius: 4px;
}

.o_chat_input_container {
    background: white;
    border-top: 1px solid #e5e7eb;
    padding: 1.5rem;
}

.o_chat_input_wrapper {
    background: white;
    border: 1px solid #d1d5db;
    border-radius: 16px;
    padding: 6px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    display: flex;
    align-items: center;
    transition: box-shadow 0.2s, border-color 0.2s;
}

.o_chat_input_wrapper:focus-within {
    border-color: #6366f1;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.1);
}

.o_chat_input {
    border: none;
    background: transparent;
    padding: 10px 16px;
    font-size: 15px;
    width: 100%;
}

.o_chat_input:focus {
    outline: none;
}

.o_send_btn {
    background-color: #4f46e5;
    color: white;
    border: none;
    border-radius: 12px;
    width: 42px;
    height: 42px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background-color 0.2s;
}

.o_send_btn:hover {
    background-color: #4338ca;
}

.o_send_btn:disabled {
    background-color: #a5b4fc;
    cursor: not-allowed;
}
"""

js_content = """
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

export class AIChatScreen extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.notification = useService("notification");
        
        this.state = useState({ 
            messages: [{role:'system', content:'¡Hola! Soy tu Copiloto Odoo Pro. ¿Qué analizamos hoy?'}], 
            currentInput: '', 
            isLoading: false,
            isTyping: false
        });
        
        this.messagesEndRef = useRef("messagesEnd");
        this.typingInterval = null;

        onMounted(() => this.scrollToBottom());
        onWillUnmount(() => {
            if (this.typingInterval) clearInterval(this.typingInterval);
        });
    }

    scrollToBottom() {
        if (this.messagesEndRef.el) this.messagesEndRef.el.scrollIntoView({ behavior: "smooth" });
    }

    // Efecto de escritura tipo ChatGPT
    startTypewriter(fullText) {
        this.state.isTyping = true;
        const msgIndex = this.state.messages.length;
        this.state.messages.push({ role: 'system', content: '' }); // Burbuja vacía
        
        let i = 0;
        const speed = 10; // Velocidad ms

        this.typingInterval = setInterval(() => {
            if (!this.state.isTyping) { clearInterval(this.typingInterval); return; }
            
            this.state.messages[msgIndex].content += fullText.charAt(i);
            i++;
            this.scrollToBottom();

            if (i >= fullText.length) {
                clearInterval(this.typingInterval);
                this.state.isTyping = false;
            }
        }, speed);
    }

    async sendMessage() {
        if (!this.state.currentInput.trim() || this.state.isLoading || this.state.isTyping) return;
        
        const text = this.state.currentInput;
        this.state.messages.push({ role: 'user', content: text });
        this.state.currentInput = '';
        this.state.isLoading = true;
        this.scrollToBottom();

        try {
            const res = await this.rpc("/ai_chat/send", { message_content: text });
            this.state.isLoading = false;
            
            if (res.status === 'success') {
                this.startTypewriter(res.content);
            } else {
                this.notification.add(res.message, { type: "danger" });
                this.state.messages.push({ role: 'system', content: "⚠️ Error: " + res.message });
            }
        } catch (e) {
            this.state.isLoading = false;
            this.notification.add("Error de conexión", { type: "danger" });
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }
}

AIChatScreen.template = "ai_modern_chat.ScreenTemplate";
registry.category("actions").add("ai_modern_chat.ChatScreen", AIChatScreen);
"""

xml_content = """
<?xml version="1.0" encoding="UTF-8"?>
<templates xml:space="preserve">
    <t t-name="ai_modern_chat.ScreenTemplate" owl="1">
        <div class="o_ai_chat_main">
            <!-- Header -->
            <div class="o_chat_header d-flex justify-content-between align-items-center">
                <div class="d-flex align-items-center gap-2">
                    <div class="bg-primary text-white rounded p-2 shadow-sm">
                        <i class="fa fa-robot"/>
                    </div>
                    <div>
                        <h4 class="m-0 fw-bold text-dark" style="font-size: 1.1rem;">Odoo Copilot</h4>
                        <small class="text-success fw-bold" style="font-size: 0.75rem;">● Online</small>
                    </div>
                </div>
                <span class="text-muted small">v1.0 • Carlos Chavez</span>
            </div>

            <!-- Body -->
            <div class="flex-grow-1 overflow-auto p-4" t-ref="scrollContainer">
                <div class="o_chat_container">
                    <t t-foreach="state.messages" t-as="msg" t-key="msg_index">
                        <div t-attf-class="d-flex w-100 {{ msg.role === 'user' ? 'justify-content-end' : 'justify-content-start' }}">
                            
                            <!-- Avatar System -->
                            <t t-if="msg.role === 'system'">
                                <div class="me-2 mt-1">
                                    <div class="rounded-circle bg-white border d-flex align-items-center justify-content-center shadow-sm" style="width: 32px; height: 32px;">
                                        <i class="fa fa-robot text-primary small"/>
                                    </div>
                                </div>
                            </t>

                            <div t-attf-class="o_chat_bubble {{ msg.role }}">
                                <div style="white-space: pre-wrap;"><t t-esc="msg.content"/></div>
                            </div>
                        </div>
                    </t>
                    
                    <t t-if="state.isLoading">
                        <div class="d-flex align-items-center gap-2 text-muted ms-5 mb-3">
                            <i class="fa fa-circle-o-notch fa-spin"/>
                            <small class="fst-italic">Analizando datos...</small>
                        </div>
                    </t>
                    
                    <div t-ref="messagesEnd"/>
                </div>
            </div>

            <!-- Input Footer -->
            <div class="o_chat_input_container">
                <div class="o_chat_container">
                    <div class="o_chat_input_wrapper">
                        <input type="text" 
                               class="o_chat_input" 
                               t-model="state.currentInput" 
                               t-on-keydown="onKeydown"
                               t-att-disabled="state.isLoading or state.isTyping"
                               placeholder="Pregunta sobre ventas, clientes o inventario..."/>
                        
                        <button class="o_send_btn me-1" 
                                t-on-click="sendMessage"
                                t-att-disabled="!state.currentInput or state.isLoading or state.isTyping">
                            <i class="fa fa-paper-plane"/>
                        </button>
                    </div>
                    <div class="text-center mt-3">
                        <small class="text-muted" style="font-size: 0.7rem;">Powered by AI • Developed by Carlos Chavez</small>
                    </div>
                </div>
            </div>
        </div>
    </t>
</templates>
"""

# ==========================================
# 5. CREACIÓN DE ARCHIVOS
# ==========================================

files_to_create = {
    "__init__.py": init_main_content,
    "__manifest__.py": manifest_content,
    "controllers/__init__.py": init_controllers_content,
    "controllers/main.py": controller_content,
    "models/__init__.py": init_models_content,
    "models/res_config_settings.py": model_content,
    "views/res_config_settings_views.xml": view_config_content,
    "views/ai_chat_action.xml": view_action_content,
    "static/src/css/chat_style.css": css_content,
    "static/src/js/ai_chat_screen.js": js_content,
    "static/src/xml/ai_chat_screen.xml": xml_content,
}

print(f"🚀 Iniciando generación de módulo: {MODULE_NAME}")
if not os.path.exists(MODULE_NAME):
    os.makedirs(MODULE_NAME)
    print(f"📂 Carpeta creada: {MODULE_NAME}")

for path, content in files_to_create.items():
    create_file(path, content)

print("\n✨ ¡MÓDULO COMPLETADO!")
print("Instrucciones:")
print(f"1. Mueve la carpeta '{MODULE_NAME}' a tu directorio 'custom_addons'.")
print("2. Reinicia Odoo.")
print("3. Instala 'Odoo AI Copilot Pro'.")