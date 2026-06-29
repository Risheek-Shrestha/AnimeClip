from django.contrib import admin

from .models import CuratedRow, CuratedRowItem


class CuratedRowItemInline(admin.TabularInline):
    model = CuratedRowItem
    extra = 3
    fields = ("order", "anime", "movie", "badge_text")


@admin.register(CuratedRow)
class CuratedRowAdmin(admin.ModelAdmin):
    list_display = ("name", "content_type", "is_active", "show_rank_numbers", "order")
    list_editable = ("is_active", "order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [CuratedRowItemInline]

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
