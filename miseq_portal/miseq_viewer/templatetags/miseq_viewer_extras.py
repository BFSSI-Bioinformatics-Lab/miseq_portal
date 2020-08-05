from django import template
from django.template.defaultfilters import stringfilter
register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
@stringfilter
def parse_samplesheet_header_value(val):
    return val.replace("_", " ").title()
