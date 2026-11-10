# AA Fleet Pings :: Scheduled pings (Send Later)

# Django
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("fleetpings", "0016_alliance_auth_proxy_models"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="aafleetpings",
            options={
                "default_permissions": (),
                "managed": False,
                "permissions": (
                    ("basic_access", "Can access this app"),
                    (
                        "manage_scheduled_pings",
                        "Can view and cancel scheduled pings of all users",
                    ),
                ),
            },
        ),
        migrations.CreateModel(
            name="ScheduledPing",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "character_name",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=255,
                        verbose_name="Character name",
                    ),
                ),
                (
                    "scheduled_time",
                    models.DateTimeField(
                        db_index=True,
                        help_text="When the pre-ping should be sent (EVE / UTC time)",
                        verbose_name="Send at (EVE time)",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("cancelled", "Cancelled"),
                            ("failed", "Failed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=16,
                        verbose_name="Status",
                    ),
                ),
                (
                    "fleet_name",
                    models.CharField(
                        blank=True,
                        default="",
                        max_length=254,
                        verbose_name="Fleet name",
                    ),
                ),
                (
                    "form_data",
                    models.JSONField(default=dict, verbose_name="Form data"),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Created at"
                    ),
                ),
                (
                    "sent_at",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="Sent at"
                    ),
                ),
                ("error", models.TextField(blank=True, default="", verbose_name="Error")),
                (
                    "webhook",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scheduled_pings",
                        to="fleetpings.webhook",
                        verbose_name="Ping channel",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fleetpings_scheduled_pings",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Scheduled by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Scheduled ping",
                "verbose_name_plural": "Scheduled pings",
                "ordering": ("scheduled_time",),
                "default_permissions": (),
            },
        ),
    ]
