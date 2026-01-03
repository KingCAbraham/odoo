# -*- coding: utf-8 -*-
{
    'name': "School",
    'summary': "Pequeño módulo de ejemplo para gestionar estudiantes",
    'description': "Módulo de prueba para aprender a desarrollar en Odoo.",
    'author': "Carlos / NextByte",
    'website': "https://www.nextbyte.mx",
    'category': 'Education',
    'version': '18.0.1.0.0',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'views/student_views.xml',
    ],
    'application': True,
}
