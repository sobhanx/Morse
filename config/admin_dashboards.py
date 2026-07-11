from django.contrib import admin
from django.urls import path


def register_admin_dashboards():
    if getattr(admin.site, "_dashboards_registered", False):
        return

    from django.conf import settings

    product_name = getattr(settings, "PRODUCT_NAME", "Morse")
    admin.site.site_header = product_name
    admin.site.site_title = product_name
    admin.site.index_title = f"{product_name} administration"

    from accounts.admin import user_usage_dashboard
    from websites.admin import website_usage_dashboard

    original_get_urls = admin.site.get_urls

    def get_urls():
        return [
            path(
                "user-usage/",
                admin.site.admin_view(user_usage_dashboard),
                name="user-usage-dashboard",
            ),
            path(
                "website-usage/",
                admin.site.admin_view(website_usage_dashboard),
                name="website-usage-dashboard",
            ),
        ] + original_get_urls()

    admin.site.get_urls = get_urls
    admin.site._dashboards_registered = True


register_admin_dashboards()
