
from odoo import models, fields, api
from odoo.exceptions import UserError
class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sales_target_line_id = fields.Many2one('sales.target.line', string='Sales Target Line', index=True)

    segment_id = fields.Many2many('crm.lead.segment', string='Segment', compute='compute_feilds_opportunity_id',store=True,readonly=True)
    lead_type_id = fields.Many2many('crm.lead.type', string='Lead Type', compute='compute_feilds_opportunity_id',store=True,readonly=True)
    sub_segment_id = fields.Many2many('crm.lead.subsegment', string='Sub-Segment', compute='compute_feilds_opportunity_id',store=True,readonly=True)
    expected_realization_date = fields.Date(string='Expected Realization',compute='compute_feilds_opportunity_id',store=True,readonly=True)
    
    lead_count = fields.Integer(compute="_compute_counts")
    sale_target_count = fields.Integer(compute="_compute_counts")

    def _compute_counts(self):
        for rec in self:
            rec.lead_count = self.env["crm.lead"].search_count([("id", "=", rec.opportunity_id.id)])
            rec.sale_target_count = self.env["sales.target"].search_count([("id", "=", rec.sales_target_line_id.target_id.id)])


    def action_view_leads(self):
        return {
            "name": "Leads",
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "domain": [("id", "=", self.opportunity_id.id)],
            "view_mode": "list,form",
        }
    def action_view_sale_target(self):
        return {
            "name": "Sales Target",
            "type": "ir.actions.act_window",
            "res_model": "sales.target",
            "domain": [("id", "=", self.sales_target_line_id.target_id.id)],
            "view_mode": "list,form",
        }
        
    @api.depends("opportunity_id","opportunity_id.segment_id","opportunity_id.lead_type_id","opportunity_id.sub_segment_id","opportunity_id.expected_realization_date")
    def compute_feilds_opportunity_id(self):
        for rec in self:
            if rec.opportunity_id:
                rec.segment_id = rec.opportunity_id.segment_id
                rec.lead_type_id = rec.opportunity_id.lead_type_id
                rec.sub_segment_id = rec.opportunity_id.sub_segment_id
                rec.expected_realization_date = rec.opportunity_id.expected_realization_date

            else:
                rec.segment_id = False
                rec.lead_type_id = False
                rec.sub_segment_id = False
                rec.expected_realization_date = False
                
    def action_confirm(self):
        super().action_confirm()
        for rec in self:
            if rec.opportunity_id.sales_target_line_id:
                rec.opportunity_id.sales_target_line_id._compute_sale_order_ids()
                rec.opportunity_id.sales_target_line_id._compute_achieved_value()
        



            
            

                

    @api.model
    def create(self, vals):
        # If a quotation is created from an opportunity/lead, propagate the sales_target_line_id

        opp_id = vals.get('opportunity_id')
        if opp_id and not vals.get('sales_target_line_id'):
            lead = self.env['crm.lead'].browse(opp_id)
            if lead and lead.sales_target_line_id:
                vals['sales_target_line_id'] = lead.sales_target_line_id.id
            order_lines = []
            for line in lead.line_items:
                order_lines.append((0,0,{
                    "product_id":line.product_id.product_tmpl_id.id,
                    "product_uom_qty":line.quantity,
                    "price_unit":line.unit_price,
                }))
            if order_lines:
                vals["order_line"] = order_lines
                
        order = super().create(vals)
        
        if order.opportunity_id.sales_target_line_id.lead_ids:  
            order.opportunity_id.sales_target_line_id._compute_sale_order_ids()
            order.opportunity_id.sales_target_line_id._compute_achieved_value()

            return order
                

        return super().create(vals)
