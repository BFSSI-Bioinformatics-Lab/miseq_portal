from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def parse_samplesheet_header_value(val):
    return val.replace("_", " ").title()
