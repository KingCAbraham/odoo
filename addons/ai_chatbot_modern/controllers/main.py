# Controlador HTTP que expone un endpoint para hacer preguntas al chatbot.
from odoo import http
from odoo.http import request, Response
import json

class AiChatbotModernController(http.Controller):

    @http.route('/ai_chatbot_modern/ask', type='json', auth='user')
    def ask(self, question):
        """
        Llama al servicio RAG del modelo para obtener una respuesta contextualizada.
        """
        rag_service = request.env['ai_chatbot_modern.rag'].sudo()
        answer = rag_service.answer_with_rag(question)
        return {'answer': answer}
