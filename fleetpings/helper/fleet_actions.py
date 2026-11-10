"""
Shared fleet side effects (optimer creation) that are triggered both by the
synchronous ping view and by the scheduled-ping Celery task.
"""

# Django
from django.utils import timezone


def create_optimer(ping_context: dict, eve_character) -> None:
    """
    Create a fleet operations timer (optimer) from a ping context.

    :param ping_context: The ping context built from the submitted form data
    :type ping_context: dict
    :param eve_character: The EveCharacter to attribute the optimer to
    :type eve_character: allianceauth.eveonline.models.EveCharacter
    :return:
    :rtype:
    """

    # Alliance Auth
    from allianceauth.optimer.models import OpTimer

    OpTimer(
        doctrine=ping_context["doctrine"]["name"],
        system=ping_context["formup_location"],
        start=ping_context["formup_time"]["datetime_string"],
        duration="N/A",
        operation_name=ping_context["fleet_name"],
        fc=ping_context["fleet_commander"],
        post_time=timezone.now(),
        eve_character=eve_character,
    ).save()
