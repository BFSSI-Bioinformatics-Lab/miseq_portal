from django import template
from django.template.defaultfilters import stringfilter
from config.settings.base import MEDIA_ROOT

register = template.Library()

""" Note that these tags were registered in config.settings.base in the TEMPLATES section under libraries """


@register.filter
@stringfilter
def filter_media_root_from_url(val):
    return val.replace(str(MEDIA_ROOT), "")
