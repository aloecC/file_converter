from django.contrib import admin

from reports.models import ReportRequest


@admin.register(ReportRequest)
class ReportRequestAdmin(admin.ModelAdmin):
    """Административный интерфейс для управления отчетами."""

    list_display = (id, "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = (
        "status",
        "user",
    )
