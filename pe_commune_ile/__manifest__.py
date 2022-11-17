# -*- coding: utf-8 -*-
{
    "name": "Contact : Communes et îles (Polynésie)",
    "summary": "Ajoute dans le modules contactes la possibilité de renseigner les communes et les îles",
    "version": "15.0.0.0.1",
    "category": "Pacific-ERP",
    "author": "Mehdi Tepava",
    'website': "https://www.pacific-erp.com/",
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": ["contacts"],
    "data": [
        "security/ir.model.access.csv",
        "views/contact_commune.xml",
        "views/contact_country.xml",
        "views/menuitems_inherit.xml",
        ],
}
