# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api, _
from odoo.tools import format_amount
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ProductTemplateInherit(models.Model):
    _inherit = "product.template"
    
    #Fields Autres
    check_adm = fields.Boolean(string='Payé par ADM',
                               default=False)
    contact_adm = fields.Many2one(string='Département(ADM)', comodel_name='res.partner')
    
    famille_produit = fields.Selection(selection=[('livraison_moorea','Livraison Moorea'),
                                                  ('livraison_tahiti','Livraison Tahiti'),
                                                  ('location','Locations'),
                                                  ('gardiennage_materiel','Gardiennage Matériel'),
                                                  ('depotage_empotage','Dépotage - Empotage'),
                                                  ('chargement_déchargement','Chargement - Déchargement'),
                                                  ('acconage','Acconage'),
                                                  ('bon_chauffeur','Bon chauffeur'),
                                                  ('gratuite','Gratuité'),
                                                  ('chauffeur','Chauffeur'),
                                                  ('assurance','Assurance'),
                                                  ('fut','Fût')],
                                       string='Famille', default='livraison_moorea')
    
    #Fields Normal
    tarif_normal = fields.Monetary(string='Tarif normal', default=0)
    tarif_minimum = fields.Monetary(string='Tarif minimum', default=0)
    
    #Fields RPA
    tarif_rpa = fields.Monetary(string='Tarif RPA', default=0)
    tarif_minimum_rpa = fields.Monetary(string='Tarif minimum RPA', default=0)
    
    #Ratio T/M
    ratio_terrestre = fields.Float(string='Terrestre(%)', help='La part du prix normal qui est pris pour la partie Terrestre en pourcentage', default=0.6, readonly=True, store=True)
    ratio_maritime = fields.Float(string='Maritime(%)', help='La part du prix normal qui est pris pour la partie maritime en pourcentage (1-Terrestre)', default=0.4, readonly=True, store=True)

    #Fields Maritime
    tarif_maritime = fields.Monetary(string='Tarif maritime', default=0, readonly=False)
    tarif_minimum_maritime = fields.Monetary(string='Tarif minimum maritime', default=0)
    
    #Fields Terrestre
    tarif_terrestre = fields.Monetary(string='Tarif terrestre', default=0, readonly=False)
    tarif_minimum_terrestre = fields.Monetary(string='Tarif minimum terrestre', default=0)
    
    def _compute_ratio_ter_mer(self, tarif_ter , tarif_normal):
        if tarif_ter and tarif_normal:
            # Ratio terrestre = tarif terrestre / tarif normal
            # Ratio maritime = 1 - ratio terrestre
            self.write({'ratio_terrestre': tarif_ter/tarif_normal,
                        'ratio_maritime' : 1 - (tarif_ter/tarif_normal) })
    
    #Terrestre 60% du prix normal & maritime 40% du prix normal
    @api.onchange('tarif_normal')
    def _get_default_revatua(self):
        # --- Check if revatua is activate ---#
        if self.env.company.revatua_ck:
            for record in self:
                # Si tarif normal existe on initialise tout les champs qui suivent (prix de vente,tarif terrester/maritime, RPA)
                if record.tarif_normal:
                    record.tarif_terrestre = record.tarif_normal * round(record.ratio_terrestre,2)
                    record.tarif_maritime = record.tarif_normal * round(record.ratio_maritime,2)
                    record.tarif_rpa = 100
                    record.list_price = record.tarif_normal
                # Si le prix normal est remis à 0 on retirer les valeurs des champs pour éviter des soucis de calcul par la suite
                else:
                    record.ratio_terrestre = 0.6
                    record.ratio_maritime = 0.4
                    record.list_price = 1
                    record.tarif_terrestre = 0
                    record.tarif_maritime = 0
                    record.tarif_rpa = 0
        else:
            _logger.error('Revatua not activate : product_template.py -> _get_default_revatua')
    
    #Ajout automatique de la taxes RPA si le champs RPA est remplis et met l'article en consu
    @api.onchange('tarif_rpa')
    def _add_rpa_taxe(self):
        # --- Check if revatua is activate ---#
        if self.env.company.revatua_ck:
            rpa = self.env['account.tax'].sudo().search([('name','=','RPA')])
            if rpa:
                for record in self:
                    if record.tarif_rpa:
                        record.taxes_id = [(4, rpa.id)]
                        record.detailed_type = "consu"
                    else:
                        if any(str(rpa.id) == str(taxe.id) for taxe in record.taxes_id):
                            record.taxes_id = [(3,rpa.id)]
            else:
                raise UserError('La taxe RPA est pas existant, la créer manuellement')
        else:
            _logger.error('Revatua not activate : product_template.py -> _add_rpa_taxe')
    
    # Recalcul des champs au changement du terrestre
    @api.onchange('tarif_terrestre')
    def _onchange_tarif_terrestre(self):
        if self.env.company.revatua_ck:
            for record in self:
                # Si tarif normal et tarif terrestre changer -> tarif maritime = tarif normal - tarif terrestre
                if record.tarif_normal:
                    record.tarif_maritime = record.tarif_normal - record.tarif_terrestre
                    record._compute_ratio_ter_mer(record.tarif_terrestre,record.tarif_normal)
                # Si pas de tarif normal et que tarif terrestre/maritime existe alors tarif normal&de vente = ter + mar
                elif not record.tarif_normal and record.tarif_maritime:
                    record.tarif_normal = record.tarif_terrestre + record.tarif_maritime
                    record.list_price = record.tarif_normal
                    record._compute_ratio_ter_mer(record.tarif_terrestre,record.tarif_terrestre + record.tarif_maritime)
                # Si le minimum est supérieur au maritime au moment du changement égaliser les deux
                if record.tarif_minimum_terrestre > record.tarif_terrestre:
                    record.tarif_minimum_terrestre = record.tarif_terrestre
                # Recalcul de la taxe
                record._construct_tax_string(record.tarif_normal)
        else:
            _logger.error('Revatua not activate : product_template.py -> _onchange_tarif_terrestre')
    
    # Recalcul des champs au changement du maritime
    @api.onchange('tarif_maritime')
    def _onchange_tarif_maritime(self):
        if self.env.company.revatua_ck:
            for record in self:
                # Si tarif normal et tarif terrestre changer -> tarif maritime = tarif normal - tarif terrestre
                if record.tarif_normal:
                    record.tarif_terrestre = record.tarif_normal - record.tarif_maritime
                    record._compute_ratio_ter_mer(record.tarif_normal - record.tarif_maritime,record.tarif_normal)
                # Si pas de tarif normal et que tarif terrestre/maritime existe alors tarif normal&de vente = ter + mar
                elif not record.tarif_normal and record.tarif_terrestre:
                    record.tarif_normal = record.tarif_terrestre + record.tarif_maritime
                    record.list_price = record.tarif_normal
                    record._compute_ratio_ter_mer(record.tarif_terrestre,record.tarif_terrestre + record.tarif_maritime)
                # Si le minimum est supérieur au maritime au moment du changement égaliser les deux
                if record.tarif_minimum_maritime > record.tarif_maritime:
                    record.tarif_minimum_maritime = record.tarif_maritime
                # Recalcul de la taxe
                record._construct_tax_string(record.tarif_normal)
        else:
            _logger.error('Revatua not activate : product_template.py -> _onchange_tarif_terrestre')
    
    # Vérifiction des minimum terrestre et maritime
    @api.onchange('tarif_minimum_maritime','tarif_minimum_terrestre')
    def _onchange_minimum_tarif(self):
        if self.env.company.revatua_ck:
            for record in self:
                if record.tarif_minimum_maritime and record.tarif_minimum_maritime > record.tarif_maritime:
                    raise UserError("Le prix minimum maritime ne peux pas être supérieur au prix normal maritime")
                if record.tarif_minimum_terrestre and record.tarif_minimum_terrestre > record.tarif_terrestre:
                    raise UserError("Le prix minimum terrestre ne peux pas être supérieur au prix normal terrestre")
        else:
            _logger.error('Revatua not activate : product_template.py -> _onchange_minimum_tarif')
                
    # Calcul de la tax sur le TTC de l'article
    def _construct_tax_string(self, price):
        # Override #
        currency = self.currency_id
        if self.tarif_terrestre:
            res = self.taxes_id.compute_all(price, product=self, partner=self.env['res.partner'], terrestre=self.tarif_terrestre)
        else:
            res = self.taxes_id.compute_all(price, product=self, partner=self.env['res.partner'])
        joined = []
        included = res['total_included']
        if currency.compare_amounts(included, price):
            joined.append(_('%s Incl. Taxes', format_amount(self.env, included, currency)))
        excluded = res['total_excluded']
        if currency.compare_amounts(excluded, price):
            joined.append(_('%s Excl. Taxes', format_amount(self.env, excluded, currency)))
        if joined:
            tax_string = f"(= {', '.join(joined)})"
        else:
            tax_string = " "
        return tax_string

class ProductProductInherit(models.Model):
    _inherit = "product.product"    
    
    def _compute_ratio_ter_mer(self, tarif_ter , tarif_normal):
        if tarif_ter and tarif_normal:
            # Ratio terrestre = tarif terrestre / tarif normal
            # Ratio maritime = 1 - ratio terrestre
            self.write({'ratio_terrestre': tarif_ter/tarif_normal,
                        'ratio_maritime' : 1 - (tarif_ter/tarif_normal) })
    
    #Terrestre 60% du prix normal & maritime 40% du prix normal
    @api.onchange('tarif_normal')
    def _get_product_default_revatua(self):
        # --- Check if revatua is activate ---#
        if self.env.company.revatua_ck:
            for record in self:
                # Si tarif normal existe on initialise tout les champs qui suivent (prix de vente,tarif terrester/maritime, RPA)
                if record.tarif_normal:
                    record.tarif_terrestre = record.tarif_normal * round(record.ratio_terrestre,2)
                    record.tarif_maritime = record.tarif_normal * round(record.ratio_maritime,2)
                    record.tarif_rpa = 100
                    record.lst_price = record.tarif_normal
                # Si le prix normal est remis à 0 on retirer les valeurs des champs pour éviter des soucis de calcul par la suite
                else:
                    record.ratio_terrestre = 0.6
                    record.ratio_maritime = 0.4
                    record.lst_price = 1
                    record.tarif_terrestre = 0
                    record.tarif_maritime = 0
                    record.tarif_rpa = 0
        else:
            _logger.error('Revatua not activate : product_template.py -> _get_default_revatua')
    
    # Exécute la méthod du template pour la rpa du product
    @api.onchange('tarif_rpa')
    def _add_rpa_taxe_product(self):
        for record in self:
            record.product_tmpl_id._add_rpa_taxe()
    
    # Recalcul des champs au changement du terrestre
    @api.onchange('tarif_terrestre')
    def _onchange_product_tarif_terrestre(self):
        if self.env.company.revatua_ck:
            for record in self:
                # Si tarif normal et tarif terrestre changer -> tarif maritime = tarif normal - tarif terrestre
                if record.tarif_normal:
                    record.tarif_maritime = record.tarif_normal - record.tarif_terrestre
                    record._compute_ratio_ter_mer(record.tarif_terrestre,record.tarif_normal)
                # Si pas de tarif normal et que tarif terrestre/maritime existe alors tarif normal&de vente = ter + mar
                elif not record.tarif_normal and record.tarif_maritime:
                    record.tarif_normal = record.tarif_terrestre + record.tarif_maritime
                    record.lst_price = record.tarif_normal
                    record._compute_ratio_ter_mer(record.tarif_terrestre,record.tarif_terrestre + record.tarif_maritime)
                # Si le minimum est supérieur au maritime au moment du changement égaliser les deux
                if record.tarif_minimum_terrestre > record.tarif_terrestre:
                    record.tarif_minimum_terrestre = record.tarif_terrestre
                # Recalcul de la taxe
                record.product_tmpl_id._construct_tax_string(record.tarif_normal)
        else:
            _logger.error('Revatua not activate : product_template.py -> _onchange_product_tarif_terrestre')
    
    # Recalcul des champs au changement du maritime
    @api.onchange('tarif_maritime')
    def _onchange_product_tarif_maritime(self):
        if self.env.company.revatua_ck:
            for record in self:
                # Si tarif normal et tarif terrestre changer -> tarif maritime = tarif normal - tarif terrestre
                if record.tarif_normal:
                    record.tarif_terrestre = record.tarif_normal - record.tarif_maritime
                    record._compute_ratio_ter_mer(record.tarif_normal - record.tarif_maritime,record.tarif_normal)
                # Si pas de tarif normal et que tarif terrestre/maritime existe alors tarif normal&de vente = ter + mar
                elif not record.tarif_normal and record.tarif_terrestre:
                    record.tarif_normal = record.tarif_terrestre + record.tarif_maritime
                    record.lst_price = record.tarif_normal
                    record._compute_ratio_ter_mer(record.tarif_terrestre,record.tarif_terrestre + record.tarif_maritime)
                # Si le minimum est supérieur au maritime au moment du changement égaliser les deux
                if record.tarif_minimum_maritime > record.tarif_maritime:
                    record.tarif_minimum_maritime = record.tarif_maritime
                # Recalcul de la taxe
                record.product_tmpl_id._construct_tax_string(record.tarif_normal)
        else:
            _logger.error('Revatua not activate : product_template.py -> _onchange_product_tarif_maritime')
        
        
    # Exécute la méthode de calcul du template pour recalculer les minimum du product
    @api.onchange('tarif_minimum_maritime','tarif_minimum_terrestre')
    def _onchange_product_minimum_tarif(self):
        for record in self:
            record.product_tmpl_id._onchange_minimum_tarif()
            