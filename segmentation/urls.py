# from django.urls import path
# from . import views

# urlpatterns = [
#     path('segment/',            views.segment_nodules,       name='segment_nodules'),
#     path('scan/<int:scan_id>/', views.get_scan_segmentations, name='get_scan_segmentations'),
# ]
from django.urls import path
from . import views

urlpatterns = [
    path('segment/',                     views.segment_nodules,        name='segment_nodules'),
    path('segment-existing/<int:scan_id>/', views.segment_existing_scan, name='segment_existing_scan'),
    path('scan/<int:scan_id>/',          views.get_scan_segmentations, name='get_scan_segmentations'),
]