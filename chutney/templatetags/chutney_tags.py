from django.conf import settings
from django.template import Library


register = Library()


@register.filter
def get(obj, key):
    """Filter to allow using a template variable as a key, e.g.:
    {{something|get:my_var}}
    """
    if obj:
        try:
            return obj[key]  # Allows use on lists/tuples as well as dicts
        except (KeyError, IndexError):
            pass
        try:
            return getattr(obj, key)
        except AttributeError:
            pass
    return settings.TEMPLATES[0]["OPTIONS"].get("string_if_invalid", "")
