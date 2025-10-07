from odoo import models, fields ,api
from odoo.exceptions import UserError



class CrmStage(models.Model):
    _inherit = 'crm.stage'
    
    prob_counter = fields.Float('Probability Counter (%)')