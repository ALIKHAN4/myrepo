from odoo import models, fields

class CrmLeadType(models.Model):
    _name = 'crm.lead.type'
    _description = 'CRM Lead Type'

    name = fields.Char(required=True)

    color = fields.Integer(string='color')