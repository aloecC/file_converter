from django.contrib import admin

from files.models import UploadedFile
from reports.models import ReportRequest


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    """Административный интерфейс для управления файлами."""

    list_display = (id, "file", "user", "uploaded_at")
    list_filter = ("file",)
    search_fields = ("user", "uploaded_at")
