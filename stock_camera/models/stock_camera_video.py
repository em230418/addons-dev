# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from odoo.tools import config
from os import rename, path, makedirs
from os.path import split, join, basename
from ..tools import upload_vimeo
from threading import Lock
import string
import logging
import time

VALID_CHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)
VIDEO_OUTPUT_DIRNAME = "stock_picking_video"

upload_lock = Lock()
_logger = logging.getLogger(__name__)


def output_dir_abs(self):
    filestore_path = config.filestore(self._cr.dbname)
    output_dir = path.join(filestore_path, VIDEO_OUTPUT_DIRNAME)
    makedirs(output_dir, exist_ok=True)
    return output_dir
    

class StockCameraVideo(models.Model):

    _name = 'stock.camera.video'
    _description = 'Stock Camera Video'

    name = fields.Char("Name", required=True)
    picking = fields.Many2one("stock.picking", string="Picking", required=True)
    filename = fields.Char("Filename", required=True)
    date_created = fields.Datetime("Video creation date", readonly=True, required=True)
    date_uploaded = fields.Datetime("Video upload date", readonly=True)
    url = fields.Char("URL", readony=True)

    def abspath(self):
        return join(output_dir_abs(self), self.filename)
        
    def create(self, vals):
        now = fields.Datetime.now()
        tmp_file = vals["picking"]._get_output_filename()
        new_file = join(
            output_dir_abs(self),
            "{}_{}.avi".format(
                "".join([c for c in vals["picking"].name if c in VALID_CHARS]),
                now
            ),
        )

        rename(tmp_file, new_file)
        vals["name"] = "{} - {}".format(vals["picking"].name, now)
        vals["filename"] = basename(new_file)
        vals["picking"] = vals["picking"].id
        vals["date_created"] = now
        
        return super(StockCameraVideo, self).create(vals)

    @api.multi
    def upload(self):
        is_locked = not upload_lock.acquire(blocking=False)
        if is_locked:
            _logger.debug("Thread is locked. Maybe next time?")
            return

        _logger.debug("Started uploading...")

        for record in self.env[self._name].search([("url", "=", False)]):
            try:
                _logger.debug("Uploading {}".format(record))
                upload_uri = upload_vimeo.upload(record.abspath(), record.name)
                if upload_uri:
                    _logger.debug("Successfully uploaded {}".format(record))
                    record.url = upload_uri
                    record.date_uploaded = fields.Datetime.now()
                else:
                    _logger.debug("Failed to upload {}. No info available, maybe logs above?".format(record))
            except Exception as e:
                _logger.exception("Failed to upload {}".format(record))

        _logger.debug("Finished uploading")

        upload_lock.release()
