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

# --------------------------------- Calcul des lignes comptable  --------------------------------- #

    @api.onchange('quantity', 'discount', 'price_unit', 'tax_ids')
    def _onchange_price_subtotal(self):
        ### Override ###
        for line in self:
            if not line.move_id.is_invoice(include_receipts=True):
                continue
            # --- Check if revatua is activate ---#
            if self.env.company.revatua_ck:
                # Pour la facture Administration article ADM
                if line.check_adm and line.move_id.is_adm_invoice:
                    if line.base_unit_price:
                        price_adm = line.base_maritime
                        if price_adm < line.product_id.tarif_minimum_maritime:
                            price_adm = line.product_id.tarif_minimum_maritime
                        line.update(line._get_price_total_and_subtotal(price_unit=price_adm) )
                        line.update(line._get_fields_onchange_subtotal())
                        
                # Pour la facture client article ADM
                elif line.check_adm and not line.move_id.is_adm_invoice:
                    if line.base_unit_price:
                        price_custo = line.base_terrestre
                        if price_custo < line.product_id.tarif_minimum_terrestre:
                            price_custo = line.product_id.tarif_minimum_terrestre
                        line.update(line._get_price_total_and_subtotal(price_unit=price_custo) )
                        line.update(line._get_fields_onchange_subtotal())
                else:
                    line.update(line._get_price_total_and_subtotal())
                    line.update(line._get_fields_onchange_subtotal())
                    line.update(line._get_tarif_values())
                    _logger.error('###################################################################################################')
                    _logger.error('###################################################################################################')
                    _logger.error('###################################################################################################')
            # Autres
            else:
                 _logger.error('Revatua not activate : account_move_line.py -> _onchange_price_subtotal')
                 line.update(line._get_price_total_and_subtotal())
                 line.update(line._get_fields_onchange_subtotal())
    
    def _get_tarif_values(self):
        self.ensure_one()
        product = self.product_id
        quantity = self.quantity
        discount = self.discount
        terrestre = self.base_terrestre * quantity
        maritime = self.base_maritime * quantity
        min_ter = product.tarif_minimum_terrestre
        min_mar = product.tarif_minimum_maritime
        vals_ter = 0
        vals_mar = 0
        ter_min = False
        if self.env.company.revatua_ck:
            if terrestre < min_ter:
                vals_ter = min_ter
            else:
                vals_ter = terrestre
                
            if maritime < min_mar:
                vals_mar = min_mar
            else:
                vals_mar = maritime
                
            if discount:
                vals_ter = vals_ter * (1 - (discount / 100.0))
                vals_mar = vals_mar * (1 - (discount / 100.0))
                if vals_ter < min_ter:
                    vals_ter = min_ter
                if vals_mar < min_mar:
                    vals_mar = min_mar
                    
            if (vals_ter + vals_mar) > self.price_subtotal:
                if not ter_min:
                    vals_ter = self.price_subtotal - vals_mar
                else:
                    vals_mar = self.price_subtotal - vals_ter
            
        else:
            _logger.error('Revatua not activate : account_move_line.py -> _get_tarif_values')
            
        vals = {
            'tarif_terrestre' : vals_ter,
            'tarif_maritime' : vals_mar,
            'tarif_rpa' : self.base_rpa * quantity,
        }
        
        return vals
        
# --------------------------------- Modification des méthode de calculs des taxes et sous totaux  --------------------------------- #
    # --------------------------------- Price Total & Subtotal  --------------------------------- #
    def _get_price_total_and_subtotal(self, price_unit=None, quantity=None, discount=None, currency=None, product=None, partner=None, taxes=None, move_type=None, terrestre=None):
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
        )
    
    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type, terrestre):
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

        # Compute 'price_subtotal'.
        line_discount_price_unit = price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
# -----Ajout du discount et du terrestre pour simplifier le calculs des taxes (car taxes s'applique uniquement à la part terrestre)
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'), terrestre=terrestre)
            _logger.error('total_sub : %s ' % taxes_res)
            res['price_subtotal'] = taxes_res['total_excluded']
            res['price_total'] = taxes_res['total_included']
        else:
            res['price_total'] = res['price_subtotal'] = subtotal
        #In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res
    
    # --------------------------------- Field onchange balance  --------------------------------- #
    def _get_fields_onchange_balance(self, quantity=None, discount=None, amount_currency=None, move_type=None, currency=None, taxes=None, price_subtotal=None,terrestre=None, force_computation=False):
        self.ensure_one()
        return self._get_fields_onchange_balance_model(
            quantity=self.quantity if quantity is None else quantity,
            discount=self.discount if discount is None else discount,
            amount_currency=self.amount_currency if amount_currency is None else amount_currency,
            move_type=self.move_id.move_type if move_type is None else move_type,
            currency=(self.currency_id or self.move_id.currency_id) if currency is None else currency,
            taxes=self.tax_ids if taxes is None else taxes,
            price_subtotal=self.price_subtotal if price_subtotal is None else price_subtotal,
            terrestre=self.tarif_terrestre if terrestre is None else terrestre,
            force_computation=force_computation,
        )
    
    @api.model
    def _get_fields_onchange_balance_model(self, quantity, discount, amount_currency, move_type, currency, taxes, price_subtotal, terrestre, force_computation=False):
        ''' This method is used to recompute the values of 'quantity', 'discount', 'price_unit' due to a change made
        in some accounting fields such as 'balance'.

        This method is a bit complex as we need to handle some special cases.
        For example, setting a positive balance with a 100% discount.

        :param quantity:        The current quantity.
        :param discount:        The current discount.
        :param amount_currency: The new balance in line's currency.
        :param move_type:       The type of the move.
        :param currency:        The currency.
        :param taxes:           The applied taxes.
        :param price_subtotal:  The price_subtotal.
        :return:                A dictionary containing 'quantity', 'discount', 'price_unit'.
        '''
        if move_type in self.move_id.get_outbound_types():
            sign = 1
        elif move_type in self.move_id.get_inbound_types():
            sign = -1
        else:
            sign = 1
        amount_currency *= sign

        # Avoid rounding issue when dealing with price included taxes. For example, when the price_unit is 2300.0 and
        # a 5.5% price included tax is applied on it, a balance of 2300.0 / 1.055 = 2180.094 ~ 2180.09 is computed.
        # However, when triggering the inverse, 2180.09 + (2180.09 * 0.055) = 2180.09 + 119.90 = 2299.99 is computed.
        # To avoid that, set the price_subtotal at the balance if the difference between them looks like a rounding
        # issue.
        if not force_computation and currency.is_zero(amount_currency - price_subtotal):
            return {}

        taxes = taxes.flatten_taxes_hierarchy()
        if taxes and any(tax.price_include for tax in taxes):
            # Inverse taxes. E.g:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 110           | 10% incl, 5%  |                   | 100               | 115
            # 10            |               | 10% incl          | 10                | 10
            # 5             |               | 5%                | 5                 | 5
            #
            # When setting the balance to -200, the expected result is:
            #
            # Price Unit    | Taxes         | Originator Tax    |Price Subtotal     | Price Total
            # -----------------------------------------------------------------------------------
            # 220           | 10% incl, 5%  |                   | 200               | 230
            # 20            |               | 10% incl          | 20                | 20
            # 10            |               | 5%                | 10                | 10
            force_sign = -1 if move_type in ('out_invoice', 'in_refund', 'out_receipt') else 1
    # -----Ajout du discount et du terrestre pour simplifier le calculs des taxes (car taxes s'applique uniquement à la part terrestre)
            taxes_res = taxes._origin.with_context(force_sign=force_sign).compute_all(amount_currency, currency=currency, handle_price_include=False, discount=discount, terrestre=terrestre)
            for tax_res in taxes_res['taxes']:
                tax = self.env['account.tax'].browse(tax_res['id'])
                if tax.price_include:
                    amount_currency += tax_res['amount']

        discount_factor = 1 - (discount / 100.0)
        if amount_currency and discount_factor:
            # discount != 100%
            vals = {
                'quantity': quantity or 1.0,
                'price_unit': amount_currency / discount_factor / (quantity or 1.0),
            }
        elif amount_currency and not discount_factor:
            # discount == 100%
            vals = {
                'quantity': quantity or 1.0,
                'discount': 0.0,
                'price_unit': amount_currency / (quantity or 1.0),
            }
        elif not discount_factor:
            # balance of line is 0, but discount  == 100% so we display the normal unit_price
            vals = {}
        else:
            # balance is 0, so unit price is 0 as well
            vals = {'price_unit': 0.0}
        return vals
    
    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        ACCOUNTING_FIELDS = ('debit', 'credit', 'amount_currency')
        BUSINESS_FIELDS = ('price_unit', 'quantity', 'discount', 'tax_ids')
        
        for vals in vals_list:
            move = self.env['account.move'].browse(vals['move_id'])
            vals.setdefault('company_currency_id', move.company_id.currency_id.id) # important to bypass the ORM limitation where monetary fields are not rounded; more info in the commit message

            # Ensure balance == amount_currency in case of missing currency or same currency as the one from the
            # company.
            currency_id = vals.get('currency_id') or move.company_id.currency_id.id
            if currency_id == move.company_id.currency_id.id:
                balance = vals.get('debit', 0.0) - vals.get('credit', 0.0)
                vals.update({
                    'currency_id': currency_id,
                    'amount_currency': balance,
                })
            else:
                vals['amount_currency'] = vals.get('amount_currency', 0.0)

            if move.is_invoice(include_receipts=True):
                currency = move.currency_id
                partner = self.env['res.partner'].browse(vals.get('partner_id'))
                taxes = self.new({'tax_ids': vals.get('tax_ids', [])}).tax_ids
                tax_ids = set(taxes.ids)
                taxes = self.env['account.tax'].browse(tax_ids)
                _logger.error(vals)
                # Ensure consistency between accounting & business fields.
                # As we can't express such synchronization as computed fields without cycling, we need to do it both
                # in onchange and in create/write. So, if something changed in accounting [resp. business] fields,
                # business [resp. accounting] fields are recomputed.
                if any(vals.get(field) for field in ACCOUNTING_FIELDS):
                    price_subtotal = self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                        terrestre = vals.get('tarif_terrestre', 0.0),
                    ).get('price_subtotal', 0.0)
                    vals.update(self._get_fields_onchange_balance_model(
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        vals['amount_currency'],
                        move.move_type,
                        currency,
                        taxes,
                        price_subtotal,
                        terrestre = vals.get('tarif_terrestre', 0.0),
                    ))
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                        terrestre = vals.get('tarif_terrestre', 0.0),
                    ))
                elif any(vals.get(field) for field in BUSINESS_FIELDS):
                    vals.update(self._get_price_total_and_subtotal_model(
                        vals.get('price_unit', 0.0),
                        vals.get('quantity', 0.0),
                        vals.get('discount', 0.0),
                        currency,
                        self.env['product.product'].browse(vals.get('product_id')),
                        partner,
                        taxes,
                        move.move_type,
                        terrestre = vals.get('tarif_terrestre', 0.0),
                    ))
                    vals.update(self._get_fields_onchange_subtotal_model(
                        vals['price_subtotal'],
                        move.move_type,
                        currency,
                        move.company_id,
                        move.date,
#                         terrestre = vals.get('tarif_terrestre', 0.0),
                    ))

        lines = super(AMoveLine, self).create(vals_list)

        moves = lines.mapped('move_id')
        if self._context.get('check_move_validity', True):
            moves._check_balanced()
        moves.filtered(lambda m: m.state == 'posted')._check_fiscalyear_lock_date()
        lines.filtered(lambda l: l.parent_state == 'posted')._check_tax_lock_date()
        moves._synchronize_business_models({'line_ids'})
        #logger.Test()
        return lines
    
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
        #_logger.error('Seq : %s | Ligne: %s' % (sequence,vals))
        return vals