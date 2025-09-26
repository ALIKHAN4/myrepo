from odoo import models, fields

class CrmLeadSubsegment(models.Model):
    _name = 'crm.lead.subsegment'
    _description = 'CRM Lead Subsegment'

    name = fields.Char(required=True)

    color = fields.Integer(string='color')