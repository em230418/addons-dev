# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import string
from odoo import api, fields, models

VALID_CHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)


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
        def on_start_callback(record_id):
            # TODO: подобрать имя для записи. Да и вообще куда записывать
            # TODO: учти еще такую вещь как запись в вимео
            pass

        def on_frame_callback(record_id, frame):
            print("frame", record_id, frame[0:10])
            return True
        
        for s in self:
            s.camera.camera_instance().start_recording(s.id, on_start_callback, on_frame_callback)

    @api.multi
    def camera_record_stop(self):
        for s in self:
            s.camera.camera_instance().stop_recording(s.id)
