# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ResPartnerInherit(models.Model):
    _inherit = "res.partner"
    
    id_adm = fields.Boolean(string='Administration', default=False, copy=False, store=True)
    
    @api.model
    def create(self, values):
        if self.env.company and self.env.company.revatua_ck:
            values['company_id'] = self.env.company.id
        return super().create(values)