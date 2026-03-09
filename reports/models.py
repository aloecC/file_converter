import uuid  # Для генерации уникальных имен файлов

from django.conf import settings
from django.db import models

import files
from config.settings import MEDIA_URL


class ReportRequest(models.Model):
    """Модель отчета."""

    STATUS_CHOICES = [
        ("PENDING", "В ожидании"),
        ("PROCESSING", "Обработка"),
        ("SUCCESS", "Успех"),
        ("FAILED", "Ошибка"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="report_requests", on_delete=models.CASCADE)

    uploaded_file = models.ForeignKey(
        "files.UploadedFile", on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Загруженный файл"
    )

    parameters = models.JSONField(
        blank=True, null=True, verbose_name="Параметры, если загрузки файла нет (например, период, фильтры)"
    )

    error_message = models.TextField(null=True, blank=True)

    task_id = models.CharField(max_length=255, unique=True, blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")

    output_file = models.FileField(
        upload_to="reports/%Y/%m/%d/", blank=True, null=True, verbose_name="Файл результата"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Report Request #{self.id} ({self.status})"

    def get_output_url(self, request_host):
        if self.status == "SUCCESS" and self.output_filename:
            return f"{request_host}{MEDIA_URL}{self.output_filename}"
        return None
