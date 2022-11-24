# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api

_logger = logging.getLogger(__name__)

class StockRule(models.Model):
    _inherit = 'stock.rule'
    
    # Méthode appeler pour chargement des mouvements de stock (stock.move)
    def _get_stock_move_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        move_values = super()._get_stock_move_values(product_id, product_qty, product_uom, location_id, name, origin, company_id, values)
        if self.env.company.revatua_ck:
            move_values['tarif_rpa'] = values.get('tarif_rpa')
            move_values['tarif_maritime'] = values.get('tarif_maritime')
            move_values['tarif_terrestre'] = values.get('tarif_terrestre')
            move_values['r_volume'] = values.get('r_volume')
            move_values['r_weight'] = values.get('r_weight')
        return move_values