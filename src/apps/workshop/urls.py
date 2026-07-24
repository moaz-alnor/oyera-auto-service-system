"""URL routes for workshop planning and execution."""

from django.urls import path

from apps.workshop import views

app_name = "workshop"

urlpatterns = [
    path(
        "",
        views.work_order_list,
        name="list",
    ),
    path(
        "new/",
        views.work_order_create,
        name="create",
    ),
    path(
        "<int:work_order_id>/",
        views.work_order_detail,
        name="detail",
    ),
    path(
        "<int:work_order_id>/start/",
        views.work_order_start,
        name="start",
    ),
    path(
        "<int:work_order_id>/hold/",
        views.work_order_hold,
        name="hold",
    ),
    path(
        "<int:work_order_id>/resume/",
        views.work_order_resume,
        name="resume",
    ),
    path(
        "<int:work_order_id>/complete/",
        views.work_order_complete,
        name="complete",
    ),
    path(
        "tasks/<int:work_task_id>/assign/",
        views.technician_assignment_create,
        name="assign_technician",
    ),
    path(
        "assignments/<int:assignment_id>/remove/",
        views.technician_assignment_remove,
        name="remove_technician",
    ),
    path(
        "tasks/<int:work_task_id>/start/",
        views.work_task_start,
        name="start_task",
    ),
    path(
        "tasks/<int:work_task_id>/block/",
        views.work_task_block,
        name="block_task",
    ),
    path(
        "tasks/<int:work_task_id>/review/",
        views.work_task_submit_for_review,
        name="submit_task_review",
    ),
    path(
        "tasks/<int:work_task_id>/approve/",
        views.work_task_approve,
        name="approve_task",
    ),
    path(
        "tasks/<int:work_task_id>/notes/new/",
        views.work_task_note_create,
        name="add_task_note",
    ),
]
