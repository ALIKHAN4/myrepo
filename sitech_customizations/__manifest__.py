
{
    "name": "Sitech Customizations",
    "version": "1.0",
    "depends": ["crm", "product", "sale"],
    "author": "Odolution",
    "category": "Customizations",

    "data": [
        "data/ir_cron.xml",
        "data/crm_stage.xml",
        "views/sales_target_views.xml",
        "views/sale_order.xml",
        "views/crm_lost_reason.xml",
        "views/product_category.xml",
        "security/ir.model.access.csv","views/crm_lead_views.xml"
        "data/record_rule.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'sitech_customizations/static/src/**/*.js',
            'sitech_customizations/static/src/**/*.xml',
        ],
    },
    "installable": True,
    "application": False
}