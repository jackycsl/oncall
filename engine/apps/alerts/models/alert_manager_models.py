import hashlib
import json

from django.db import transaction

from apps.alerts.models import Alert, AlertGroup


class AlertGroupForAlertManager(AlertGroup):
    MAX_ALERTS_IN_GROUP_FOR_AUTO_RESOLVE = 500

    def is_alert_a_resolve_signal(self, alert):
        non_resolved_hashes = set()
        hash = alert.get_integration_optimization_hash()
        if alert.calculated_is_resolve_signal:
            # Calculate leftover hashes
            for alert in AlertForAlertManager.objects.filter(group=self).exclude(pk=alert.pk)[
                : AlertGroupForAlertManager.MAX_ALERTS_IN_GROUP_FOR_AUTO_RESOLVE
            ]:
                if alert.calculated_is_resolve_signal:
                    try:
                        non_resolved_hashes.remove(alert.get_integration_optimization_hash())
                    except KeyError:
                        pass
                else:
                    non_resolved_hashes.add(alert.get_integration_optimization_hash())
            # Remove last hash
            try:
                non_resolved_hashes.remove(hash)
            except KeyError:
                pass
            return len(non_resolved_hashes) == 0
        else:
            return False

    class Meta:
        app_label = "alerts"
        proxy = True


class AlertForAlertManager(Alert):
    def get_integration_optimization_hash(self):
        if self.integration_optimization_hash is None:
            with transaction.atomic():
                if self.id is not None:
                    alert = AlertForAlertManager.objects.filter(id=self.id).select_for_update().get()
                else:
                    alert = self

                _hash = dict(alert.raw_request_data.get("labels", {}))
                _hash = json.dumps(_hash, sort_keys=True)
                _hash = hashlib.md5(str(_hash).encode()).hexdigest()
                alert.integration_optimization_hash = _hash

                if self.id is not None:
                    alert.save()

            return alert.integration_optimization_hash
        else:
            return self.integration_optimization_hash

    @property
    def calculated_is_resolve_signal(self):
        return self.raw_request_data.get("status", "") == "resolved"

    class Meta:
        app_label = "alerts"
        proxy = True
