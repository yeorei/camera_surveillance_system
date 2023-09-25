from django.urls import path
from . import views

# URLConf
urlpatterns = [
    path('', views.index, name='index'),
    path('camera_view/', views.camera_view, name='camera_view'),
    path('update_alert/', views.update_alert, name='update_alert'),
    path('recordings/', views.recordings, name='recordings'),
    path('delete_recording/<int:id>/', views.delete_recording, name='delete_recording'),
    path('edit_account/', views.edit_account, name='edit_account'),
    path('video_feed', views.video_feed, name='video_feed'),
]