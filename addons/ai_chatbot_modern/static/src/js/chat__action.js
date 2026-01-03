/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onWillStart, onMounted, useRef, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ChatModernAction extends Component {
    setup() {
        console.log("✅ ai_chatbot_modern chat_action.js cargado");

        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            sessionId: null,
            messages: [],
            input: "",
            loading: false,
        });

        this.inputRef = useRef("inputRef");

        onWillStart(async () => {
            this.state.sessionId = await this.orm.call(
                "ai_chatbot_modern.session",
                "get_or_create_session",
                [],
                {}
            );

            this.state.messages = await this.orm.call(
                "ai_chatbot_modern.session",
                "rpc_get_messages",
                [this.state.sessionId],
                {}
            );
        });

        onMounted(() => {
            if (this.inputRef.el) this.inputRef.el.focus();
        });
    }

    async sendMessage() {
        const text = (this.state.input || "").trim();
        if (!text || this.state.loading) return;

        this.state.loading = true;
        this.state.messages.push({ role: "user", content: text });
        this.state.input = "";

        try {
            const res = await this.orm.call(
                "ai_chatbot_modern.session",
                "rpc_send_message",
                [this.state.sessionId, text],
                {}
            );

            if (res && res.answer) {
                this.state.messages.push({ role: "assistant", content: res.answer });
            } else {
                this.state.messages.push({ role: "assistant", content: "No pude obtener respuesta del servidor." });
            }
        } catch (e) {
            this.notification.add("Error al enviar el mensaje. Revisa logs del servidor.", { type: "danger" });
        } finally {
            this.state.loading = false;
            if (this.inputRef.el) this.inputRef.el.focus();
        }
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }
}

ChatModernAction.template = "ai_chatbot_modern.ChatAction";

// ✅ Tag exacto del ir.actions.client
registry.category("actions").add("ai_chatbot_modern.chat", ChatModernAction);
