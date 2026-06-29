from django.contrib import admin
from .models import FAQ, FAQCategory, SupportTicket, TicketReply


class FAQInline(admin.TabularInline):
    model = FAQ
    extra = 1


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    inlines = [FAQInline]
    list_display = ("name", "order")


class TicketReplyInline(admin.TabularInline):
    model = TicketReply
    extra = 1
    fields = ("author", "body", "is_staff_reply")


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "user", "category", "status", "created_at")
    list_filter = ("status", "category")
    search_fields = ("subject", "user__username")
    inlines = [TicketReplyInline]
