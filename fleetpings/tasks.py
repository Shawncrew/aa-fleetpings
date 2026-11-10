"""
Celery tasks for AA Fleet Pings
"""

# Third Party
from celery import shared_task

# Django
from django.db import transaction
from django.utils import timezone

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

# AA Fleet Pings
from fleetpings import __title__
from fleetpings.app_settings import optimer_installed
from fleetpings.helper.discord_webhook import ping_discord_webhook
from fleetpings.helper.fleet_actions import create_optimer
from fleetpings.helper.ping_context import get_ping_context_from_form_data
from fleetpings.models import ScheduledPing
from fleetpings.providers.applogger import AppLogger

logger = AppLogger(my_logger=get_extension_logger(name=__name__))


@shared_task
def send_scheduled_pings() -> None:
    """
    Periodic task: send all scheduled pings that are due.

    Intended to run roughly once a minute via CELERYBEAT_SCHEDULE.

    :return:
    :rtype:
    """

    now = timezone.now()
    due_ping_ids = list(
        ScheduledPing.objects.filter(
            status=ScheduledPing.Status.PENDING, scheduled_time__lte=now
        )
        .order_by("scheduled_time")
        .values_list("pk", flat=True)
    )

    if not due_ping_ids:
        return

    logger.info(msg=f"{__title__}: Processing {len(due_ping_ids)} due scheduled ping(s)")

    for ping_id in due_ping_ids:
        _send_single_scheduled_ping(ping_id=ping_id)


def _send_single_scheduled_ping(ping_id: int) -> None:
    """
    Atomically claim and dispatch a single scheduled ping.

    Uses ``select_for_update(skip_locked=True)`` so overlapping task runs can
    never dispatch the same ping twice.

    :param ping_id:
    :type ping_id:
    :return:
    :rtype:
    """

    with transaction.atomic():
        ping = (
            ScheduledPing.objects.select_for_update(skip_locked=True)
            .filter(pk=ping_id, status=ScheduledPing.Status.PENDING)
            .first()
        )

        # Already handled by another worker, cancelled, or currently locked
        if ping is None:
            return

        try:
            ping_context = get_ping_context_from_form_data(form_data=ping.form_data)

            main_character = (
                ping.user.profile.main_character if ping.user_id else None
            )

            if main_character is None:
                raise ValueError(
                    "The scheduling user no longer has a main character; "
                    "cannot attribute the ping."
                )

            # Create an optimer if it was requested (deferred to send time so the
            # post time reflects when the ping actually went out)
            if optimer_installed() and ping_context["create_optimer"]:
                create_optimer(
                    ping_context=ping_context, eve_character=main_character
                )

            # Dispatch the Discord webhook
            if ping_context["ping_channel"]["webhook"]:
                ping_discord_webhook(ping_context=ping_context, user=ping.user)
            else:
                raise ValueError(
                    "The scheduled ping has no target webhook to send to."
                )

            ping.status = ScheduledPing.Status.SENT
            ping.sent_at = timezone.now()
            ping.error = ""
            ping.save(update_fields=["status", "sent_at", "error"])

            logger.info(
                msg=f"{__title__}: Sent scheduled ping #{ping.pk} for user {ping.user}"
            )
        except Exception as exc:  # pylint: disable=broad-except
            ping.status = ScheduledPing.Status.FAILED
            ping.error = str(exc)
            ping.save(update_fields=["status", "error"])

            logger.error(
                msg=f"{__title__}: Failed to send scheduled ping #{ping.pk}: {exc}"
            )
