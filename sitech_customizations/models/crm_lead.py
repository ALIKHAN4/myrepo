from odoo import models, fields ,api
from odoo.exceptions import UserError



class CrmLead(models.Model):
    _inherit = 'crm.lead'

    segment_id = fields.Many2many('crm.lead.segment', string='Segment')
    lead_type_id = fields.Many2many('crm.lead.type', string='Lead Type')
    sub_segment_id = fields.Many2many('crm.lead.subsegment', string='Sub-Segment')
    code = fields.Char(string='Code')
    line_items = fields.One2many('crm.lead.line', 'lead_id', string='Line Items')
    sales_target_line_id = fields.Many2one('sales.target.line', string='Sales Target Line', index=True)
    
    expected_realization_date = fields.Date(string='Expected Realization')
    parent_lead_id = fields.Many2one("crm.lead",string="Parent Lead")
    child_lead_id = fields.Many2one("crm.lead",string="Child Lead")
    all_child_lead_ids = fields.Many2many(
        "crm.lead",
        "crm_lead_child_rel",              # relation table name
        "parent_lead_id",                  # column for the current lead
        "child_lead_id",                   # column for the related lead
        string="All Child Leads",
        compute="compute_child_lead_ids",
        store=False,
        readonly=True
    )
    lead_children = fields.Integer(string='Lead Children',compute="compute_child_lead_ids",store=False,readonly=True)

    sale_target_count = fields.Integer(compute="_compute_sale_target_count")

    @api.depends("sales_target_line_id")
    def _compute_sale_target_count(self):
        for rec in self:
            rec.sale_target_count = self.env["sales.target"].search_count([("id", "=", rec.sales_target_line_id.target_id.id)])


    @api.depends("child_lead_id")
    def compute_child_lead_ids(self):
        for rec in self:
            all_children = rec.recursive_fetch_children()
            if all_children:
                rec.all_child_lead_ids = all_children
                rec.lead_children = len(all_children)
            else:
                rec.all_child_lead_ids = False
                rec.lead_children = False
                
    @api.model_create_multi
    def create(self, vals_list):
        backup_lead_tag = self.env['crm.tag'].search([('name', 'like', 'Backup-Lead')], limit=1)
        must_win_tag = self.env['crm.tag'].search([('name', 'like', 'Must Win')], limit=1)
        
        for vals in vals_list:
            if self.env.context.get('must_win'):
                vals['tag_ids'] = [(6, 0, [must_win_tag.id])] if must_win_tag else False
            elif backup_lead_tag:
                segment_ids = [value[1] for value in vals.get('segment_id')] if vals.get('segment_id') else []
                sub_segment_ids = [value[1] for value in vals.get('sub_segment_id')] if vals.get('sub_segment_id') else []
                customer = vals.get('partner_id')
                salesperson = vals.get('user_id')
                line_items = vals.get('line_items')
                product_ids = [line_item[2].get('product_id') for line_item in line_items] if line_items else []
                date = vals.get('expected_realization_date') if vals.get('expected_realization_date') else False
                
                sales_target_line = self.env['sales.target.line'].search([
                     '|', '|', '|', '|',
                    ('segment_id', 'in', segment_ids),
                    ('sub_segment_id', 'in', sub_segment_ids), 
                    ('partner_id', '=', customer), 
                    ('user_id', '=', salesperson), 
                    ('product_id', 'in', product_ids), 
                    ('month', '=', date.month), 
                    ])
                if sales_target_line:
                    vals['sales_target_line_id'] = sales_target_line.id
                
                vals['tag_ids'] = [(6, 0, [backup_lead_tag.id])]
                    
        return super().create(vals_list)
    
    
    def write(self, vals):
        if 'segment_id' in vals and 'sub_segment_id' in vals and 'lead_type_id' in vals and 'partner_id' in vals and 'user_id' in vals and 'line_items' in vals:
            for record in self:
                segment_ids = [value[1] for value in vals.get('segment_id')]
                sub_segment_ids = [value[1] for value in vals.get('sub_segment_id')]
                lead_type_ids = [value[1] for value in vals.get('lead_type_id')]
                customer = vals.get('partner_id')
                salesperson = vals.get('user_id')
                line_items = vals.get('line_items')
                product_ids = [line_item[2].get('product_id') for line_item in line_items] if line_items else []
                
                sales_target_line = self.env['sales.target.line'].search([
                    ('segment_id', 'in', segment_ids),
                    ('sub_segment_id', 'in', sub_segment_ids), 
                    ('lead_type_id', 'in', lead_type_ids), 
                    ('partner_id', '=', customer), 
                    ('user_id', '=', salesperson), 
                    ('product_id', 'in', product_ids), 
                    ])
                if sales_target_line:
                    vals['sales_target_line_id'] = sales_target_line.id

        return super().write(vals)

    
    def create_parent_child_relation(self,new_lead_id):
        for old_lead in self:
            new_lead_id.write({"parent_lead_id":old_lead.id})
            old_lead.write({"child_lead_id":new_lead_id.id})
    
    def recursive_fetch_children(self, visited=None):
        self.ensure_one()
        if visited is None:
            visited = self.env['crm.lead']

        if self.child_lead_id and self.child_lead_id not in visited:
            visited |= self.child_lead_id
            visited |= self.child_lead_id.recursive_fetch_children(visited)

        return visited

    def action_view_lead_children(self):
        
        return {
            "name": "All Child Leads",
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "domain": [("id", "=", self.all_child_lead_ids.ids)],
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
    
    def create_activity_target_line(self):
        for rec in self:
            rec.activity_schedule(
                activity_type_id=self.env.ref("mail.mail_activity_data_todo").id,
                summary="Balance Target Escalation",
                note="A balance target lead has been created because the realization month has passed and the target amount is still pending. Please take follow-up action.",
                date_deadline=fields.Date.today(),
                user_id=rec.user_id.id or self.env.user.id,
            )
                        