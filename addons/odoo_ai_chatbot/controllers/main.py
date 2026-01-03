# Main controller for the AI chatbot
from odoo import http
from odoo.http import request

class AiChatbotController(http.Controller):

    @http.route("/odoo_ai_chatbot/ask", type="json", auth="user")
    def ask(self, session_id, question):
        session = request.env["odoo_ai_chatbot.session"].sudo().browse(int(session_id))
        session.ensure_one()

        # asegura que cada usuario use su sesión (excepto admin)
        if session.user_id.id != request.env.user.id and not request.env.user.has_group("base.group_system"):
            return {"answer": "No tienes permiso para usar esta sesión."}

        request.env["odoo_ai_chatbot.message"].sudo().create({
            "session_id": session.id,
            "role": "user",
            "content": question,
        })

        answer = request.env["odoo_ai_chatbot.rag"].sudo().answer_with_rag(question)

        request.env["odoo_ai_chatbot.message"].sudo().create({
            "session_id": session.id,
            "role": "assistant",
            "content": answer,
        })

        return {"answer": answer}
