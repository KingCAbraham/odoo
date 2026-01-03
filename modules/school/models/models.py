# -*- coding: utf-8 -*-
from odoo import models, fields


class SchoolStudent(models.Model):
    _name = "school.student"
    _description = "Student"

    name = fields.Char(string="Nombre", required=True)
    age = fields.Integer(string="Edad")
    active = fields.Boolean(string="Activo", default=True)
    enrollment_date = fields.Date(
        string="Fecha de inscripción",
        default=fields.Date.context_today,
    )
    email = fields.Char(string="Correo electrónico")
    phone = fields.Char(string="Teléfono")
    notes = fields.Text(string="Notas internas")

    # campos nuevos para que el kanban luzca
    image_1920 = fields.Image(string="Foto")
    level = fields.Selection([
        ('primary', 'Primaria'),
        ('secondary', 'Secundaria'),
        ('university', 'Universidad'),
    ], string="Nivel")
    average_score = fields.Float(string="Promedio")
