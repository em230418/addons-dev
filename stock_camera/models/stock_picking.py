# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import time
import string
from odoo import api, fields, models
from odoo.tools import config
from os import path, makedirs
from .stock_camera_video import output_dir_abs
import cv2


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.depends("camera")
    def _compute_camera_is_recording(self):
        for record in self:
            record.camera_is_recording = record.move_lines.filtered(lambda move: move.camera_is_recording)

    @api.depends("videos")
    def _compute_last_uploaded_video(self):
        for record in self:
            uploaded_videos = record.videos.filtered(lambda v: v.url)
            if uploaded_videos:
                record.last_uploaded_video = uploaded_videos.sorted(reverse=True)[0].url

    # TODO: on change camera - stop recording prevous one
    camera = fields.Many2one('stock.camera.config', 'Camera')
    camera_is_recording = fields.Boolean('Is being recorded by stock camera?', compute=_compute_camera_is_recording, readonly=True, store=False)
    camera_filename_prefix = fields.Char('Record output filename prefix')  # TODO: validate it
    last_uploaded_video = fields.Char("Last uploaded video", readonly=True, compute=_compute_last_uploaded_video)
    videos = fields.One2many('stock.camera.video', 'picking', 'Recorded videos', readonly=True)
