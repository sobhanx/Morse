import logging

from django.conf import settings

from .models import SmsLog

logger = logging.getLogger(__name__)


def _sms_credentials_configured():
    return bool(
        settings.SMS_IR_API_KEY
        and settings.SMS_IR_LINE_NUMBER
    )


def send_sms(data, subject, user_id=None, phone=None, template_id=None):
    from django.contrib.auth import get_user_model
    from sms_ir import SmsIr

    User = get_user_model()

    if not _sms_credentials_configured():
        logger.error(
            "SMS not sent: SMS_IR_API_KEY and SMS_IR_LINE_NUMBER must be set in environment"
        )
        return False

    if subject == "phone_verify" and not (template_id or settings.SMS_IR_VERIFY_TEMPLATE_ID):
        logger.error(
            "SMS verify not sent: SMS_IR_VERIFY_TEMPLATE_ID must be set in environment"
        )
        return False

    api_key = settings.SMS_IR_API_KEY
    line_number = settings.SMS_IR_LINE_NUMBER
    sms_ir = SmsIr(api_key, line_number)

    status = True
    user = None
    if user_id:
        user = User.objects.filter(id=user_id).first()

    try:
        number = data.get("receptor") if isinstance(data, dict) else None
        if not phone:
            phone = number

        if subject == "phone_verify":
            code = data.get("token") or data.get("code")
            parameters = [{"name": "code", "value": code}]
            result = sms_ir.send_verify_code(
                number=phone,
                template_id=template_id or settings.SMS_IR_VERIFY_TEMPLATE_ID,
                parameters=parameters,
            )
        else:
            message = data.get("token")
            result = sms_ir.send_sms(phone, message)

        SmsLog.objects.create(
            is_sent=(result.status_code == 200),
            status_code=result.status_code,
            subject=subject,
            user=user,
            phone=phone,
        )

        if result.status_code != 200:
            status = False

    except Exception:
        logger.exception("SMS send failed for subject=%s phone=%s", subject, phone)
        SmsLog.objects.create(
            is_sent=False,
            subject=subject,
            user=user,
            phone=phone,
            status_code=999,
        )
        status = False

    return status
