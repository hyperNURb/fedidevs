import time

import schedule
from django.core import management
from django_rich.management import RichCommand
from sentry_sdk.crons import monitor

from stats.models import store_daily_stats


class Command(RichCommand):
    help = "Starts the scheduler"

    @monitor(monitor_slug="daily-sync")
    def job(self):
        self.console.print("Running crawler")
        management.call_command("crawler", skip_inactive_for=3, pre_filter=True)
        self.console.print("Running indexer")
        management.call_command("indexer")
        self.console.print("Running optimizer")
        management.call_command("optimizer")
        self.console.print("Running statuser")
        management.call_command("statuser")
        self.console.print("Running dailystats")
        management.call_command("dailystats")

    def handle(self, *args, **options):
        self.console.print("Starting scheduler 🕐")
        schedule.every().day.at("01:00").do(self.job)

        while True:
            schedule.run_pending()
            time.sleep(1)
