import os
import uuid

from rest_framework import serializers

from config import settings
from files.models import UploadedFile

from .models import ReportRequest
from .tasks import process_report_task


class ReportRequestSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра списка и деталей отчета."""

    user = serializers.ReadOnlyField(source="user.username")

    # DRF автоматически подставит полный URL для FileField, если request есть в контексте

    class Meta:
        model = ReportRequest
        fields = [
            "id",
            "user",
            "uploaded_file",
            "parameters",
            "task_id",
            "status",
            "output_file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "user",
            "task_id",
            "status",
            "output_file",
            "created_at",
            "updated_at",
        ]


class FileUploadSerializer(serializers.Serializer):
    """
    Сериализатор для загрузки файла и немедленного запуска обработки.
    """

    file = serializers.FileField(write_only=True)
    parameters = serializers.JSONField(required=False, default=dict)

    def create(self, validated_data):
        request = self.context.get("request")
        user = request.user if request else None

        file_data = validated_data.pop("file")
        parameters = validated_data.get("parameters", {})

        uploaded_file_instance = UploadedFile.objects.create(
            file=file_data, user=user if user.is_authenticated else None
        )

        report_request = ReportRequest.objects.create(
            user=user,
            uploaded_file=uploaded_file_instance,
            parameters=parameters,
            status="PENDING",  # Начальный статус
        )

        task = process_report_task.delay(report_request.id)

        report_request.task_id = task.id
        report_request.save()
        return report_request

    def to_representation(self, instance):
        """
        После создания возвращаем данные через основной сериализатор,
        чтобы ответ API был полным и красивым.
        """
        return ReportRequestSerializer(instance, context=self.context).data
