from typing import Tuple

from django.conf import settings
from django.core import validators
from django.db import models
from django.utils import timezone

from apps.auth_token import constants, crypto
from apps.auth_token.models import BaseAuthToken
from apps.user_management.models import Organization, User

MOBILE_APP_AUTH_VERIFICATION_TOKEN_TIMEOUT_SECONDS = 60 * (5 if settings.DEBUG else 1)


def get_expire_date():
    return timezone.now() + timezone.timedelta(seconds=MOBILE_APP_AUTH_VERIFICATION_TOKEN_TIMEOUT_SECONDS)


class MobileAppVerificationTokenQueryset(models.QuerySet):
    def filter(self, *args, **kwargs):
        now = timezone.now()
        return super().filter(*args, **kwargs, revoked_at=None, expire_date__gte=now)

    def delete(self):
        self.update(revoked_at=timezone.now())


class MobileAppVerificationToken(BaseAuthToken):
    objects = MobileAppVerificationTokenQueryset.as_manager()
    user = models.ForeignKey(
        "user_management.User",
        related_name="mobile_app_verification_token_set",
        on_delete=models.CASCADE,
    )
    organization = models.ForeignKey(
        "user_management.Organization", related_name="mobile_app_verification_token_set", on_delete=models.CASCADE
    )
    expire_date = models.DateTimeField(default=get_expire_date)

    @classmethod
    def create_auth_token(cls, user: User, organization: Organization) -> Tuple["MobileAppVerificationToken", str]:
        token_string = crypto.generate_short_token_string()
        digest = crypto.hash_token_string(token_string)

        instance = cls.objects.create(
            token_key=token_string[: constants.TOKEN_KEY_LENGTH],
            digest=digest,
            user=user,
            organization=organization,
        )
        return instance, token_string


class MobileAppAuthToken(BaseAuthToken):
    user = models.OneToOneField(to=User, null=False, blank=False, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        to=Organization, null=False, blank=False, related_name="mobile_app_auth_tokens", on_delete=models.CASCADE
    )

    @classmethod
    def create_auth_token(cls, user: User, organization: Organization) -> Tuple["MobileAppAuthToken", str]:
        token_string = crypto.generate_token_string()
        digest = crypto.hash_token_string(token_string)

        instance = cls.objects.create(
            token_key=token_string[: constants.TOKEN_KEY_LENGTH],
            digest=digest,
            user=user,
            organization=organization,
        )
        return instance, token_string


class MobileAppUserSettings(models.Model):
    # Sound names are stored without extension, extension is added when sending push notifications
    IOS_SOUND_NAME_EXTENSION = ".aiff"
    ANDROID_SOUND_NAME_EXTENSION = ".mp3"

    class VolumeType(models.TextChoices):
        CONSTANT = "constant"
        INTENSIFYING = "intensifying"

    user = models.OneToOneField(to=User, null=False, on_delete=models.CASCADE)

    # Push notification settings for default notifications
    default_notification_sound_name = models.CharField(max_length=100, default="default_sound")
    default_notification_volume_type = models.CharField(
        max_length=50, choices=VolumeType.choices, default=VolumeType.CONSTANT
    )

    # APNS only allows to specify volume for critical notifications,
    # so "default_notification_volume" and "default_notification_volume_override" are only used on Android
    default_notification_volume = models.FloatField(
        validators=[validators.MinValueValidator(0.0), validators.MaxValueValidator(1.0)], default=0.8
    )
    default_notification_volume_override = models.BooleanField(default=False)

    # Push notification settings for important notifications
    important_notification_sound_name = models.CharField(max_length=100, default="default_sound_important")
    important_notification_volume_type = models.CharField(
        max_length=50, choices=VolumeType.choices, default=VolumeType.CONSTANT
    )
    important_notification_volume = models.FloatField(
        validators=[validators.MinValueValidator(0.0), validators.MaxValueValidator(1.0)], default=0.8
    )
    important_notification_volume_override = models.BooleanField(default=True, null=True)

    # For the "Mobile push important" step it's possible to make notifications non-critical
    # if "override DND" setting is disabled in the app
    important_notification_override_dnd = models.BooleanField(default=True)

    # Push notification settings for info notifications
    # this is used for non escalation related push notifications such as the
    # "You're going OnCall soon" push notification
    info_notifications_enabled = models.BooleanField(default=False)

    info_notification_sound_name = models.CharField(max_length=100, default="default_sound", null=True)
    info_notification_volume_type = models.CharField(
        max_length=50, choices=VolumeType.choices, default=VolumeType.CONSTANT, null=True
    )

    # APNS only allows to specify volume for critical notifications,
    # so "info_notification_volume" and "info_notification_volume_override" are only used on Android
    info_notification_volume = models.FloatField(
        validators=[validators.MinValueValidator(0.0), validators.MaxValueValidator(1.0)], default=0.8, null=True
    )
    info_notification_volume_override = models.BooleanField(default=False, null=True)

    # these choices + the below column are used to calculate when to send the "You're Going OnCall soon"
    # push notification
    # ONE_HOUR, TWELVE_HOURS, ONE_DAY, ONE_WEEK = range(4)
    TWELVE_HOURS_IN_SECONDS = 12 * 60 * 60
    ONE_DAY_IN_SECONDS = TWELVE_HOURS_IN_SECONDS * 2
    ONE_WEEK_IN_SECONDS = ONE_DAY_IN_SECONDS * 7

    NOTIFICATION_TIMING_CHOICES = (
        (TWELVE_HOURS_IN_SECONDS, "twelve hours before"),
        (ONE_DAY_IN_SECONDS, "one day before"),
        (ONE_WEEK_IN_SECONDS, "one week before"),
    )
    going_oncall_notification_timing = models.IntegerField(
        choices=NOTIFICATION_TIMING_CHOICES, default=TWELVE_HOURS_IN_SECONDS
    )

    locale = models.CharField(max_length=50, null=True)
