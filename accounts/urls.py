from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.sms_login_view, name="login"),
    path(
        "login/sms/verification/<str:phone>/",
        views.sms_login_verification_view,
        name="sms-login-verification",
    ),
    path(
        "login/sms/resend/<str:phone>/",
        views.resend_verification_code,
        name="resend-code",
    ),
    path("signup/", views.signup, name="signup"),
    path("logout/", views.logout_view, name="logout"),
]
