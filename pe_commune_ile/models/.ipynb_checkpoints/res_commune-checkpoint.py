# -*- coding: utf-8 -*-

from odoo import fields, models, api

class ContactCommune(models.Model):
    _name = "res.commune"
    _description = "Commune des îles"
    _order = 'sequence asc'
    
    name = fields.Char(string='Nom')
    sequence = fields.Integer(default=10)
    ile_id = fields.Many2one(string='Île/Archipel', comodel_name='res.country.state', required=True)

class ResCountryStateInherit(models.Model):
    _inherit = "res.country.state"
    
    commune_ids = fields.One2many(string='Communes', comodel_name='res.commune', inverse_name='ile_id')