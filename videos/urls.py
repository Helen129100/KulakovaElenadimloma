from django.urls import path

from . import views

app_name = "videos"


urlpatterns = [
    path("increment_views/", views.increment_views, name="increment_views"),
    path("video/<int:id>/", views.video, name="video"),
    path("add_video/", views.add_video, name="add_video"),
    path("comment/", views.comment, name="comment"),
    path("remove/", views.remove, name="remove"),
    path("edit_video/<int:id>/", views.edit_video, name="edit_video"),
    path("like/", views.like, name="like"),
    path("home/", views.home, name="home"),
    path("subscribe/", views.subscribe, name="subscribe"),
    path("video/delete/<int:video_id>/", views.delete_video, name="delete_video"),
    path(
        "set_language/", views.set_language, name="set_language"
    ),  # Добавленный маршрут
]
