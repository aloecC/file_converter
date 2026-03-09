import logging
import os

import pandas as pd
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_report_task(self, report_request_id):
    """
    Фоновая задача для обработки файлов и генерации отчетов.
    bind=True позволяет обращаться к self (атрибутам самой задачи).
    """
    from files.models import UploadedFile

    from .models import ReportRequest

    try:
        try:
            report_request = ReportRequest.objects.get(id=report_request_id)
        except ReportRequest.DoesNotExist:
            logger.error(f"ReportRequest с ID {report_request_id} не найден.")
            return

        report_request.status = "PROCESSING"
        report_request.task_id = self.request.id
        report_request.save()

        logger.info(f"Начало обработки задачи {report_request_id}")

        df = None

        if report_request.uploaded_file:

            input_file_path = report_request.uploaded_file.file.path
            logger.info(f"Чтение файла: {input_file_path}")

            if not os.path.exists(input_file_path):
                raise FileNotFoundError(f"Файл не найден на диске: {input_file_path}")

            if input_file_path.endswith(".csv"):
                df = pd.read_csv(input_file_path)
            elif input_file_path.endswith((".xls", ".xlsx")):
                df = pd.read_excel(input_file_path)
            else:
                raise ValueError("Формат файла не поддерживается. Используйте CSV или Excel.")

        elif report_request.parameters:
            logger.info(f"Файл не предоставлен. Генерируем данные из параметров: {report_request.parameters}")
            df = pd.DataFrame(report_request.parameters)

        if df is None or df.empty:
            raise ValueError("Нет данных для обработки (файл пуст или не предоставлен).")

        params = report_request.parameters or {}
        filter_col = params.get("filter_col")
        filter_val = params.get("filter_val")

        if filter_col and filter_val and filter_col in df.columns:
            df = df[df[filter_col] == filter_val]
            logger.info(f"Применен фильтр: {filter_col} = {filter_val}")

        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        output_filename = f"report_{report_request.id}_{timestamp}.xlsx"

        relative_path = os.path.join("reports", output_filename)

        full_output_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

        df.to_excel(full_output_path, index=False)
        logger.info(f"Файл успешно сохранен: {full_output_path}")

        report_request.output_file = relative_path  # Записываем путь в FileField
        report_request.status = "SUCCESS"
        report_request.save()

        return f"Report {report_request_id} processed successfully."

    except Exception as e:
        logger.exception(f"Критическая ошибка при обработке отчета {report_request_id}")

        ReportRequest.objects.filter(id=report_request_id).update(status="FAILED")

        raise e
