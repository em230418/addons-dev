# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class ProductTemplate(models.Model):

    _inherit = 'product.template'

    stock_move_videos = fields.One2many("stock.move.video", "product_tmpl_id", readonly=True)

    
