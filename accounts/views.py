from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_backends, login
from django.contrib.auth import logout
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from morse.permissions import (
    get_accessible_websites,
    set_active_website,
)

from .models import User, VerifyCode
from .services import send_sms
from .validators import phone_validation


def get_post_login_redirect_url(request, user):
    websites = get_accessible_websites(user)
    if not websites.exists():
        return reverse("websites:list")
    active_id = request.session.get("active_website_id")
    website = None
    if active_id:
        website = websites.filter(pk=active_id).first()
    if not website:
        website = websites.first()
        set_active_website(request, website)
    if website.owner_id == user.id and not website.is_active:
        return reverse("websites:activate", kwargs={"website_id": website.id})
    return reverse("dashboard:inbox")


def _login_user(request, user):
    backends = [b for b in get_backends() if b.user_can_authenticate(user)]
    if not backends:
        return False
    user.backend = backends[0].__module__ + "." + backends[0].__class__.__name__
    login(request, user)
    websites = get_accessible_websites(user)
    if websites.exists():
        active_id = request.session.get("active_website_id")
        if not active_id or not websites.filter(pk=active_id).exists():
            set_active_website(request, websites.first())
    return True


def _send_phone_verify_sms(user, phone):
    new_verify_code = VerifyCode.objects.create(user=user, subject="phone")
    data = {
        "receptor": phone,
        "token": new_verify_code.code,
    }
    send_sms(
        data=data,
        subject="phone_verify",
        user_id=user.id,
        phone=phone,
        template_id=settings.SMS_IR_VERIFY_TEMPLATE_ID,
    )
    return new_verify_code


def sms_login_view(request):
    if request.user.is_authenticated:
        return redirect(get_post_login_redirect_url(request, request.user))

    template_name = "accounts/sms_login_form.html"
    context = {}

    next_url = request.GET.get("next")
    if next_url:
        request.session["next"] = next_url

    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        request.session["phone"] = phone

        if not phone:
            context["error"] = _("Phone number is required.")
            return render(request, template_name, context)

        the_user = User.objects.filter(phone=phone).first()

        if not the_user:
            if not phone_validation(phone):
                context["error"] = _(
                    "Invalid phone number. It must start with 09 and be 11 digits."
                )
                return render(request, template_name, context)
            try:
                the_user = User.objects.create_user(phone=phone, is_active=True)
            except Exception as exc:
                context["error"] = _("Could not create account. (%(error)s)") % {
                    "error": exc
                }
                return render(request, template_name, context)

        try:
            _send_phone_verify_sms(the_user, phone)
        except Exception:
            context["error"] = _("Could not send verification code.")
            return render(request, template_name, context)

        return redirect("accounts:sms-login-verification", phone=the_user.phone)

    return render(request, template_name, context)


def sms_login_verification_view(request, phone):
    template_name = "accounts/sms_login_confirm.html"
    context = {"phone": phone}

    if request.method == "POST":
        try:
            the_user = User.objects.get(phone=phone)
        except User.DoesNotExist:
            context["error"] = _("User not found.")
            return render(request, template_name, context)

        verify_code = request.POST.get("verify_code", "").strip()
        if not verify_code:
            return render(request, template_name, context)

        verify = VerifyCode.objects.filter(user=the_user, subject="phone", status=1)
        if not verify.exists():
            context["error"] = _("Verification code has expired.")
            return render(request, template_name, context)

        verify = verify.last()
        if verify.code == verify_code:
            verify.attempts += 1
            verify.status = 2
            verify.save()

            the_user.valid_phone = True
            the_user.save(update_fields=["valid_phone"])

            if not _login_user(request, the_user):
                context["error"] = _("Authentication failed.")
                return render(request, template_name, context)

            if "next" in request.session:
                next_url = request.session.pop("next")
                if next_url.startswith("/admin") and not the_user.is_staff:
                    messages.error(
                        request,
                        _("You do not have permission to access the admin panel."),
                    )
                    return redirect(get_post_login_redirect_url(request, the_user))
                return redirect(next_url)

            messages.success(request, _("Signed in successfully."))
            return redirect(get_post_login_redirect_url(request, the_user))

        verify.attempts += 1
        if verify.attempts >= 5:
            verify.status = 0
        verify.save()
        context["error"] = _("Invalid verification code.")
        return render(request, template_name, context)

    return render(request, template_name, context)


@require_POST
@csrf_protect
def resend_verification_code(request, phone):
    try:
        the_user = User.objects.get(phone=phone)
        _send_phone_verify_sms(the_user, phone)
        return JsonResponse({"success": True})
    except User.DoesNotExist:
        return JsonResponse({"success": False, "error": _("User not found.")})
    except Exception as exc:
        return JsonResponse({"success": False, "error": str(exc)})


def signup(request):
    return redirect("accounts:login")


def logout_view(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)
