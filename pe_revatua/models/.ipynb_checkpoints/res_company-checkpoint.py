# -*- coding: utf-8 -*-
from odoo import fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    revatua_ck = fields.Boolean(string="Activer fonctionnalité Revatua",
        help="Débloque les modes de calculs dans le modules ventes pour les connaissements",
        default=False,
    )

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    revatua_ck = fields.Boolean(related="company_id.revatua_ck", readonly=False)