# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

{
    "name": """Inventory camera""",
    "summary": """TODO description intro""",
    "category": "Warehouse",
    # "live_test_url": "http://apps.it-projects.info/shop/product/DEMO-URL?version=12.0",
    "images": [],
    "version": "12.0.1.0.0",
    "application": False,

    "author": "IT-Projects LLC, Eugene Molotov",
    "support": "apps@it-projects.info",
    "website": "https://apps.odoo.com/apps/modules/12.0/stock_camera/",
    "license": "LGPL-3",
    # "price": 9.00,
    # "currency": "EUR",

    "depends": [
        'stock',
    ],
    "external_dependencies": {"python": ["cv2", "vimeo"], "bin": []},
    "data": [
        'views/stock_picking_views.xml',
        'views/stock_camera.xml',
        'security/ir.model.access.csv',
    ],
    "demo": [
        # TODO: rtsp://170.93.143.139/rtplive/470011e600ef003a004ee33696235daa
        # TODO: rtmp://semerkandglb.mediatriple.net:1935/semerkandliveedge/semerkand2
    ],
    "qweb": [
    ],

    "post_load": None,
    "pre_init_hook": None,
    "post_init_hook": None,
    "uninstall_hook": None,

    "auto_install": False,
    "installable": True,

    # "demo_title": "Inventory camera",
    # "demo_addons": [
    # ],
    # "demo_addons_hidden": [
    # ],
    # "demo_url": "DEMO-URL",
    # "demo_summary": "TODO description intro",
    # "demo_images": [
    #    "images/MAIN_IMAGE",
    # ]
}
