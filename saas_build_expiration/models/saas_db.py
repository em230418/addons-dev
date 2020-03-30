# Copyright 2020 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models, sql_db
from odoo.addons.queue_job.job import job


class SaasDb(models.Model):

    _inherit = 'saas.db'

    expiration_date = fields.Datetime("Expiration date")

    def write(self, vals):
        is_expiration_date_set = 'expiration_date' in vals
        res = super(SaasDb, self).write(vals)

        # поменяли expiration_date в мастере - надо поменять в билде
        if is_expiration_date_set:
            self.with_delay().write_expiration_date_to_build(self.expiration_date)  # TODO: проверить, после write оно обновляется?

        return res

    @job
    def write_expiration_date_to_build(self, expiration_date):
        self.ensure_one()
        db = sql_db.db_connect(self.name)
        with api.Environment.manage(), db.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['ir.config_parameter'].set_param("base.expiration_date", str(expiration_date))
