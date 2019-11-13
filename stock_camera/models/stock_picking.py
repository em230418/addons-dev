# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import time
import string
from odoo import api, fields, models
from odoo.tools import config
from os import path, makedirs
from ..tools import upload_vimeo
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
    last_uploaded_video = fields.Char("Last uploaded video", readonly=True)


    def _get_output_filename(self, prefix="tmp"):
        record_id = self.id
        filestore_path = config.filestore(self._cr.dbname)
        output_dir = path.join(filestore_path, VIDEO_OUTPUT_DIRNAME)
        makedirs(output_dir, exist_ok = True)
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
            output_filename_abs = self._get_output_filename()
            upload_uri = upload_vimeo.upload(output_filename_abs, time.strftime("{name} - %D %T".format(name=self.name)))
            if upload_uri:
                s.last_uploaded_video =  upload_uri
