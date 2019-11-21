from django.template.defaulttags import register

from config.settings.base import MEDIA_ROOT

""" Note that these tags were registered in config.settings.base in the TEMPLATES section under libraries """


@register.filter
def filter_media_root_from_url(val):
    return val.replace(str(MEDIA_ROOT), "")
