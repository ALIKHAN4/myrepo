from odoo import models, fields

class CrmLostReason(models.Model):
    _inherit = 'crm.lost.reason'
    
    company_id = fields.Many2one('res.company', string='Company')
