from rest_framework.routers import DefaultRouter

from .views import ReportRequestViewSet

router = DefaultRouter()
router.register(r"reports", ReportRequestViewSet, basename="reportrequest")

urlpatterns = router.urls
