from django import template

from websites.demo import localized_website_name

register = template.Library()


@register.filter
def localized_name(website):
    return localized_website_name(website)
