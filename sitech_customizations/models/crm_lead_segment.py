from odoo import models, fields

class CrmLeadSegment(models.Model):
    _name = 'crm.lead.segment'
    _description = 'CRM Lead Segment'


    name = fields.Char(required=True)
    color = fields.Integer(string='color')
    company_id = fields.Many2one('res.company', string='Company')
