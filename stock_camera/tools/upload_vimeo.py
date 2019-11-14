try:
    import vimeo
except ImportError:
    vimeo = None

import logging
    
_logger = logging.getLogger(__name__)

from odoo.tools import config

def upload(filename, title, description = ""):
    if not vimeo:
        _logger.error("Cannot upload to vimeo: module PyVimeo is not installed")
        return

    required_options = (
        "vimeo_client_id",
        "vimeo_secret",
        "vimeo_token",
    )

    required_options_values = []
    missing_options = []
    
    for i in required_options:
        value = config.options.get(i)
        if not value:
            missing_options.append(i)

        required_options_values.append(value)

    if missing_options:
        _logger.error("Cannot upload to vimeo: missing values in config for following options: {}".format(", ".join(missing_options)))
        return

    key, secret, token = required_options_values

    client = vimeo.VimeoClient(token=token, key=key, secret=secret)

    result = client.upload(filename, data={
        "name": title,
        "description": description,
        "chuck_size": 512 * 1024,  # https://github.com/vimeo/vimeo.py/issues/141#issuecomment-517446424
    })
    if not result:
        return result

    return "https://vimeo.com" + result.replace("/videos", "")
