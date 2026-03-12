import os
import uuid

from django.conf import settings
from django.db import models


def upload_to(instance, filename):
    ext = os.path.splitext(filename)[1]
    filename_uuid = str(uuid.uuid4()).replace("-", "")
    return os.path.join("uploads", f"{filename_uuid}{ext}")


class UploadedFile(models.Model):
    """Модель для оригиналов файлов."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="uploaded_files",
    )

    file = models.FileField(upload_to=upload_to)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return os.path.basename(self.file.name)
