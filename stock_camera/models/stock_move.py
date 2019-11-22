# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class StockMove(models.Model):

    _inherit = 'stock.move'

    @api.depends("picking_id")
    def _compute_camera_is_recording(self):
        for record in self:
            picking = record.picking
            record.camera_is_recording = picking.camera.camera_instance().is_recording(record.id) if picking.camera and record.id else False

    camera_is_recording = fields.Boolean('Is being recorded by stock camera?', compute=_compute_camera_is_recording, readonly=True, store=False)

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
            s.picking_id.camera.camera_instance().start_recording(s.id, on_start_callback, on_frame_callback, on_finish_callback)

    @api.multi
    def camera_record_stop(self):
        for s in self:

            # check if it was recording actually
            if not s.camera.camera_instance().stop_recording(s.id):
                continue

            self.env['stock.camera.video'].create({
                "move": s,
            })
