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
        for s in self:
            s.camera_is_recording = s.camera.camera_instance().is_recording(s.id) if s.camera and s.id else False

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

    def _get_output_filename(self, prefix="tmp"):
        record_id = self.id
        output_dir = output_dir_abs(self)
        filename = "{}_{}.avi".format(prefix, record_id)
        return path.join(output_dir, filename)

    @api.multi
    def camera_record_start(self):
        output = None
        
        def on_start_callback(record_id, video_width, video_height, video_fps):
            nonlocal output
            output_filename_abs = self._get_output_filename()
            output = cv2.VideoWriter(
                output_filename_abs,
                cv2.VideoWriter_fourcc('M','J','P','G'),
                min(video_fps, 30),  # it can give overly high fps (180 000), so it would be better to limit it
                (video_width, video_height)
            )

        def on_frame_callback(record_id, frame):
            nonlocal output
            output.write(frame)

        def on_finish_callback(record_id):
            nonlocal output
            output.release()

        for s in self:
            s.camera.camera_instance().start_recording(s.id, on_start_callback, on_frame_callback, on_finish_callback)

    @api.multi
    def camera_record_stop(self):
        for s in self:

            # check if it was recording actually
            if not s.camera.camera_instance().stop_recording(s.id):
                continue

            self.env['stock.camera.video'].create({
                "picking": s,
            })
