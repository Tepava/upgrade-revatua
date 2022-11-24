# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api

class StockMoveInherit(models.Model):
    _inherit = "stock.move"
    
    tarif_rpa = fields.Float(string='RPA')
    tarif_maritime = fields.Float(string='Maritime')
    tarif_terrestre = fields.Float(string='Terrestre')
    r_volume = fields.Float(string='Volume Revatua (m³)', digits=(12, 3))
    r_weight = fields.Float(string='Volume weight (T)', digits=(12, 3))
    
    @api.model_create_multi
    def create(self, values):
        res = super(StockMoveInherit, self).create(values)
        for res_line in res:
            if res_line.move_dest_ids and self.env.company.revatua_ck:
                if not res_line.r_volume and not res_line.r_weight and not res_line.tarif_terrestre and not res_line.tarif_maritime and not res_line.tarif_rpa:
                    destination = res_line.move_dest_ids
                    vals = {
                        'r_volume': destination.r_volume,
                        'r_weight': destination.r_weight,
                        'tarif_terrestre': destination.tarif_terrestre,
                        'tarif_maritime': destination.tarif_maritime,
                        'tarif_rpa': destination.tarif_rpa,
                    }
                    res_line.update(vals)
        return res