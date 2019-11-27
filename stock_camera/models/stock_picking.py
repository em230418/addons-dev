# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from odoo.tools import config


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.depends("camera")
    def _compute_camera_is_recording(self):
        for record in self:
            record.camera_is_recording = record.move_lines.filtered(lambda move: move.camera_is_recording)

    # TODO: on change camera - stop recording prevous one
    camera = fields.Many2one('stock.camera.config', 'Camera')
    camera_is_recording = fields.Boolean('Is being recorded by stock camera?', compute=_compute_camera_is_recording, readonly=True, store=False)
