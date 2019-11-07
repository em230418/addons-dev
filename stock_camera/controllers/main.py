# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import http
from odoo.http import request
from odoo.exceptions import UserError
from werkzeug.wrappers import BaseResponse


class Main(http.Controller):
    @http.route('/stream/stock_camera/<int:camera_id>', type='http', auth='user')
    def camera_stream(self, camera_id, *args, **kwargs):
        camera = request.env['stock.camera.config'].browse(camera_id)  # TODO: настроить права
        camera_instance = camera.camera_instance()

        def iterator():
            while True:
                frame = camera_instance.get_frame()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        return BaseResponse(iterator(), 200, [('Content-Type', 'multipart/x-mixed-replace; boundary=frame')])
