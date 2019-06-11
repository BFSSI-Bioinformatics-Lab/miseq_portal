from django.template.defaulttags import register


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def parse_samplesheet_header_value(val):
    return val.replace("_", " ").title()
