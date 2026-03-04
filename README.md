#  Веб-сервис для генерации отчетов / конвертер файлов

Цель:
Создать веб-приложение, где пользователь может загрузить файл (например, CSV, Excel) или указать параметры, а сервис в фоновом режиме обработает его (конвертирует, сгенерирует отчет) и предоставит результат для скачивания.

Используемые технологии:
•  Python 3.10+
•  Django
•  Django REST Framework (DRF)
•  PostgreSQL
•  Celery (для фоновых задач)
•  Redis (для Celery брокера и кэширования)
•  pandas (для работы с CSV/Excel)
•  openpyxl, xlrd (для Excel)
•  reportlab или weasyprint (для PDF отчетов, опционально)
•  django-environ, dj-database-url
•  djangorestframework-simplejwt (для аутентификации, если нужно)
•  Docker, Docker Compose
•  Pytest, pytest-django, factory-boy
•  black, isort, ruff, pre-commit

 🚀 Основные возможности

 🛠 Технологический стек

 📋 Требования

 ⚙️ Установка и настройка

1. Клонируйте репозиторий
2. Установите зависимости
3. Настройте переменные окружения:
  Создайте файл .env в корне проекта или пропишите в settings.py
    TELEGRAM_BOT_TOKEN=your_token_here
    SECRET_KEY=django_secret_key
    DEBUG=True
    CELERY_BROKER_URL=redis://localhost:6379/0
4. Примените миграции
5. Создайте суперпользователя (для доступа к админке)

||| Шаги для запуска проекта через
docker-compose:
1. Копирование Dockerfile и Docker-compose.yml
2. Настройка файла .env (Конфиденциальность)
3. Проверка файлов исключений .gitignore и .dockerignore
Первый запуск
1. docker compose down -v # Остановит и удалит все контейнеры, сети, и ТОМЫ (postgres_data, media)
2. docker compose up -d --build # Запустит все сервисы и соберет образы
*  -d: Запустить в фоновом режиме.
  •  --build: Пересобрать образы (особенно важно после изменений в Dockerfile).
3. docker compose ps # Проверит статус контейнеров(Все сервисы должны быть в статусе Up или Running)
4. docker compose logs -f  # Покажет логи (для отладки)
5. docker compose exec app poetry run python manage.py migrate # Выполнит миграции Django
6. docker compose exec app poetry run python manage.py createsuperuser # Создаст суперпользователя Django
7. Проверьте веб-приложение:
  Откройте браузер и перейдите на http://localhost:8000/. Должна открыться страница Django.
  Проверьте админку: http://localhost:8000/admin/.
8. docker compose logs worker # Проверит Celery Worker


🏃 Запуск проекта

📐 Архитектура базы данных

 📝 Использование

 🤝 Контакты
•  Разработчик: Щербакова Дарья/aloecC
•  Проект создан в рамках обучения DRF

---
