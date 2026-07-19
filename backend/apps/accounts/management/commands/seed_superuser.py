from __future__ import annotations

import os

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create the first Django superuser from SUPERUSER_EMAIL / SUPERUSER_PASSWORD."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--email",
            default=os.environ.get("SUPERUSER_EMAIL", "admin@darling.pk"),
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("SUPERUSER_PASSWORD", "DarlingAdmin123!"),
        )
        parser.add_argument("--first-name", default="Darling")

    def handle(self, *args, **options) -> None:
        email = str(options["email"]).strip().lower()
        password = str(options["password"])
        first_name = str(options["first_name"]).strip()

        existing = User.objects.filter(is_superuser=True).first()
        if existing is not None:
            self.stdout.write(
                self.style.WARNING(
                    f"Superuser already exists ({existing.email or existing.username}). Skipping."
                )
            )
            return

        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(
            username__iexact=email
        ).exists():
            user = User.objects.filter(email__iexact=email).first() or User.objects.filter(
                username__iexact=email
            ).first()
            assert user is not None
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            if first_name and not user.first_name:
                user.first_name = first_name
            user.email = email
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Promoted existing user to superuser: {email}"))
        else:
            user = User.objects.create_superuser(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
            )
            self.stdout.write(self.style.SUCCESS(f"Created superuser: {email}"))

        EmailAddress.objects.update_or_create(
            user=user,
            email=email,
            defaults={"primary": True, "verified": True},
        )
        self.stdout.write(f"Password: {password}")
        self.stdout.write("Sign in at /admin/login")
