# -*- coding: utf-8 -*-
import logging
from odoo import fields, models, api
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class AccountMoveAdm(models.Model):
    _name = 'account.move.adm'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Facture global ADM'
    
    name = fields.Char(string='Numéro', store=True, readonly=True, copy=False)
    start_date = fields.Date(string='Du', store=True, copy=False, tracking=True)
    end_date = fields.Date(string='Au', store=True, copy=False, tracking=True)
    partner_id = fields.Many2one(string='Client', store=True, comodel_name='res.partner', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True, states={'draft': [('readonly', False)], 'refused': [('readonly', False)]}, default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', string='Currency')
    note_adm = fields.Html(string='Note')
    state = fields.Selection(string='État de facturation', selection=[('draft','Brouillons'),
                                                                      ('done','Confirmé'),
                                                                      ('in_payment','Paiement Partiel'),
                                                                      ('payed','Paiement complet')]
                             ,store=True, default='draft', copy=False, tracking=True)
    # M2m/O2m
    invoice_line_ids = fields.Many2many(string='Factures ADM', store=True, comodel_name='account.move')
    invoice_ids = fields.One2many(string='Factures lié ADM', store=True, comodel_name='account.move', inverse_name='adm_group_id')
    product_line_ids = fields.One2many(string='Articles', store=True, comodel_name='account.move.adm.line', inverse_name='invoice_id')
    
    # Total
    total_ht = fields.Float(string='Total HT', store=True, copy=False)
    total_rpa = fields.Float(string='Total RPA', store=True, copy=False)
    total_ttc = fields.Float(string='Total TTC', store=True, copy=False, help='Total RPA + Total HT')
    
    @api.model_create_multi
    def create(self, vals_list):
        # OVERRIDE
        res = super(AccountMoveAdm, self).create(vals_list)
        if not res['name']:
            sequence = self.env["ir.sequence"].next_by_code("account.move.adm")
            res['name'] = sequence or "/"
        return res
    
    @api.onchange('start_date','end_date')
    def _onchange_admg_date(self):
        for record in self:
            adms = []
            if record.start_date:
                moves = record.env['account.move'].search([('is_adm_invoice','=',True)])
                for move in moves:
                    if move.invoice_date and move.state not in ('draft','cancel') and not move.adm_group_id:
                        if record.end_date:
                            if record.end_date <= record.start_date:
                                raise ValidationError('La date de fin ne peut pas être inférieur à la date de départ')
                            else: 
                                if move.invoice_date >= record.start_date and move.invoice_date <= record.end_date:
                                   adms.append(move.id)
                        else:
                            if move.invoice_date >= record.start_date:
                               adms.append(move.id)
            record.invoice_line_ids = [(6,0,adms)]
            
    # Build des lignes à facturé                         
    @api.onchange('invoice_line_ids')
    def _onchange_invoice_list_update_detail(self):
        for record in self:
            record.product_line_ids = [(5,0,0)]
            moves = record.invoice_line_ids
            adm_line = []
            sequence = 1
            for move in moves:
                _logger.error(move.name)
                adm_line.append((0,0,move._add_move_line(sequence=sequence)),)
                sequence += 1
                if move.invoice_line_ids:
                    for line in move.invoice_line_ids:
                        adm_line.append((0,0,line._prepare_line_admg(sequence=sequence)),)
                        sequence += 1
            record.product_line_ids = adm_line
    
    # Calcul des totaux
    @api.onchange('product_line_ids')
    def _compute_total(self):
        for record in self:
            total_ht = 0
            total_rpa = 0
            total_ttc = 0
            for line in record.product_line_ids:
                total_ht += line.price_subtotal
                total_rpa += line.tarif_rpa
                total_ttc += line.price_total
        record.write({
            'total_ht' : total_ht,
            'total_rpa' : total_rpa,
            'total_ttc' : total_ttc,
        })
    
    def action_confirm_adm(self):
        _logger.error('action_confirm_adm')
        for record in self:
            for line in record.invoice_line_ids:
                adm = record.env['account.move'].sudo().search([('id','=',line.id)])
                if adm and not adm.adm_group_id:
                    adm.write({'adm_group_id': record.id})
            record.write({'state':'done'})
    
    # changement d'état sur létat du paiement
    @api.onchange('invoice_ids.payment_state')
    def _onchange_paiement_state(self):
        for record in self:
            if record.invoice_ids:
                if all(line.payment_state == 'paid' for line in record.invoice_ids):
                    record.write({'state':'payed'})
                elif any(line.payment_state == 'paid' for line in record.invoice_ids):
                    record.write({'state':'in_payment'})
                else:
                    continue
                
            
#--------- LINE ---------#   
class AccountMoveAdmLine(models.Model):
    _name = 'account.move.adm.line'
    _description = 'Ligne des facture grouper pour les administrations'
    
    invoice_id = fields.Many2one(string='Facture globale', comodel_name='account.move.adm')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id', string='Devise')
    # Article
    sequence = fields.Integer(string='Sequence', default=1)
    name = fields.Char(string='Description')
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    product_id = fields.Many2one(
        'product.product', string='Product', domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        change_default=True, ondelete='restrict', check_company=True)  # Unrequired company
    product_template_id = fields.Many2one(
        'product.template', string='Product Template',
        related="product_id.product_tmpl_id", domain=[('sale_ok', '=', True)])
    quantity = fields.Float(string='Quantité', default=0.0, store=True)
    
    # Prix
    price_unit = fields.Float('Unit Price', required=True, digits='Product Price', default=0.0)
    currency_id = fields.Many2one(related='invoice_id.currency_id', depends=['invoice_id.currency_id'], store=True, string='Currency')
    price_subtotal = fields.Monetary(string='Subtotal', store=True)
    tax_id = fields.Many2many('account.tax', string='Taxes', context={'active_test': False})
    price_tax = fields.Float(string='Total Tax', store=True)
    price_total = fields.Monetary(string='Total', store=True)
    
    # Revatua
    tarif_rpa = fields.Float(string='RPA', default=0, required=True, store=True)
    tarif_maritime = fields.Float(string='Maritime', default=0, required=True, store=True)
    tarif_terrestre = fields.Float(string='Terrestre', default=0, required=True, store=True)
    r_volume = fields.Float(string='Volume Revatua (m³)', default=0, store=True, digits=(12, 3))
    r_weight = fields.Float(string='Volume weight (T)', default=0, store=True, digits=(12, 3))
    check_adm = fields.Boolean(string='Payé par ADM', related="product_id.check_adm")