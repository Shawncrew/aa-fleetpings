"""
The views
"""

# pylint: disable=import-outside-toplevel

# Standard Library
import json
from datetime import datetime, timezone as dt_timezone

# Django
from django.conf import settings
from django.contrib.auth.decorators import login_required, permission_required
from django.core.handlers.wsgi import WSGIRequest
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import dateformat, timezone
from django.utils.translation import gettext_lazy as _

# Alliance Auth
from allianceauth.services.hooks import get_extension_logger

# AA Fleet Pings
from fleetpings import __title__
from fleetpings.app_settings import (
    can_add_srp_links,
    fittings_installed,
    optimer_installed,
    srp_module_installed,
    srp_module_is,
    use_fittings_module_for_doctrines,
)
from fleetpings.form import FleetPingForm
from fleetpings.helper.discord_webhook import ping_discord_webhook
from fleetpings.helper.fleet_actions import create_optimer
from fleetpings.helper.ping_context import get_ping_context_from_form_data
from fleetpings.helper.urls import reverse_absolute
from fleetpings.models import (
    DiscordPingTarget,
    FleetComm,
    FleetDoctrine,
    FleetType,
    FormupLocation,
    ScheduledPing,
    Setting,
    Webhook,
)
from fleetpings.providers.applogger import AppLogger

logger = AppLogger(my_logger=get_extension_logger(name=__name__))


@login_required
@permission_required(perm="fleetpings.basic_access")
def index(request: WSGIRequest) -> HttpResponse:
    """
    Index view

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.info(msg=f"Fleet pings view called by user {request.user}")

    srp_module_available_to_user = srp_module_installed() and any(
        can_add_srp_links(request=request, module_name=module_name)
        for module_name in ["aasrp", "allianceauth.srp"]
    )

    context = {
        "title": __title__,
        "webhooks_configured": Webhook.objects.filter(
            Q(restricted_to_group__in=request.user.groups.all())
            | Q(restricted_to_group__isnull=True),
            is_enabled=True,
        ).exists(),
        "site_url": settings.SITE_URL,
        "optimer_installed": optimer_installed(),
        "fittings_installed": fittings_installed(),
        "main_character": request.user.profile.main_character,
        "srp_module_available_to_user": srp_module_available_to_user,
        "form": FleetPingForm,
    }

    return render(
        request=request, template_name="fleetpings/index.html", context=context
    )


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_get_ping_targets(request: WSGIRequest) -> HttpResponse:
    """
    Get ping targets for the current user

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.info(msg=f"Getting ping targets for user {request.user}")

    additional_discord_ping_targets = (
        DiscordPingTarget.objects.filter(
            Q(restricted_to_group__in=request.user.groups.all())
            | Q(restricted_to_group__isnull=True),
            is_enabled=True,
        )
        .distinct()
        .order_by("name")
    )

    return render(
        request=request,
        template_name="fleetpings/partials/form/segments/ping-targets.html",
        context={
            "ping_targets": additional_discord_ping_targets,
            "use_default_ping_targets": Setting.objects.get_setting(
                setting_key=Setting.Field.USE_DEFAULT_PING_TARGETS
            ),
        },
    )


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_get_webhooks(request: WSGIRequest) -> HttpResponse:
    """
    Get webhooks for current user

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.info(msg=f"Getting webhooks for user {request.user}")

    webhooks = (
        Webhook.objects.filter(
            Q(restricted_to_group__in=request.user.groups.all())
            | Q(restricted_to_group__isnull=True),
            is_enabled=True,
        )
        .distinct()
        .order_by("name")
    )

    return render(
        request=request,
        template_name="fleetpings/partials/form/segments/ping-channel.html",
        context={"webhooks": webhooks},
    )


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_get_fleet_types(request: WSGIRequest) -> HttpResponse:
    """
    Get fleet types for current user

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.info(msg=f"Getting fleet types for user {request.user}")

    fleet_types = (
        FleetType.objects.filter(
            Q(restricted_to_group__in=request.user.groups.all())
            | Q(restricted_to_group__isnull=True),
            is_enabled=True,
        )
        .distinct()
        .order_by("name")
    )

    return render(
        request=request,
        template_name="fleetpings/partials/form/segments/fleet-type.html",
        context={
            "fleet_types": fleet_types,
            "use_default_fleet_types": Setting.objects.get_setting(
                setting_key=Setting.Field.USE_DEFAULT_FLEET_TYPES
            ),
        },
    )


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_get_formup_locations(request: WSGIRequest) -> HttpResponse:
    """
    Get formup locations for current user

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.info(msg=f"Getting formup locations for user {request.user}")

    formup_locations = FormupLocation.objects.filter(is_enabled=True).order_by("name")

    return render(
        request=request,
        template_name="fleetpings/partials/form/segments/fleet-formup-location.html",
        context={"formup_locations": formup_locations},
    )


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_get_fleet_comms(request: WSGIRequest) -> HttpResponse:
    """
    Get fleet comms for current user

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.info(msg=f"Getting formup locations for user {request.user}")

    fleet_comms = FleetComm.objects.filter(is_enabled=True).order_by("name")

    return render(
        request=request,
        template_name="fleetpings/partials/form/segments/fleet-comms.html",
        context={"fleet_comms": fleet_comms},
    )


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_get_fleet_doctrines(request: WSGIRequest) -> HttpResponse:
    """
    Get fleet doctrines for current user

    :param request:
    :type request:
    :return:
    :rtype:
    """

    logger.info(msg=f"Getting fleet doctrines for user {request.user}")

    # Get doctrines
    if use_fittings_module_for_doctrines() is True:
        # Third Party
        from fittings.views import _get_docs_qs

        groups = request.user.groups.all()
        doctrines = _get_docs_qs(request, groups).order_by("name")
    else:
        doctrines = (
            FleetDoctrine.objects.filter(
                Q(restricted_to_group__in=request.user.groups.all())
                | Q(restricted_to_group__isnull=True),
                is_enabled=True,
            )
            .distinct()
            .order_by("name")
        )

    return render(
        request=request,
        template_name="fleetpings/partials/form/segments/fleet-doctrine.html",
        context={
            "doctrines": doctrines,
            "use_fleet_doctrines": use_fittings_module_for_doctrines(),
        },
    )


@login_required
@permission_required(perm="fleetpings.basic_access")
def _create_optimer(request: WSGIRequest, ping_context: dict):
    """
    Create an optimer entry

    :param request:
    :type request:
    :param ping_context:
    :type ping_context:
    :return:
    :rtype:
    """

    create_optimer(
        ping_context=ping_context,
        eve_character=request.user.profile.main_character,
    )

    logger.info(msg=f"Optimer created by user {request.user}")


@login_required
@permission_required(perm="fleetpings.basic_access")
def _create_aasrp_link(request: WSGIRequest, ping_context: dict) -> dict:
    """
    Create an SRP link in aasrp

    :param request:
    :type request:
    :param ping_context:
    :type ping_context:
    :return:
    :rtype:
    """

    # Third Party
    from aasrp.models import SrpLink

    # Django
    from django.utils.crypto import get_random_string

    srp_code = get_random_string(length=16)

    SrpLink(
        srp_name=ping_context["fleet_name"],
        fleet_time=timezone.now(),
        fleet_doctrine=ping_context["doctrine"]["name"],
        srp_code=srp_code,
        fleet_commander=request.user.profile.main_character,
        creator=request.user,
    ).save()

    logger.info(msg=f"SRP Link created by user {request.user}")

    return {
        "success": True,
        "code": srp_code,
        "link": reverse_absolute(viewname="aasrp:request_srp", args=[srp_code]),
    }


@login_required
@permission_required(perm="fleetpings.basic_access")
def _create_allianceauth_srp_link(request: WSGIRequest, ping_context: dict) -> dict:
    """
    Create an SRP link in allianceauth.srp

    :param request:
    :type request:
    :param ping_context:
    :type ping_context:
    :return:
    :rtype:
    """

    # Alliance Auth
    from allianceauth.srp.models import SrpFleetMain
    from allianceauth.srp.views import random_string

    srp_code = random_string(8)

    SrpFleetMain(
        fleet_name=ping_context["fleet_name"],
        fleet_doctrine=ping_context["doctrine"]["name"],
        fleet_time=timezone.now(),
        fleet_srp_code=srp_code,
        fleet_commander=request.user.profile.main_character,
    ).save()

    logger.info(msg=f"SRP Link created by user {request.user}")

    return {
        "success": True,
        "code": srp_code,
        "link": reverse_absolute(viewname="srp:request", args=[srp_code]),
    }


@login_required
@permission_required(perm="fleetpings.basic_access")
def _create_srp_link(request: WSGIRequest, ping_context: dict) -> dict:
    """
    Create an SRP link
    Conditions:
        - formup == now
        - SRP == yes
        - fleet_name and doctrine are given

    :param request:
    :type request:
    :param ping_context:
    :type ping_context:
    :return:
    :rtype:
    """

    if ping_context["fleet_name"] and ping_context["doctrine"]["name"]:
        # Create aasrp link (prioritized app)
        if srp_module_is(module_name="aasrp") and can_add_srp_links(
            request=request, module_name="aasrp"
        ):
            return _create_aasrp_link(request=request, ping_context=ping_context)

        # Create allianceauth.srp link
        if srp_module_is(module_name="allianceauth.srp") and can_add_srp_links(
            request=request, module_name="allianceauth.srp"
        ):
            return _create_allianceauth_srp_link(
                request=request, ping_context=ping_context
            )

    return {
        "success": False,
        "message": _("Not all mandatory information available to create an SRP link."),
    }


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_create_fleet_ping(request: WSGIRequest) -> HttpResponse:
    """
    Create a fleet ping

    :param request:
    :type request:
    :return:
    :rtype:
    """

    context = {"success": False, "message": ""}

    if request.method == "POST":
        form = FleetPingForm(data=json.loads(request.body))

        logger.debug(msg=f"Fleet ping form data: {form.data}")

        if form.is_valid():
            logger.info(msg="Fleet ping information received")

            # Get ping context
            ping_context = get_ping_context_from_form_data(form_data=form.cleaned_data)

            logger.debug(msg=f"Ping context: {ping_context}")

            # Scheduled (send later) pre-ping? Store it and let the Celery task
            # dispatch it when it is due, instead of sending it right now.
            if form.cleaned_data.get("send_later"):
                return _schedule_fleet_ping(
                    request=request, form=form, ping_context=ping_context
                )

            # Create optimer is requested
            if optimer_installed() and ping_context["create_optimer"]:
                _create_optimer(
                    request=request,
                    ping_context=ping_context,
                )

                context["message"] = str(_("Fleet operations timer has been created…"))

            # Create an SRP link if requested
            if srp_module_installed() and ping_context["srp"]["create_srp_link"]:
                ping_context["srp"]["link"] = _create_srp_link(
                    request=request,
                    ping_context=ping_context,
                )

                context["message"] = str(_("SRP link has been created…"))

            # If we have a Discord webhook, ping it
            if ping_context["ping_channel"]["webhook"]:
                ping_discord_webhook(ping_context=ping_context, user=request.user)

            logger.info(msg=f"Fleet ping created by user {request.user}")

            ping_context["request"] = request

            context["ping_context"] = render_to_string(
                template_name="fleetpings/partials/ping/copy-paste-text.html",
                context=ping_context,
                request=request,
            )
            context["success"] = True
        else:
            context["message"] = str(_("Form invalid. Please check your input."))
    else:
        context["message"] = str(_("No form data submitted."))

    return HttpResponse(content=json.dumps(context), content_type="application/json")


def _parse_scheduled_time(form_data: dict) -> datetime | None:
    """
    Parse the requested send time from the submitted form data.

    EVE time is UTC, so both the JavaScript timestamp and the raw datetime
    string are interpreted as UTC.

    :param form_data:
    :type form_data:
    :return: Timezone-aware (UTC) datetime, or None if it could not be parsed
    :rtype:
    """

    timestamp = form_data.get("scheduled_timestamp")

    if timestamp:
        try:
            return datetime.fromtimestamp(int(float(timestamp)), tz=dt_timezone.utc)
        except (ValueError, TypeError, OSError):
            pass

    raw_datetime = form_data.get("scheduled_time")

    if raw_datetime:
        try:
            return datetime.strptime(raw_datetime, "%Y-%m-%d %H:%M").replace(
                tzinfo=dt_timezone.utc
            )
        except ValueError:
            pass

    return None


def _schedule_fleet_ping(
    request: WSGIRequest, form: FleetPingForm, ping_context: dict
) -> HttpResponse:
    """
    Store a pre-ping to be sent later by the Celery task.

    :param request:
    :type request:
    :param form:
    :type form:
    :param ping_context:
    :type ping_context:
    :return:
    :rtype:
    """

    context = {"success": False, "message": ""}

    # "Send Later" only makes sense for a pre-ping
    if not form.cleaned_data.get("pre_ping"):
        context["message"] = str(
            _('"Send Later" can only be used together with a pre-ping.')
        )

        return HttpResponse(
            content=json.dumps(context), content_type="application/json"
        )

    scheduled_time = _parse_scheduled_time(form_data=form.cleaned_data)

    if scheduled_time is None:
        context["message"] = str(_("Please provide a valid send time."))

        return HttpResponse(
            content=json.dumps(context), content_type="application/json"
        )

    if scheduled_time <= timezone.now():
        context["message"] = str(_("The send time must be in the future."))

        return HttpResponse(
            content=json.dumps(context), content_type="application/json"
        )

    # Resolve the target webhook (for display) from the submitted channel id
    webhook = None

    if form.cleaned_data.get("ping_channel"):
        try:
            webhook = Webhook.objects.get(pk=form.cleaned_data["ping_channel"])
        except (Webhook.DoesNotExist, ValueError):
            webhook = None

    main_character = request.user.profile.main_character
    character_name = (
        main_character.character_name if main_character is not None else ""
    )

    ScheduledPing.objects.create(
        user=request.user,
        character_name=character_name,
        scheduled_time=scheduled_time,
        fleet_name=form.cleaned_data.get("fleet_name", ""),
        webhook=webhook,
        form_data=form.cleaned_data,
        status=ScheduledPing.Status.PENDING,
    )

    logger.info(
        msg=f"Fleet ping scheduled for {scheduled_time} by user {request.user}"
    )

    # Render a preview of the ping so the FC can see what will be sent
    ping_context["request"] = request
    context["ping_context"] = render_to_string(
        template_name="fleetpings/partials/ping/copy-paste-text.html",
        context=ping_context,
        request=request,
    )
    context["scheduled"] = True
    context["message"] = str(
        _("Pre-ping scheduled for %(datetime)s EVE time.")
        % {"datetime": dateformat.format(scheduled_time, "Y-m-d H:i")}
    )
    context["success"] = True

    return HttpResponse(content=json.dumps(context), content_type="application/json")


def _user_can_manage_scheduled_pings(request: WSGIRequest) -> bool:
    """
    Whether the user may see / cancel scheduled pings of all users.

    :param request:
    :type request:
    :return:
    :rtype:
    """

    return request.user.has_perm(perm="fleetpings.manage_scheduled_pings")


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_get_scheduled_pings(request: WSGIRequest) -> HttpResponse:
    """
    Get the list of pending scheduled pings for the current user
    (or all pending pings for managers).

    :param request:
    :type request:
    :return:
    :rtype:
    """

    scheduled_pings = ScheduledPing.objects.filter(
        status=ScheduledPing.Status.PENDING
    ).select_related("user", "webhook")

    can_manage = _user_can_manage_scheduled_pings(request=request)

    if not can_manage:
        scheduled_pings = scheduled_pings.filter(user=request.user)

    return render(
        request=request,
        template_name="fleetpings/partials/scheduled/scheduled-list.html",
        context={
            "scheduled_pings": scheduled_pings.order_by("scheduled_time"),
            "can_manage_scheduled_pings": can_manage,
        },
    )


@login_required
@permission_required(perm="fleetpings.basic_access")
def ajax_cancel_scheduled_ping(request: WSGIRequest) -> HttpResponse:
    """
    Cancel a pending scheduled ping.

    :param request:
    :type request:
    :return:
    :rtype:
    """

    context = {"success": False, "message": ""}

    if request.method != "POST":
        context["message"] = str(_("No form data submitted."))

        return HttpResponse(
            content=json.dumps(context), content_type="application/json"
        )

    try:
        payload = json.loads(request.body)
        ping_id = int(payload.get("id"))
    except (ValueError, TypeError, json.JSONDecodeError):
        context["message"] = str(_("Invalid request."))

        return HttpResponse(
            content=json.dumps(context), content_type="application/json"
        )

    scheduled_pings = ScheduledPing.objects.filter(
        pk=ping_id, status=ScheduledPing.Status.PENDING
    )

    if not _user_can_manage_scheduled_pings(request=request):
        scheduled_pings = scheduled_pings.filter(user=request.user)

    scheduled_ping = scheduled_pings.first()

    if scheduled_ping is None:
        context["message"] = str(
            _("Scheduled ping not found or you are not allowed to cancel it.")
        )

        return HttpResponse(
            content=json.dumps(context), content_type="application/json"
        )

    scheduled_ping.status = ScheduledPing.Status.CANCELLED
    scheduled_ping.save(update_fields=["status"])

    logger.info(
        msg=f"Scheduled ping #{scheduled_ping.pk} cancelled by user {request.user}"
    )

    context["success"] = True
    context["message"] = str(_("Scheduled ping cancelled."))

    return HttpResponse(content=json.dumps(context), content_type="application/json")
