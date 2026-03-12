import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from files.models import UploadedFile
from reports.models import ReportRequest
from reports.serializers import ReportRequestSerializer
from reports.tasks import process_report_task


class MockAsyncResult:
    def __init__(self, id):
        self.id = id


def mock_delay(*args, **kwargs):
    return MockAsyncResult("mock_task_id_123")


class ReportRequestViewSetTests(APITestCase):
    def setUp(self):
        """
        Настройка тестовой среды перед каждым тестом.
        """
        self.user = get_user_model().objects.create_user(username="testuser", password="password")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.report_request = ReportRequest.objects.create(user=self.user, status="PENDING", task_id="initial_task_id")
        self.list_url = reverse("reportrequest-list")
        self.detail_url = reverse("reportrequest-detail", kwargs={"pk": self.report_request.pk})
        self.upload_url = reverse("reportrequest-upload-file")
        self.status_url = reverse("reportrequest-status", kwargs={"pk": self.report_request.pk})

        import unittest.mock

        mock_obj = unittest.mock.MagicMock()
        mock_obj.side_effect = mock_delay

        self.patcher_celery_delay = unittest.mock.patch("reports.serializers.process_report_task.delay", new=mock_obj)
        self.mock_celery = self.patcher_celery_delay.start()

    def tearDown(self):
        """
        Очистка после каждого теста.
        """
        self.patcher_celery_delay.stop()

        ReportRequest.objects.all().delete()
        UploadedFile.objects.all().delete()
        get_user_model().objects.all().delete()

    def test_list_reports(self):
        """
        Проверяеn, что пользователь видит только свои отчеты.
        """
        other_user = get_user_model().objects.create_user(username="otheruser", password="password")
        ReportRequest.objects.create(user=other_user, status="SUCCESS")

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIsInstance(response.data, dict)
        self.assertIn("results", response.data)
        self.assertIn("count", response.data)

        results = response.data["results"]
        self.assertEqual(len(results), 1)

        report_data = results[0]
        self.assertEqual(report_data["id"], self.report_request.id)
        self.assertEqual(report_data["user"], self.user.username)

    def test_create_report_without_file(self):
        """
        Проверяет создание отчета только с JSON параметрами.
        """
        data = {
            "parameters": {"period": "last_month", "filters": ["sales", "customers"], "format": "pdf"},
        }

        response = self.client.post(self.list_url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("id", response.data)
        self.assertIn("task_id", response.data)
        self.assertEqual(response.data["task_id"], "mock_task_id_123")

        report_request = ReportRequest.objects.get(id=response.data["id"])
        self.assertEqual(report_request.user, self.user)
        self.assertEqual(report_request.status, "PENDING")
        self.assertEqual(report_request.task_id, "mock_task_id_123")
        self.assertEqual(
            report_request.parameters, {"period": "last_month", "filters": ["sales", "customers"], "format": "pdf"}
        )
        self.assertIsNone(report_request.uploaded_file)
        self.mock_celery.assert_called_once_with(report_request.id)

    def test_upload_file_success(self):
        """
        Проверяем успешную загрузку файла и создание отчета с параметрами.
        """
        from django.core.files.uploadedfile import SimpleUploadedFile

        file_content = b"This is a test file content."
        uploaded_file_instance = SimpleUploadedFile("test_report.txt", file_content, content_type="text/plain")

        report_params = {
            "period": "current_quarter",
            "category": "electronics",
        }

        data = {
            "file": uploaded_file_instance,
            "parameters": json.dumps(report_params),
        }

        response = self.client.post(self.upload_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

        self.assertEqual(ReportRequest.objects.count(), 2)
        self.assertEqual(UploadedFile.objects.count(), 1)

        new_report_request = ReportRequest.objects.filter(user=self.user).order_by("-created_at").first()
        self.assertIsNotNone(new_report_request)

        self.assertEqual(new_report_request.user, self.user)
        self.assertEqual(new_report_request.status, "PENDING")
        self.assertEqual(new_report_request.parameters, report_params)
        self.assertIsNotNone(new_report_request.uploaded_file)

        created_uploaded_file = new_report_request.uploaded_file
        self.assertEqual(created_uploaded_file.user, self.user)

        self.assertIn("uploads/", created_uploaded_file.file.name)
        self.assertTrue(created_uploaded_file.file.name.endswith(".txt"))

        file_basename = created_uploaded_file.file.name.split("/")[-1]
        file_uuid_part = file_basename.split(".")[0]
        self.assertEqual(len(file_uuid_part), 32)

        self.mock_celery.assert_called_once_with(new_report_request.id)
        self.assertEqual(new_report_request.task_id, "mock_task_id_123")

        self.assertIn("id", response.data)
        self.assertEqual(response.data["id"], new_report_request.id)

        self.assertIn("user", response.data)
        self.assertEqual(response.data["user"], self.user.username)

        self.assertIn("uploaded_file", response.data)
        self.assertEqual(response.data["uploaded_file"], created_uploaded_file.id)

        self.assertIn("parameters", response.data)
        self.assertEqual(response.data["parameters"], report_params)

        self.assertIn("task_id", response.data)
        self.assertEqual(response.data["task_id"], "mock_task_id_123")

        self.assertIn("status", response.data)
        self.assertEqual(response.data["status"], "PENDING")

        self.assertIn("output_file", response.data)
        self.assertIsNone(response.data["output_file"])

        self.assertIn("created_at", response.data)
        self.assertIn("updated_at", response.data)

    def test_upload_file_invalid_data(self):
        """
        Проверяем ошибку при некорректных данных для загрузки файла (нет файла).
        """

        data = {}
        response = self.client.post(self.upload_url, data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)
        self.assertEqual(response.data["file"][0].code, "required")
        self.assertIn("No file was submitted.", response.data["file"][0])
        self.assertEqual(ReportRequest.objects.count(), 1)
        self.assertEqual(UploadedFile.objects.count(), 0)

    def test_get_report_status(self):
        """
        Проверяем получение статуса конкретного отчета.
        """
        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.report_request.id)
        self.assertEqual(response.data["status"], "PENDING")
        self.assertEqual(response.data["task_id"], "initial_task_id")
        self.assertIsNone(response.data["error_message"])
        self.assertIsNone(response.data["output_file"])

    def test_get_report_status_not_found_for_other_user(self):
        """
        Проверяем, что другой пользователь не может получить статус чужого отчета.
        """
        other_user = get_user_model().objects.create_user(username="otheruser", password="password")
        report_other = ReportRequest.objects.create(user=other_user, status="SUCCESS")

        other_client = APIClient()
        other_client.force_authenticate(user=other_user)

        response = self.client.get(reverse("reportrequest-status", kwargs={"pk": report_other.pk}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_report_status_with_output_file(self):
        """
        Проверяем, что URL выходного файла возвращается, если он есть.
        """
        import os

        from django.conf import settings
        from django.core.files.uploadedfile import SimpleUploadedFile

        file_content = b"Report content."
        output_file_name = "output_report.txt"
        temp_media_root = None
        media_root = getattr(settings, "MEDIA_ROOT", None)
        if not media_root:

            from tempfile import mkdtemp

            temp_media_root = mkdtemp()
            setattr(settings, "MEDIA_ROOT", temp_media_root)
            media_root = temp_media_root

        file_path_in_media = os.path.join(settings.MEDIA_ROOT, "reports", "2026", "03", "12", output_file_name)
        os.makedirs(os.path.dirname(file_path_in_media), exist_ok=True)
        with open(file_path_in_media, "wb") as f:
            f.write(file_content)

        self.report_request.output_file.name = os.path.join("reports", "2026", "03", "12", output_file_name)
        self.report_request.status = "SUCCESS"
        self.report_request.save()

        response = self.client.get(self.status_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "SUCCESS")
        self.assertIsNotNone(response.data["output_file"])

        self.assertIn(settings.MEDIA_URL, response.data["output_file"])
        self.assertIn(output_file_name, response.data["output_file"])

        if temp_media_root:
            import shutil

            shutil.rmtree(temp_media_root)
