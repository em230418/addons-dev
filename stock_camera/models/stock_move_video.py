# Copyright 2019 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models
from odoo.tools import config
import os
import os.path
from ..tools import upload_vimeo
from threading import Lock
import string
import logging
import time

VALID_CHARS = "-_.() %s%s" % (string.ascii_letters, string.digits)
VIDEO_OUTPUT_DIRNAME = "stock_move_video"

upload_lock = Lock()
_logger = logging.getLogger(__name__)


def output_dir_abs(self):
    filestore_path = config.filestore(self._cr.dbname)
    output_dir = os.path.join(filestore_path, VIDEO_OUTPUT_DIRNAME)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir
    

# Note: there was an idea to make one2one
class StockMoveVideo(models.Model):

    _name = 'stock.move.video'
    _description = 'Product tranfser video'

    name = fields.Char("Name", required=True)
    move = fields.Many2one("stock.move", required=True)
    picking = fields.Many2one("stock.picking", related="move.picking_id", readonly=True)
    filename = fields.Char("Filename", required=True)
    date_created = fields.Datetime("Video creation date", readonly=True, required=True)
    date_uploaded = fields.Datetime("Video upload date", readonly=True)
    url = fields.Char("URL", readony=True)
    product_id = fields.Many2one("product.product", related="move.product_id", required=True, readonly=True)
    product_tmpl_id = fields.Many2one("product.template", related="move.product_tmpl_id", required=True, readonly=True)

    def abspath(self):
        return os.path.join(output_dir_abs(self), self.filename)
        
    def create(self, vals):
        now = fields.Datetime.now()
        picking = vals["move"].picking_id
        tmp_file = vals["move"]._get_output_filename()
        vals["name"] = "{} - {} - {}".format(picking.name, vals["move"].name, now)

        new_file = os.path.join(
            output_dir_abs(self),
            "{}_.avi".format(
                "".join([c for c in vals["name"] if c in VALID_CHARS]),
            ),
        )

        os.rename(tmp_file, new_file)
        vals["filename"] = os.path.basename(new_file)
        vals["date_created"] = now
        #vals["product_id"] = vals["move"].product_id.id
        #vals["product_tmpl_id"] = vals["move"].product_tmpl_id.id
        vals["move"] = vals["move"].id
        vals["picking"] = picking.id
        
        return super(StockMoveVideo, self).create(vals)

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

    def unlink(self):
        file_to_remove = os.path.join(output_dir_abs(self), self.filename)
        try:
            os.unlink(file_to_remove)
        except:
            _logger.exception("Failed to delete video file")
        super(StockMoveVideo, self).unlink()
