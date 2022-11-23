# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api
from odoo.addons.account.models.account_move import AccountMoveLine as AMoveLine

_logger = logging.getLogger(__name__)

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    
    r_volume = fields.Float(string='Volume Revatua (m³)', default=0, store=True, digits=(12, 3))
    r_weight = fields.Float(string='Volume weight (T)', default=0, store=True, digits=(12, 3))
    check_adm = fields.Boolean(string='Payé par ADM', related="product_id.check_adm")
    
    # Field from Sales line before recompute of value
    base_qty = fields.Float(string='Base Quantity', default=0, store=True)
    base_unit_price = fields.Float(string='Origin Unit Price', default=0, store=True)
    base_subtotal = fields.Float(string='Base Total HT', default=0, store=True)
    base_total = fields.Float(string='Base Total TTC', default=0, store=True)
    
    # -- RPA --#
    base_rpa = fields.Float(string='Base RPA', store=True)
    tarif_rpa = fields.Float(string='RPA', default=0, store=True)
    tarif_minimum_rpa = fields.Float(string='Minimum RPA', store=True)
    
    # -- Maritime --#
    base_maritime = fields.Float(string='Base Maritime', store=True)
    tarif_maritime = fields.Float(string='Maritime', default=0, store=True)
    tarif_minimum_maritime = fields.Float(string='Minimum Maritime', store=True)
    
    # -- Terrestre --#
    base_terrestre = fields.Float(string='Base Terrestre', store=True)
    tarif_terrestre = fields.Float(string='Terrestre', default=0, store=True)
    tarif_minimum_terrestre = fields.Float(string='Minimum Terrestre', store=True)
    
    # Tarif de ventes
    tarif_minimum = fields.Float(string='Prix Minimum', default=0, required=True, store=True)
    
# --------------------------------- Calcul de l'udm à utiliser  --------------------------------- #
    @api.onchange('r_volume','r_weight')
    def _onchange_update_qty(self):
        # --- Check if revatua is activate ---#
        if self.env.company.revatua_ck:
            m3 = self.env['uom.uom'].sudo().search([('name','=','m3')])
            t = self.env['uom.uom'].sudo().search([('name','=','T')])
            t_m3 = self.env['uom.uom'].sudo().search([('name','=','T/m³')])
            # Poid volumétrique
            if self.r_volume and self.r_weight and self.product_id.uom_id.id == m3.id:
                self.quantity = (self.r_volume + self.r_weight) / 2
                self.product_uom_id = t_m3 
            # Tonne
            elif self.r_weight and not self.r_volume:
                self.quantity = self.r_weight
                self.product_uom_id = t
            # Métre cube
            elif self.r_volume and not self.r_weight:
                self.quantity = self.r_volume
                self.product_uom_id = m3
            # Autres 
            else:
                self.quantity = 1
                self.product_uom_id = self.product_id.uom_id
        else:
            _logger.error('Revatua not activate : account_move_line.py -> _onchange_update_qty')

# --------------------------------- Calcules des lignes  --------------------------------- #
    @api.onchange('product_id')
    def _onchange_product_id(self):
        # Override #
        # --- Check if revatua is activate ---#
        if self.env.company.revatua_ck:
            res = super(AccountMoveLine,self)._onchange_product_id()
            for line in self:
                if line.product_id:
                    line.tarif_minimum = self.product_id.tarif_minimum
                    line.check_adm = self.product_id.check_adm
                    line.base_terrestre = self.product_id.tarif_terrestre
                    line.tarif_terrestre = self.product_id.tarif_terrestre
                    line.tarif_minimum_terrestre = self.product_id.tarif_minimum_terrestre
                    line.base_maritime = self.product_id.tarif_maritime
                    line.tarif_maritime = self.product_id.tarif_maritime
                    line.tarif_minimum_maritime = self.product_id.tarif_minimum_maritime
                    line.base_rpa = self.product_id.tarif_rpa
                    line.tarif_rpa = self.product_id.tarif_rpa
                    line.tarif_minimum_rpa = self.product_id.tarif_minimum_rpa
            return res
   
    # Méthode de calcule pour les tarifs par lignes
    def _compute_amount_base_revatua(self, base, qty, discount, mini_amount=0):
        """ Renvoie le montant de la part (terrestre,maritime,rpa) au changement de quantités
        
            param float base : Valeur de la base de la part à tester
            param float qty : la quantités
            param discount : 1 - (remise/100) -> si remise existant résultat < 0 sinon 1
            param mini_amount : Minimum que la part peut prendre
        """
        res = 0.0
        # Si minimum et Si part inférieur minimum alors res = minimum
        if mini_amount and ((base * discount) * qty) < mini_amount:
            res = mini_amount
        else :
            res = (base * discount) * qty
        return res
        
    # Calcul des part terrestre et maritime selon la quantité et la remise
    @api.onchange('quantity','discount')
    def _compute_revatua_part(self):
        if self.env.company.revatua_ck:
            for line in self:
                # Remise si existant : remise < 1 sinon = 1
                discount = 1-(line.discount/100)
                quantity = line.quantity
                # Facture normal Aremiti
                if not line.move_id.is_adm_invoice:
                    line.tarif_terrestre = line._compute_amount_base_revatua(line.base_terrestre, quantity, discount, line.tarif_minimum_terrestre)
                    line.tarif_maritime = line._compute_amount_base_revatua(line.base_maritime, quantity, discount, line.tarif_minimum_maritime)
                    line.tarif_rpa = line._compute_amount_base_revatua(line.base_rpa, quantity, discount, line.tarif_minimum_rpa)
                # Facture ADM
                else:
                    # Partie administration
                    rpa = self.env['account.tax'].sudo().search([('name','=','RPA')])
                    if line.check_adm:
                        line.tarif_maritime = line._compute_amount_base_revatua(line.base_maritime, quantity, discount, line.tarif_minimum_maritime)
                        line.tarif_rpa = line._compute_amount_base_revatua(line.base_rpa, quantity, discount, line.tarif_minimum_rpa)
                        line.tarif_terrestre = 0.0
                        line.tax_ids = [(6,0,[rpa.id])]
        else:
            _logger.error('Revatua not activate : sale_order_line.py -> _compute_revatua_part')
# --------------------------------- Modification des méthode de calculs des taxes et sous totaux  --------------------------------- #
    # --------------------------------- Price Total & Subtotal  --------------------------------- #
    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None, terrestre=None, maritime=None, adm=None):
        self.ensure_one()
        return self._get_price_total_and_subtotal_model(
            price_unit=self.price_unit if price_unit is None else price_unit,
            quantity=self.quantity if quantity is None else quantity,
            discount=self.discount if discount is None else discount,
            currency=self.currency_id if currency is None else currency,
            product=self.product_id if product is None else product,
            partner=self.partner_id if partner is None else partner,
            taxes=self.tax_ids if taxes is None else taxes,
            move_type=self.move_id.move_type if move_type is None else move_type,
            terrestre=self.tarif_terrestre if terrestre is None else terrestre,
            maritime=self.tarif_maritime if maritime is None else maritime,
            adm=self.move_id.is_adm_invoice if adm is None else adm,
        )
    
    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type, terrestre, maritime, adm):
        ''' This method is used to compute 'price_total' & 'price_subtotal'.

        :param price_unit:  The current price unit.
        :param quantity:    The current quantity.
        :param discount:    The current discount.
        :param currency:    The line's currency.
        :param product:     The line's product.
        :param partner:     The line's partner.
        :param taxes:       The applied taxes.
        :param move_type:   The type of the move.
        :return:            A dictionary containing 'price_subtotal' & 'price_total'.
        '''
        res = {}
                # ----- Modification du prix unitaire pour chaque état possible d'une facture Aremiti ----- #
# ----------------------------------------------------------------------------------------------------------------------------------- #
        if self.env.company.revatua_ck:
            # Facture ADM administration
            if self.move_id.is_adm_invoice:
                price_unit = self.base_maritime
            # Facture ADM client
            elif not self.tarif_maritime and self.tarif_terrestre:
                price_unit = self.base_terrestre
            # Facture Aremiti normal
            elif self.tarif_maritime and self.tarif_terrestre:
                price_unit = self.base_maritime + self.base_terrestre
            # Facture normal
            else:
                price_unit = price_unit
# ----------------------------------------------------------------------------------------------------------------------------------- #
                # ----- Modification du prix unitaire pour chaque état possible d'une facture Aremiti ----- #

        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
# ----- Ajout du discount et du terrestre pour simplifier le calculs des taxes (car taxes s'applique uniquement à la part terrestre)
            if self.env.company.revatua_ck:
                taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'), terrestre=terrestre, maritime=maritime, adm=adm) #
            else:
                taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res
    
    # Erreur de création
    @api.model
    def create(self, vals_list):
        res = super(AMoveLine,self).create(vals_list)
        return res
    
# --------------------------------- Méthode de récupération des champs du model : account.admg  --------------------------------- #  

    def _prepare_line_admg(self, sequence=1):
        self.ensure_one()
        vals = {
            'sequence': sequence,
            'display_type': self.display_type,
            'product_id': self.product_id,
            'r_volume': self.r_volume,
            'r_weight': self.r_weight,
            'quantity': self.quantity,
            'price_subtotal': self.price_subtotal,
            'tax_id': [(6,0,[137])], #RPA id
            'price_unit': self.price_unit,
            'tarif_terrestre': self.tarif_terrestre,
            'tarif_maritime': self.tarif_maritime,
            'tarif_rpa': self.tarif_rpa,
            'price_total': self.price_total,
        }
        return vals