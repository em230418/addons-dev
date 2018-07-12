# Copyright 2018 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).
import logging
import json

from odoo import models, fields, api
from odoo.http import request

_logger = logging.getLogger(__name__)
PAYMENT_RESULT_NOTIFICATION_URL = 'wechat/callback'
SUCCESS = 'SUCCESS'


class WeChatOrder(models.Model):
    """Records with order information and payment status.

    Can be used for different types of Payments. See description of trade_type field. """

    _name = 'wechat.order'
    _description = 'Unified Order'
    _rec_name = 'order_ref'

    trade_type = fields.Selection([
        ('JSAPI', 'Official Account Payment (Mini Program)'),
        ('NATIVE', 'Native Payment'),
        ('APP', 'In-App Payment'),
    ], help="""
* Official Account Payment -- Mini Program Payment or In-App Web-based Payment
* Native Payment -- Customer scans QR for specific order and confirm payment
* In-App Payment -- payments in native mobile applications
    """)

    order_ref = fields.Char('Order Reference', readonly=True)
    total_fee = fields.Integer('Total Fee', help='Amount in cents', readonly=True)
    state = fields.Selection([
        ('draft', 'Unpaid'),
        ('done', 'Paid'),
        ('error', 'Error'),
    ], string='State', default='draft')
    # terminal_ref = fields.Char('Terminal Reference', help='e.g. POS Name', readonly=True)
    debug = fields.Boolean('Sandbox', help="Payment was not made. It's only for testing purposes", readonly=True)
    order_details_raw = fields.Text('Raw Order', readonly=True)
    result_raw = fields.Text('Raw result', readonly=True)
    notification_result_raw = fields.Text('Raw Notification result', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.user.company_id.currency_id)
    notification_received = fields.Boolean(help='Set to true on receiving notifcation to avoid repeated processing', default=False)
    line_ids = fields.One2many('wechat.order.line', 'order_id')

    def _body(self):
        """ Example of result:

        {"goods_detail": [
            {
                "goods_id": "iphone6s_16G",
                "wxpay_goods_id": "100 1",
                "goods_name": "iPhone 6s 16G",
                "goods_num": 1,
                "price": 100,
                "goods_category": "123456",
                "body": "苹果手机",
            },
            {
                "goods_id": "iphone6s_3 2G",
                "wxpay_goods_id": "100 2",
                "goods_name": "iPhone 6s 32G",
                "quantity": 1,
                "price": 200,
                "goods_category": "123789",
            }
        ]}"""
        self.ensure_one()
        rendered_lines = [{
            'goods_id': str(line.product_id.id),
            'wxpay_goods_id': line.wxpay_goods_ID,
            'goods_name': line.name or line.product_id.name,
            'goods_num': line.quantity,
            'price': line.get_fee(),
            'goods_category': line.category,
        } for line in self.line_ids]
        body = {'goods_detail': rendered_lines}

        return body

    def _total_fee(self):
        self.ensure_one()
        total_fee = sum([
            line.get_fee()
            for line in self.line_ids])
        return total_fee

    def _notify_url(self):
        url = self.env['ir.config_parameter'].get_param('wechat.payment_result_notification_url')
        if url:
            return url
        # Try to compute url automatically
        try:
            scheme = request.httprequest.scheme
        except:
            scheme = 'http'

        domain = self.env["ir.config_parameter"].get_param('web.base.url')
        return "{scheme}://domain/{path}".format(
            scheme=scheme,
            domain=domain,
            path=PAYMENT_RESULT_NOTIFICATION_URL,
        )

    @api.model
    def create_qr(self, lines, total_fee, create_vals=None, **kwargs):
        """Native Payment

        :param lines: list of dictionary
        :param total_fee: amount in cents
        """
        debug = self.env['ir.config_parameter'].get_param('wechat.local_sandbox') == '1'
        vals = {
            'trade_type': 'NATIVE',
            'line_ids': [(0, 0, data) for data in lines],
            'debug': debug,
        }
        if create_vals:
            vals.update(create_vals)
        order = self.create(vals)
        total_fee = order._total_fee()
        if debug:
            _logger.info('SANDBOX is activated. Request to wechat servers is not sending')
            # Dummy Data. Change it to try different scenarios
            result_json = {
                'return_code': 'SUCCESS',
                'result_code': 'SUCCESS',
                'openid': '123',
                'total_fee': total_fee,
                'order_ref': order_ref,
            }
            if self.env.context.get('debug_wechat_order_response'):
                result_json = self.env.context.get('debug_wechat_order_response')
        else:
            body = order._body()
            wpay = self.env['ir.config_parameter'].get_wechat_pay_object()
            # TODO: we probably have make cr.commit() before making request to
            # be sure that we save data before sending request to avoid
            # situation when order is sent to wechat server, but was not saved
            # in our server for any reason
            result_json = wpay.order.create(
                'NATIVE',
                total_fee,
                body,
                total_fee,
                self._notify_url(),
                out_trade_no=order.id,
                # TODO fee_type=record.currency_id.name
            )

        result_raw = json.dumps(result_json)
        _logger.debug('result_raw: %s', result_raw)
        vals = {
            'result_raw': result_raw,
            'total_fee': total_fee,
        }
        order.write(vals)
        code_url = result_json['code_url']
        return order, code_url

    def on_notification(self, data):
        """
        return True if notification changed order
        """
        # check signature
        wpay = self.env['ir.config_parameter'].get_wechat_pay_object()
        if not wpay.check_signature(data):
            _logger.warning("Notification Signature is not valid:\n", data)
            return False

        order_id = data.get('out_trade_no')
        order = None
        if order_id:
            order = self.browse(order_id)
        if not order:
            _logger.warning("Order %s from notification is not found", order_id)
            return False

        # check for duplicates
        if order.notification_received:
            _logger.warning("Notifcation duplicate is received: %s", order)
            return False

        vals = {
            'notification_result_raw': json.dumps(data),
            'notification_received': True,
        }
        if not (data['return_code'] == SUCCESS and data['result_code'] == SUCCESS):
            vals['state'] = 'error'

        else:
            vals['state'] = 'done'

        order.write(vals)
        return True


class WeChatOrderLine(models.Model):
    _name = 'wechat.order.line'

    name = fields.Char('Name', help="When empty, product's name is used")
    description = fields.Char('Body')
    product_id = fields.Many2one('product.product', required=True)
    wxpay_goods_ID = fields.Char('Wechat Good ID')
    price = fields.Monetary('Price', required=True, help='Price in currency units (not cents)')
    currency_id = fields.Many2one('res.currency', related='order_id')
    quantity = fields.Char('Quantity', default=1)
    category = fields.Char('Category')
    order_id = fields.Many2one('wechat.order')

    def get_fee(self):
        self.ensure_one()
        return int(100*(self.price or self.product_id.price))
