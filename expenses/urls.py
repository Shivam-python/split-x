# urls.py
from django.urls import path, include

import expenses.views as expense_views
from rest_framework import routers

router = routers.DefaultRouter()
router.register('groups', expense_views.GroupAPIView, basename='groups')
router.register('expense', expense_views.ExpenseViewSet, basename='expenses')
router.register('payment', expense_views.SettlementViewSet, basename='payments')
router.register('reminder', expense_views.ReminderViewSet, basename='reminders')

urlpatterns = [
    path('', include(router.urls)),
    path('get-payment-link/', expense_views.PaymentSimulator.as_view(), name='generate-payment-link'),
    path('payment-summary/<str:payment_uid>', expense_views.PaymentSummary.as_view(), name='payment-summary')
]
