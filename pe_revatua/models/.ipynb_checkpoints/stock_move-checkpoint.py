# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)

class StockMoveInherit(models.Model):
    _inherit = "stock.move"
    
    tarif_rpa = fields.Float(string='RPA', related='sale_line_id.tarif_rpa', required=True)
    tarif_maritime = fields.Float(string='Maritime', related='sale_line_id.tarif_maritime', required=True)
    tarif_terrestre = fields.Float(string='Terrestre', related='sale_line_id.tarif_terrestre', required=True)
    r_volume = fields.Float(string='Volume Revatua (m³)', related='sale_line_id.r_volume', digits=(12, 3))
    r_weight = fields.Float(string='Volume weight (T)', related='sale_line_id.r_weight', digits=(12, 3))
