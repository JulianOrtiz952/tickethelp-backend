from rest_framework.routers import DefaultRouter
from .views import UserViewSet, AdminViewSet, TechnicianViewSet, ClientViewSet

router = DefaultRouter()
router.register('users', UserViewSet, basename='user')
router.register('admins', AdminViewSet, basename='admin')
router.register('technicians', TechnicianViewSet, basename='technician')
router.register('clients', ClientViewSet, basename='client')

urlpatterns = router.urls