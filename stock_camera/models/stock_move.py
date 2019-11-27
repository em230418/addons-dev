# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from .stock_move_video import output_dir_abs
from os import path, makedirs
import cv2
import time
import string


class StockMove(models.Model):

    _inherit = 'stock.move'

    @api.depends("picking_id")
    def _compute_camera_is_recording(self):
        is_busy = False
        for record in self:
            picking = record.picking_id
            record.camera_is_recording = picking.camera.camera_instance().is_recording(record.id) if picking.camera and record.id else False
            if record.camera_is_recording:
                is_busy = True

        for record in self:
            record.camera_is_busy = is_busy

    camera_is_busy = fields.Boolean('Is camera already recording other move in current picking?', compute=_compute_camera_is_recording, readonly=True, store=False)
    camera_is_recording = fields.Boolean('Is being recorded by stock camera?', compute=_compute_camera_is_recording, readonly=True, store=False)
    camera = fields.Many2one(related="picking_id.camera", readonly=True)
    video = fields.Many2one("stock.move.video", "Transfer video", readonly=True)

    def _get_output_filename(self, prefix="tmp"):
        record_id = self.id
        output_dir = output_dir_abs(self)
        filename = "{}_{}.avi".format(prefix, record_id)
        return path.join(output_dir, filename)

    @api.multi
    def camera_record_start(self):
        self.ensure_one()

        # TODO: message if video allready exists
        # TODO: check permission

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

        self.picking_id.camera.camera_instance().start_recording(s.id, on_start_callback, on_frame_callback, on_finish_callback)
        

    @api.multi
    def camera_record_stop(self):
        for s in self:

            # check if it was recording actually
            if not s.camera.camera_instance().stop_recording(s.id):
                continue

            self.env['stock.move.video'].create({
                "move": s,
            })
