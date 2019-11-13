# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from .camera import Camera


class StockCameraConfig(models.Model):

    _name = 'stock.camera.config'
    _description = 'Camera configuration'

    name = fields.Char('Name', required=True)
    uri = fields.Char('URI to ip camera', required=True)  # TODO: validate url

    # TODO: надо выбирать, куда сохранять

    # TODO: on change uri, cleanup threads

    @api.model
    def camera_instance(self):
        self.ensure_one()
        return Camera(self.uri)

    @api.multi
    def watch_action(self):
        return {
            "type": "ir.actions.act_url",
            "url": "/stream/stock_camera/{}".format(self._context['active_id']),
            "target": "new",
        }
