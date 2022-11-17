# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResPartnerInherit(models.Model):
    _inherit = "res.partner"
    
    id_adm = fields.Boolean(string='Administration', default=False, copy=False, store=True)
    
    @api.model
    def create(self, values):
        if self.env.company.id == 2:
            values['company_id'] = 2
        return super().create(values)