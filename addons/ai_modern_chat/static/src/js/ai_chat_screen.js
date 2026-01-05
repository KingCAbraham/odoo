/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";

export class AIChatScreen extends Component {
    setup() {
        // INTENTO DE CARGA DE SERVICIOS CON SEGURIDAD
        try {
            this.rpc = useService("rpc");
        } catch (e) {
            console.log("Servicio RPC no disponible, usando fallback nativo.");
            this.rpc = null;
        }
        
        try {
            this.notification = useService("notification");
        } catch (e) {
            this.notification = { add: (msg) => console.log(msg) };
        }

        this.state = useState({ 
            messages: [{role:'system', content:'¡Hola! Soy tu Copiloto Odoo. ¿Qué analizamos hoy?'}], 
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

    startTypewriter(fullText) {
        this.state.isTyping = true;
        const msgIndex = this.state.messages.length;
        this.state.messages.push({ role: 'system', content: '' });
        
        let i = 0;
        const speed = 10; 

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
            let result;
            
            // LÓGICA HÍBRIDA: Si RPC falla, usamos FETCH estándar
            if (this.rpc) {
                result = await this.rpc("/ai_chat/send", { message_content: text });
            } else {
                // Fallback robusto para Odoo 18
                const response = await fetch('/ai_chat/send', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-Openerp-Session-Id': document.cookie.match(/session_id=([^;]+)/)?.[1] 
                    },
                    body: JSON.stringify({ params: { message_content: text } })
                });
                const json = await response.json();
                result = json.result;
            }
            
            this.state.isLoading = false;
            
            if (result && result.status === 'success') {
                this.startTypewriter(result.content);
            } else {
                const errorMsg = result ? result.message : "Error de respuesta";
                this.notification.add(errorMsg, { type: "danger" });
                this.state.messages.push({ role: 'system', content: "⚠️ Error: " + errorMsg });
            }
        } catch (e) {
            console.error(e);
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