from django import template

register = template.Library()

@register.filter
def get_item(value, arg):
    try:
        return arg in value  # value — це список, arg — ID уроку
    except:
        return False
