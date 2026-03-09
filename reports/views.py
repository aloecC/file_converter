import os

from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import ReportRequest
from .serializers import FileUploadSerializer, ReportRequestSerializer
from .tasks import process_report_task


class ReportRequestViewSet(viewsets.ModelViewSet):
    serializer_class = ReportRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReportRequest.objects.filter(user=self.request.user).order_by("-created_at")

    def perform_create(self, serializer):
        """
        Используется при создании отчета БЕЗ файла (только по параметрам JSON).
        """

        report_request = serializer.save(user=self.request.user)

        task = process_report_task.delay(report_request.id)

        report_request.task_id = task.id
        report_request.save()

    @action(detail=False, methods=["post"], serializer_class=FileUploadSerializer)
    def upload_file(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            report_request = serializer.save()

            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def status(self, request, pk=None):
        """
        Метод для быстрой проверки статуса конкретного отчета.
        """
        report_request = get_object_or_404(ReportRequest, pk=pk, user=request.user)

        return Response(
            {
                "id": report_request.id,
                "status": report_request.status,
                "task_id": report_request.task_id,
                "error_message": report_request.error_message,
                "output_file": (report_request.output_file.url if report_request.output_file else None),
            }
        )
