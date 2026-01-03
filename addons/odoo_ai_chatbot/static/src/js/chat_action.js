// JavaScript actions for chatbot
/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onMounted, useRef } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";

class ChatClient extends Component {
    static template = "odoo_ai_chatbot.ChatClient";

    setup() {
        this.state = useState({ sessionId: null, messages: [], input: "" });
        this.bodyRef = useRef("body");

        onMounted(async () => {
            await this.newSession();
        });
    }

    async newSession() {
        const sessionId = await rpc("/web/dataset/call_kw", {
            model: "odoo_ai_chatbot.session",
            method: "create",
            args: [{ name: "Chat" }],
            kwargs: {},
        });
        this.state.sessionId = sessionId;
        this.state.messages = [];
    }

    async send() {
        const text = (this.state.input || "").trim();
        if (!text) return;

        this.state.messages.push({ id: Date.now() + "_u", role: "user", content: text });
        this.state.input = "";

        const result = await rpc("/odoo_ai_chatbot/ask", {
            session_id: this.state.sessionId,
            question: text,
        });

        this.state.messages.push({ id: Date.now() + "_a", role: "assistant", content: result.answer });

        setTimeout(() => {
            const el = this.bodyRef.el;
            if (el) el.scrollTop = el.scrollHeight;
        }, 10);
    }
}

registry.category("actions").add("odoo_ai_chatbot.chat_client", ChatClient);
