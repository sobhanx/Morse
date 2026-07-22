"""Bilingual demo knowledge base content keyed by stable slugs."""

DEMO_KB = {
    "getting-started": {
        "fa": {
            "name": "شروع کار",
            "description": "اصول اولیه پلتفرم را بیاموزید",
            "articles": {
                "how-do-i-create-an-account": {
                    "title": "چگونه حساب کاربری بسازم؟",
                    "content": (
                        "در صفحه اصلی با ایمیل خود ثبت‌نام کنید. "
                        "لینک تأیید در چند دقیقه ارسال می‌شود."
                    ),
                },
                "how-do-i-reset-my-password": {
                    "title": "چگونه رمز عبور را بازنشانی کنم؟",
                    "content": (
                        "روی «فراموشی رمز عبور» در صفحه ورود کلیک کنید "
                        "و مراحل بازنشانی را دنبال کنید."
                    ),
                },
            },
        },
        "en": {
            "name": "Getting Started",
            "description": "Learn the basics of our platform",
            "articles": {
                "how-do-i-create-an-account": {
                    "title": "How do I create an account?",
                    "content": (
                        "Sign up on our homepage with your email address. "
                        "You'll receive a confirmation link within minutes."
                    ),
                },
                "how-do-i-reset-my-password": {
                    "title": "How do I reset my password?",
                    "content": (
                        "Click 'Forgot password' on the login page. Enter your email "
                        "and follow the reset link we send you."
                    ),
                },
            },
        },
    },
    "billing": {
        "fa": {
            "name": "صورتحساب",
            "description": "سوالات پرداخت و اشتراک",
            "articles": {
                "what-payment-methods-do-you-accept": {
                    "title": "چه روش‌های پرداختی قبول می‌کنید؟",
                    "content": (
                        "کارت‌های بانکی، پی‌پال و انتقال بانکی برای پلن‌های سالانه."
                    ),
                },
                "how-do-i-cancel-my-subscription": {
                    "title": "چگونه اشتراک را لغو کنم؟",
                    "content": (
                        "به تنظیمات > صورتحساب > لغو اشتراک بروید. "
                        "دسترسی تا پایان دوره ادامه دارد."
                    ),
                },
            },
        },
        "en": {
            "name": "Billing",
            "description": "Payment and subscription questions",
            "articles": {
                "what-payment-methods-do-you-accept": {
                    "title": "What payment methods do you accept?",
                    "content": (
                        "We accept all major credit cards, PayPal, and bank transfers "
                        "for annual plans."
                    ),
                },
                "how-do-i-cancel-my-subscription": {
                    "title": "How do I cancel my subscription?",
                    "content": (
                        "Go to Settings > Billing > Cancel subscription. Your access "
                        "continues until the end of the billing period."
                    ),
                },
            },
        },
    },
    "technical-support": {
        "fa": {
            "name": "پشتیبانی فنی",
            "description": "عیب‌یابی و یکپارچه‌سازی",
            "articles": {
                "how-do-i-embed-the-chat-widget": {
                    "title": "چگونه ویجت گفتگو را نصب کنم؟",
                    "content": (
                        "اسکریپت نصب را از داشبورد کپی کرده و قبل از تگ پایانی "
                        "</body> در سایت قرار دهید."
                    ),
                },
                "is-there-an-api-available": {
                    "title": "آیا API دارید؟",
                    "content": (
                        "بله! مستندات REST API و WebSocket را در بخش توسعه‌دهندگان ببینید."
                    ),
                },
            },
        },
        "en": {
            "name": "Technical Support",
            "description": "Troubleshooting and integrations",
            "articles": {
                "how-do-i-embed-the-chat-widget": {
                    "title": "How do I embed the chat widget?",
                    "content": (
                        "Copy the embed script from your dashboard and paste it before "
                        "the closing </body> tag on your website."
                    ),
                },
                "is-there-an-api-available": {
                    "title": "Is there an API available?",
                    "content": (
                        "Yes! Visit our developer documentation for REST API endpoints "
                        "and WebSocket integration guides."
                    ),
                },
            },
        },
    },
}


def get_demo_category_slugs():
    return list(DEMO_KB.keys())


def get_demo_article_slugs():
    slugs = []
    for category in DEMO_KB.values():
        for lang_data in category.values():
            slugs.extend(lang_data["articles"].keys())
    return list(dict.fromkeys(slugs))
