from django.db import models
from django.urls import reverse
from django.utils.text import slugify

from websites.tenant import TenantModel


class Category(TenantModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(blank=True)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]
        verbose_name_plural = "categories"
        unique_together = [("website", "slug")]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Article(TenantModel):
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="articles"
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(blank=True)
    content = models.TextField()
    is_published = models.BooleanField(default=True)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = [("website", "slug")]

    def save(self, *args, **kwargs):
        if self.category_id and not self.website_id:
            self.website_id = self.category.website_id
        if not self.slug:
            base = slugify(self.title)
            slug = base
            counter = 1
            while (
                Article.unscoped.filter(website=self.website, slug=slug)
                .exclude(pk=self.pk)
                .exists()
            ):
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse(
            "knowledge:article",
            kwargs={"slug": self.slug},
        ) + f"?key={self.website.public_widget_key}"
