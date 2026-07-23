from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_POST

from morse.models import Website, WebsiteAgent
from morse.platform_monitor import (
    build_customer_rows,
    build_website_rows,
    get_platform_conversations,
    get_platform_customers,
    get_platform_totals,
    get_platform_websites,
)
from morse.permissions import (
    get_accessible_websites,
    set_active_website,
    user_can_access_website,
    website_required,
)


@login_required
@require_GET
def website_list(request):
    websites = get_accessible_websites(request.user)
    return render(
        request,
        "websites/list.html",
        {"websites": websites, "active_website": request.website},
    )


@login_required
def website_create(request):
    if request.method == "GET":
        return render(request, "websites/create.html")

    name = request.POST.get("name", "").strip()
    domain = request.POST.get("domain", "").strip()
    if not name:
        return render(
            request,
            "websites/create.html",
            {"error": _("Website name is required.")},
        )

    website = Website.objects.create(
        name=name,
        domain=domain,
        owner=request.user,
    )
    WebsiteAgent.objects.create(website=website, user=request.user)
    set_active_website(request, website)
    return redirect("websites:activate", website_id=website.id)


@login_required
@require_POST
def website_switch(request, website_id):
    website = get_object_or_404(Website, pk=website_id)
    if not user_can_access_website(request.user, website):
        return redirect("websites:list")
    set_active_website(request, website)
    next_url = request.POST.get("next", "dashboard:inbox")
    return redirect(next_url)


@login_required
@require_GET
def website_activate(request, website_id):
    website = get_object_or_404(Website, pk=website_id)
    if not user_can_access_website(request.user, website):
        return redirect("websites:list")
    if website.owner_id != request.user.id and not request.user.is_superuser:
        return redirect("dashboard:inbox")

    set_active_website(request, website)
    embed_url = request.build_absolute_uri(
        f"/widget/embed.js?key={website.public_widget_key}"
    )
    return render(
        request,
        "websites/activate.html",
        {
            "website": website,
            "embed_url": embed_url,
        },
    )


@login_required
@require_POST
def website_activate_toggle(request, website_id):
    website = get_object_or_404(Website, pk=website_id)
    if website.owner_id != request.user.id and not request.user.is_superuser:
        return redirect("websites:list")

    website.is_active = True
    website.activated_at = timezone.now()
    website.save(update_fields=["is_active", "activated_at"])
    set_active_website(request, website)
    return redirect("dashboard:inbox")


@login_required
@require_POST
def website_deactivate(request, website_id):
    website = get_object_or_404(Website, pk=website_id)
    if website.owner_id != request.user.id and not request.user.is_superuser:
        return redirect("websites:list")

    website.is_active = False
    website.save(update_fields=["is_active"])
    return redirect("websites:settings")


@login_required
@require_GET
@website_required
def website_settings(request):
    website = request.website
    embed_url = request.build_absolute_uri(
        f"/widget/embed.js?key={website.public_widget_key}"
    )
    return render(
        request,
        "websites/settings.html",
        {
            "website": website,
            "embed_url": embed_url,
            "agents": website.agents.select_related("user"),
        },
    )


def _is_superuser(user):
    return user.is_superuser


@login_required
@user_passes_test(_is_superuser)
@require_GET
def admin_panel(request):
    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")
    website_id = request.GET.get("website", "").strip()
    tab = request.GET.get("tab", "questions")

    totals = get_platform_totals()
    customers = get_platform_customers(search)
    websites = get_platform_websites(search)
    conversations = get_platform_conversations(search, status, website_id)

    website_choices = Website.objects.order_by("name")

    return render(
        request,
        "websites/admin_panel.html",
        {
            "totals": totals,
            "customer_rows": build_customer_rows(customers),
            "website_rows": build_website_rows(websites),
            "conversations": conversations,
            "website_choices": website_choices,
            "search": search,
            "status": status,
            "website_id": website_id,
            "tab": tab,
        },
    )
