from odoo import models, fields

class ProductCategory(models.Model):
    _inherit = 'product.category'
    
    company_id = fields.Many2one('res.company', string='Company')
    code = fields.Char(string='Code')
