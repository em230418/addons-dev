# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import time
import string
from odoo import api, fields, models
from odoo.tools import config
from os import path, makedirs
import cv2

VALID_CHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)
VIDEO_OUTPUT_DIRNAME = "stock_picking_video"


class StockPicking(models.Model):

    _inherit = 'stock.picking'

    @api.depends("camera")
    def _compute_camera_is_recording(self):
        for s in self:
            s.camera_is_recording = s.camera.camera_instance().is_recording(s.id) if s.camera and s.id else False

    # TODO: on change camera - stop recording prevous one
    camera = fields.Many2one('stock.camera.config', 'Camera')
    camera_is_recording = fields.Boolean('Is being recorded by stock camera?', compute=_compute_camera_is_recording, readonly=True, store=False)
    camera_filename_prefix = fields.Char('Record output filename prefix')  # TODO: validate it

    @api.multi
    def camera_record_start(self):
        output = None
        output_filename = None
        def on_start_callback(record_id, video_width, video_height, video_fps):
            nonlocal output
            nonlocal output_dir
            nonlocal output_filename
            filestore_path = config.filestore(self._cr.dbname),
            output_dir = path.join(filestore_path, VIDEO_OUTPUT_DIRNAME)
            makedirs(output_dir, exist_ok = True)
            
            filename = "{}_{}_{}.avi".format(self.name, int(time.time()), self.id)
            filename = ''.join(c for c in filename if c in VALID_CHARS)

            output = cv2.VideoWriter(
                path.join(output_dir, filename),
                cv2.VideoWriter_fourcc('M','J','P','G'),
                min(video_fps, 30),  # it can give overly high fps (180 000), so it would be better to limit it
                (video_width, video_height)
            )
            output_filename = filename

        def on_frame_callback(record_id, frame):
            nonlocal output
            output.write(frame)

        def on_finish_callback(record_id):
            nonlocal output
            output.release()
            # TODO: create attachment
            # TODO: post it to vimeo
        
        for s in self:
            s.camera.camera_instance().start_recording(s.id, on_start_callback, on_frame_callback, on_finish_callback)

    @api.multi
    def camera_record_stop(self):
        for s in self:
            s.camera.camera_instance().stop_recording(s.id)
