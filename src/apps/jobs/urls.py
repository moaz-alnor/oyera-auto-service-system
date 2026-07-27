"""URL routes for job-card workflows."""

from django.urls import path

from apps.jobs import views

app_name = "jobs"

urlpatterns = [
    path(
        "",
        views.job_list,
        name="list",
    ),
    path(
        "new/",
        views.job_create,
        name="create",
    ),
    path(
        "<int:job_card_id>/inspections/new/",
        views.inspection_create,
        name="inspection_create",
    ),
    path(
        "<int:job_card_id>/notes/new/",
        views.note_create,
        name="note_create",
    ),
    path(
        "<int:job_card_id>/cancel/",
        views.job_cancel,
        name="cancel",
    ),
    path(
        "<int:job_card_id>/release/",
        views.vehicle_release_create,
        name="release_create",
    ),
    path(
        "releases/<int:release_id>/",
        views.vehicle_release_detail,
        name="release_detail",
    ),
    path(
        "<int:job_card_id>/",
        views.job_detail,
        name="detail",
    ),
]
