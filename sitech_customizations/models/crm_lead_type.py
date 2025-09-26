from odoo import models, fields

class CrmLeadType(models.Model):
    _name = 'crm.lead.type'
    _description = 'CRM Lead Type'

    name = fields.Char(required=True)
    company_id = fields.Many2one('res.company', string='Company')

    color = fields.Integer(string='color')