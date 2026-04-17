from django.core.management.base import BaseCommand, CommandError
from django.db.utils import DatabaseError

from core.health import check_database


class Command(BaseCommand):
    help = "Verify database connectivity for hosted readiness checks."

    def handle(self, *args, **options) -> None:
        try:
            check_database()
        except DatabaseError as exc:
            raise CommandError(
                "Database readiness check failed. Verify DATABASE_URL, credentials, "
                "network access, and database availability before deploying."
            ) from exc

        self.stdout.write(self.style.SUCCESS("Database readiness check passed."))
