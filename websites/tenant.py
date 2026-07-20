from contextvars import ContextVar

from django.db import models

_current_website = ContextVar("current_website", default=None)


def set_current_website(website):
    return _current_website.set(website)


def get_current_website():
    return _current_website.get()


def reset_current_website(token):
    _current_website.reset(token)


class TenantQuerySet(models.QuerySet):
    def for_website(self, website):
        if website is None:
            return self
        return self.filter(website=website)


class TenantManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        # Django 5.2 builds reverse related managers (e.g. category.articles) as a
        # subclass of the *default* manager. Those managers set `instance` and
        # already constrain rows via the FK. Applying website filtering here would
        # hide related objects whenever the website ContextVar is missing/wrong.
        if getattr(self, "instance", None) is not None:
            return qs
        website = get_current_website()
        if website is not None:
            qs = qs.filter(website=website)
        return qs

    def for_website(self, website):
        return self.get_queryset().for_website(website)


class TenantModel(models.Model):
    website = models.ForeignKey(
        "websites.Website",
        on_delete=models.CASCADE,
        related_name="%(class)ss",
    )

    objects = TenantManager()
    unscoped = models.Manager()

    class Meta:
        abstract = True
        base_manager_name = "unscoped"
