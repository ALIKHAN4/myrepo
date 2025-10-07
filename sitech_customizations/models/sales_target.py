
from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

from datetime import datetime, timedelta

class SalesTarget(models.Model):
    _name = 'sales.target'
    _description = 'Sales Target'
    _rec_name = 'name'

    _inherit = ["mail.thread", "mail.activity.mixin"]
    name = fields.Char(string='Target Name', required=True,  tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company,  tracking=True)
    team_id = fields.Many2one('crm.team', string='Sales Team',  tracking=True)
    timespan = fields.Selection([('yearly','Yearly'), ('quarterly','Quarterly'), ('monthly','Monthly')], string='Time Span', required=True,  tracking=True)
    period_start = fields.Date(string='Period Start', required=True,  tracking=True)
    period_end = fields.Date(string='Period End', store=True,  tracking=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True, readonly=True,  tracking=True)
    target_value = fields.Float(string="Target Value",compute="_compute_target_value", store=True,  tracking=True)

    @api.depends('line_ids.total_price')
    def _compute_target_value(self):
        for rec in self:
            rec.target_value = sum(rec.line_ids.mapped('total_price'))
    achievement_value = fields.Float(string='Target Achievement Value (Achieved)', compute='_compute_achievement_totals', store=True,  tracking=True)
    achievement_status = fields.Char(string='Target Achievement Status (%)', compute='_compute_achievement_totals', store=True,  tracking=True)
    success_status = fields.Selection([('high','High'), ('medium','Medium'), ('low','Low')], compute='_compute_achievement_totals',  tracking=True)
    state = fields.Selection([('draft','Draft'), ('waiting','Waiting for Approval'), ('approved','Approved'), ('rejected','Rejected')], default='draft',  tracking=True)
    line_ids = fields.One2many('sales.target.line', 'target_id', string='Line Items',  tracking=True)
    # @api.depends('period_start', 'timespan')
    # def _compute_period_end(self):
    #     for rec in self:
    #             # rec.period_end = rec.period_start

    #         if rec.period_start and rec.timespan:
    #             if rec.timespan == 'monthly':
    #                 rec.period_end = rec.period_start + relativedelta(months=1, days=-1)
    #             elif rec.timespan == 'quarterly':
    #                 rec.period_end = rec.period_start + relativedelta(months=3, days=-1)
    #             elif rec.timespan == 'yearly':
    #                 rec.period_end = rec.period_start + relativedelta(years=1, days=-1)
    #         else:
    #             rec.period_end = False
    def action_waiting(self):
        self.write({'state':'waiting'})
    def action_approve(self):
        # Set approved and create leads for each line
        for rec in self:
            # avoid duplicate lead creation if re-approving
            existing_leads = self.env['crm.lead'].search([('sales_target_line_id', 'in', rec.line_ids.ids)])
            created_for = set(existing_leads.mapped('sales_target_line_id').ids)
            tag = self.env["crm.tag"].search([("name","like","Must Win")],limit=1)
            for line in rec.line_ids:
                if line.id in created_for:
                    continue
                vals = {
                    'name': line.partner_id.name and f"{line.partner_id.name} - {rec.name}" or (rec.name or 'New Opportunity'),
                    'type': 'opportunity',
                    'partner_id': line.partner_id.id if line.partner_id else False,
                    'user_id': line.user_id.id if line.user_id else False,
                    'team_id': rec.team_id.id if rec.team_id else False,
                    'expected_revenue': line.total_price or 0.0,
                    'date_open': rec.period_start,
                    'date_deadline': rec.period_end,
                    'sales_target_line_id': line.id,
                    'segment_id': [(6, 0, line.segment_id.ids)] if getattr(line, 'segment_id', False) else False,
                    'lead_type_id': [(6, 0, line.lead_type_id.ids)] if getattr(line, 'lead_type_id', False) else False,
                    'sub_segment_id': [(6, 0, line.sub_segment_id.ids)] if getattr(line, 'sub_segment_id', False) else False,
                    "expected_realization_date": line.expected_realization_date,
                    "tag_ids": [(6, 0, [tag.id])] if tag else False,


                }
                lead = self.env['crm.lead'].with_context(must_win=True).create(vals)
                # if you have crm.lead.line model:
                self.env["crm.lead.line"].create({
                    "lead_id": lead.id,
                    "product_id": line.product_id.id if line.product_id else False,
                    "description": line.description,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                })
        self.write({'state':'approved'})

    def action_reject(self):
        self.write({'state':'rejected'})
    def action_reset_draft(self):
        self.write({'state':'draft'})

    @api.depends('line_ids.achieved_value', 'target_value')
    def _compute_achievement_totals(self):
        for rec in self:
            total_achieved = sum(rec.line_ids.mapped('achieved_value'))
            rec.achievement_value = total_achieved
            pct = (total_achieved / rec.target_value * 100.0) if rec.target_value else 0.0
            rec.achievement_status = f"{pct:.2f}%"
            if pct > 60:
                rec.success_status = 'high'
            elif pct >= 40:
                rec.success_status = 'medium'
            else:
                rec.success_status = 'low'


    lead_count = fields.Integer(compute="_compute_counts")
    order_count = fields.Integer(compute="_compute_counts")

    def _compute_counts(self):
        for rec in self:
            rec.lead_count = self.env["crm.lead"].search_count([("id", "in", rec.line_ids.lead_ids.ids)])
            rec.order_count = self.env["sale.order"].search_count([("id", "in", rec.line_ids.sale_order_ids.ids)])

    def action_view_leads(self):
        return {
            "name": "Leads",
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "domain": [("sales_target_line_id", "in", self.line_ids.ids)],
            "view_mode": "list,form",
        }

    def action_view_orders(self):
        return {
            "name": "Quotations",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "domain": [("id", "in", self.line_ids.sale_order_ids.ids)],
            "view_mode": "list,form",
        }

    @api.model
    def create_lead_and_activity(self):
        current_date = datetime.today().date()
        sale_targets = self.env["sales.target"].search([
            ("state","=","approved"),
            ])
        lines = sale_targets.mapped("line_ids")
        filtered_lines = lines.filtered(
            lambda line: line.expected_realization_date and line.expected_realization_date < current_date and line.pending > 0 and not line.child_line_id 
        )
        for line in filtered_lines:
            line.create_auto_lead()
    


class SalesTargetLine(models.Model):
    _name = 'sales.target.line'
    _description = 'Sales Target Line'



    target_id = fields.Many2one('sales.target', string='Target', ondelete='cascade', required=True)
    child_line_id = fields.Many2one('sales.target.line', string='Child Line')
    parent_line_id = fields.Many2one('sales.target.line', string='Parent Line')

    name = fields.Char(string='Target Name', related='target_id.name', store=True)
    company_id = fields.Many2one('res.company', string='Company', related='target_id.company_id' , store=True)
    team_id = fields.Many2one('crm.team', string='Sales Team',  related='target_id.team_id' , store=True)
    team_member_ids = fields.Many2many('res.users', string='Team Members', related='target_id.team_id.member_ids')
    timespan = fields.Selection([('yearly','Yearly'), ('quarterly','Quarterly'), ('monthly','Monthly')], string='Time Span',  related='target_id.timespan' , store=True)
    period_start = fields.Date(string='Period Start', related='target_id.period_start' , store=True)
    period_end = fields.Date(string='Period End', compute='_compute_period_end' ,  related='target_id.period_end' , store=True)
    expected_realization_date = fields.Date(string='Expected Realization')
    
    achievement_status = fields.Char(string='Target Achievement Status (%)', compute='_compute_status', store=True)
    
    segment_id = fields.Many2many('crm.lead.segment', string='Segment')
    lead_type_id = fields.Many2many('crm.lead.type', string='Lead Type')
    sub_segment_id = fields.Many2many('crm.lead.subsegment', string='Sub-Segment')
    code = fields.Char(string='Code')
    
    partner_id = fields.Many2one('res.partner', string='Customer')
    user_id = fields.Many2one('res.users', string='Salesperson')
    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    quantity = fields.Float(string='Qty', default=1.0)
    unit_price = fields.Float(string='Amount')
    total_price = fields.Float(string='Total', compute='_compute_total_price', store=True)
    line_type = fields.Selection([('by_user', 'Current Month'), ('by_pending', 'Unachieved')], required=True,readonly=True, default='by_user', string='Target Type')

    prob_counter = fields.Float('Probability Counter (%)', compute='_compute_prob_counter')
    month = fields.Integer(string='Month', compute="_compute_month", store=True)
    @api.depends('expected_realization_date')
    def _compute_month(self):
        for rec in self:
            if rec.expected_realization_date:
                rec.month = rec.expected_realization_date.month
            else:
                rec.month = False

    # @api.depends('target_id.lead_ids','target_id.lead_ids' )
    def _compute_prob_counter(self):
        for rec in self:
            if rec.lead_ids:
                probabilites = rec.lead_ids.mapped('stage_id').mapped('prob_counter')
                rec.prob_counter = sum(probabilites) / len(probabilites)
            else:
                rec.prob_counter = 0

    @api.depends('quantity', 'unit_price')
    def _compute_total_price(self):
        for line in self:
            line.total_price = line.quantity * line.unit_price

    currency_id = fields.Many2one(related='target_id.currency_id', comodel_name='res.currency', store=True, readonly=True)

    achieved_value = fields.Float(string='Achieved Value', store=True, compute='_compute_achieved_value')
    pending = fields.Float(string='Pending', compute='_compute_pending', store=True)
    status = fields.Selection([('high','High'), ('medium','Medium'), ('low','Low')], compute='_compute_status')
    lead_ids = fields.One2many("crm.lead", "sales_target_line_id", string="Leads")
    sale_order_ids = fields.Many2many("sale.order", compute="_compute_sale_order_ids",string="Quotations", store=True)
    quote_generated = fields.Integer(
        compute="_compute_sale_order_ids", string="Quote Generated", store=True
    )
    quote_confirmed = fields.Integer(
        compute="_compute_sale_order_ids", string="Quote Confirmed", store=True
    )
    quote_pending = fields.Integer(
        compute="_compute_sale_order_ids", string="Quote Pending", store=True
    )
    @api.depends("lead_ids.order_ids")
    def _compute_sale_order_ids(self):
        for rec in self:
            orders = rec.lead_ids.mapped("order_ids")
            # raise UserError(orders)
            rec.sale_order_ids = orders
            rec.quote_generated = len(orders)
            rec.quote_confirmed = len(orders.filtered(lambda o: o.state in ["sale", "done"]))
            rec.quote_pending = len(orders.filtered(lambda o: o.state in ["draft", "sent"]))

    @api.depends("sale_order_ids.amount_total", "lead_ids")
    def _compute_achieved_value(self):
        for line in self:
            total = sum(order.amount_total for order in line.sale_order_ids if order.state=='sale')
            line.achieved_value = total
            
    @api.depends('total_price', 'achieved_value')
    def _compute_pending(self):
        for line in self:
            line.pending = (line.total_price or 0.0) - (line.achieved_value or 0.0)
            if line.pending<0:
                line.pending=0


    @api.depends('total_price', 'achieved_value')
    def _compute_status(self):
        for line in self:
            if not line.total_price:
                line.status = 'low'
                continue
            pct = (line.achieved_value / line.total_price) * 100.0
            line.achievement_status =  f"{pct:.2f}%"
            if pct > 60:
                line.status = 'high'
            elif pct >= 40:
                line.status = 'medium'
            else:
                line.status = 'low'
    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.unit_price = line.product_id.list_price
                line.description = line.product_id.name

    def action_view_orders(self, domain=False):
        """Helper method to open relevant sale orders"""
        self.ensure_one()
        return {
            "name": "Quotations / Orders",
            "type": "ir.actions.act_window",
            "res_model": "sale.order",
            "view_mode": "list",
            "domain": [("id", "in", self.sale_order_ids.ids)] + (domain or []),
            "target": "current",
        }

    def action_view_generated(self):
        return self.action_view_orders()

    def action_view_confirmed(self):
        return self.action_view_orders([("state", "in", ["sale"])])

    def action_view_pending(self):
        return self.action_view_orders([("state", "in", ["draft","sent"])])


    def create_auto_pending_line(self):
        self.ensure_one()
        new_line_vals = {
                "segment_id":self.segment_id.ids,
                "sub_segment_id":self.sub_segment_id.ids,
                "lead_type_id":self.lead_type_id.ids,
                "product_id":self.product_id.id,
                "partner_id":self.partner_id.id,
                "user_id":self.user_id.id,
                "description":self.description,
                "expected_realization_date":self.expected_realization_date + timedelta(days=30),
                "quantity":1,
                "unit_price":self.pending,
                "parent_line_id":self.id,
                "target_id":self.target_id.id,
                "line_type":"by_pending"
        }
        new_line = self.create(new_line_vals)
        self.write({
            "child_line_id":new_line.id
        })
        return new_line
    
    def create_lead(self):
        for line in self:
            rec = line.target_id
            state = self.env["crm.stage"].search([("name","like","Balance Target Lead")],limit=1)
            tag = self.env["crm.tag"].search([("name","like","Backup-Lead")],limit=1)
            
            
            vals = {
                'name': line.partner_id.name and f"{line.partner_id.name} - {rec.name}" or (rec.name or 'New Opportunity'),
                'type': 'opportunity',
                'partner_id': line.partner_id.id if line.partner_id else False,
                'user_id': line.user_id.id if line.user_id else False,
                'team_id': rec.team_id.id if rec.team_id else False,
                'expected_revenue': line.total_price or 0.0,
                'date_open': rec.period_start,
                'date_deadline': rec.period_end,
                'sales_target_line_id': line.id,
                'segment_id': [(6, 0, line.segment_id.ids)] if getattr(line, 'segment_id', False) else False,
                'lead_type_id': [(6, 0, line.lead_type_id.ids)] if getattr(line, 'lead_type_id', False) else False,
                'sub_segment_id': [(6, 0, line.sub_segment_id.ids)] if getattr(line, 'sub_segment_id', False) else False,
                "expected_realization_date": line.expected_realization_date,
                "tag_ids": [(6, 0, [tag.id])] if tag else False,
                
            }
            if state:
                vals["stage_id"] = state.id
            lead = self.env['crm.lead'].create(vals)
            # if you have crm.lead.line model:
            self.env["crm.lead.line"].create({
                "lead_id": lead.id,
                "product_id": line.product_id.id if line.product_id else False,
                "description": line.description,
                "quantity": line.quantity,
                "unit_price": line.unit_price,
            })

    def create_auto_lead(self):
        for rec in self:
            old_lead_id = rec.lead_ids
            new_line = rec.create_auto_pending_line()
            new_line.create_lead()
            new_line.create_activity()
            new_lead_id = new_line.lead_ids
            if not old_lead_id or not new_lead_id:
                continue
            old_lead_id.create_parent_child_relation(new_lead_id)
            

    def create_activity(self):
        for line in self:
            line.lead_ids.create_activity_target_line()
            
            