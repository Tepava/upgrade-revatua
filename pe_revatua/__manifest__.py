# -*- coding: utf-8 -*-
{
    "name": "Revatua",
    "summary": "Ajout des fonctionnalité en liens à Revatua (création de connaissement, visualisation des planing bateau, etc...)",
    "version": "15.1.0.8.9",
    "category": "Pacific-ERP",
    "author": "Mehdi Tepava",
    'website': "https://www.pacific-erp.com/",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": ['account','stock','purchase','sale_management','pe_commune_ile'],
    "data": [
        "security/res_groups.xml",
        "security/ir.model.access.csv",
        "data/account_journal.xml",
        "data/account_tax_data.xml",
        "data/ir_actions_report.xml",
        "data/account_move_adm_sequence.xml",
        "data/udm_data.xml",
        "data/decimal_precision.xml",
        "views/bon_livraison_template.xml",
        "views/devis_commande_template.xml",
        "views/facture_template.xml",
        "views/connaissement_template.xml",
        "views/admg_template.xml",
        "views/setting_inherits.xml",
        "views/contact_partner.xml",
        "views/menuitems_inherit.xml",
        "views/product_template_inherit.xml",
        "views/sale_order_form_inherit.xml",
        "views/stock_picking_inherit.xml",
        "views/account_move_inherit.xml",
        "views/accocunt_move_adm.xml",
        ],
    'assets': {
        'web.assets_backend': [
            'pe_revatua/static/src/style.css',
        ],
    },
}