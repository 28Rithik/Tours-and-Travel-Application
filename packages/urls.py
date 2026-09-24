from django.urls import path
from . import views
from .manifest_import import download_manifest_template_csv, upload_manifest_csv_view

app_name = 'packages'

urlpatterns = [
    path('quote/preview/', views.preview_tour_quotation, name='preview_tour_quotation'),
    path('quote/<int:package_id>/', views.generate_tour_quotation, name='quotation_proposal'),
    path('voucher/<int:package_id>/', views.generate_tour_voucher, name='tour_voucher'),
    path('manifest/<int:expedition_id>/rooming-list/', views.view_rooming_list, name='view_rooming_list'),
    path('manifest/template/download/', download_manifest_template_csv, name='download_manifest_template'),
    path('manifest/upload/', upload_manifest_csv_view, name='upload_manifest_csv'),
    path('api/package/<int:package_id>/info/', views.api_package_info, name='api_package_info'),
    path('api/template/<int:template_id>/info/', views.api_template_info, name='api_template_info'),
    path('api/vehicle/<int:vehicle_id>/info/', views.api_vehicle_info, name='api_vehicle_info'),
]
