from odoo import models, fields, api

class CrmLeadLine(models.Model):
    _name = 'crm.lead.line'
    _description = 'CRM Lead Line Item'

    
    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Customer', related='lead_id.partner_id', store=True)
    name = fields.Char( string='Name', related='lead_id.name', store=True)
    user_id = fields.Many2one('res.users', string='Sales Person', related='lead_id.user_id', store=True)
    team_id = fields.Many2one('crm.team', string='Sales Team', related='lead_id.team_id', store=True)
    stage_id = fields.Many2one('crm.stage', string='Stage', related='lead_id.stage_id', store=True)
    
    segment_id = fields.Many2many('crm.lead.segment', string='Segment', related='lead_id.segment_id')
    lead_type_id = fields.Many2many('crm.lead.type', string='Lead Type', related='lead_id.lead_type_id')
    sub_segment_id = fields.Many2many('crm.lead.subsegment', string='Sub-Segment', related='lead_id.sub_segment_id')
    code = fields.Char(string='Code', related='lead_id.code', store=True)

    sequence = fields.Integer(string='#')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Qty', default=1.0)
    unit_price = fields.Float(string='Unit Price')
    total_price = fields.Float(string='Total', compute='_compute_total_price', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for line in self:
            line.total_price = line.quantity * line.unit_price
    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.unit_price = line.product_id.list_price
                line.description = line.product_id.name