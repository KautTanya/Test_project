import re
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def urlize_blank(text):
    url_pattern = r'(https?://[^\s<]+)'
    result = re.sub(url_pattern, r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', text)
    return mark_safe(result.replace('\n', '<br>'))
