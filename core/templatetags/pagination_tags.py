"""
Pagination template tags for cleanly rendering pagination links and preserving
existing GET query parameters (filters, search, sorting).
"""

from urllib.parse import urlencode
from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Returns the current query string with specified parameters updated or added.
    Preserves all existing search terms, tab selections, and filters.

    Usage:
        <a href="?{% url_replace page=3 %}">Page 3</a>
        <a href="?{% url_replace tab='in_transit' page=1 %}">In Transit</a>
    """
    request = context.get("request")
    if not request:
        return urlencode(kwargs)

    query_params = request.GET.copy()
    for key, value in kwargs.items():
        if value is None or value == "":
            query_params.pop(key, None)
        else:
            query_params[key] = str(value)

    return query_params.urlencode()
