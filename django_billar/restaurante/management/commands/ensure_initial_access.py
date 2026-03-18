import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Garante que exista um usuário gerente padrão para primeiro acesso.'

    def handle(self, *args, **options):
        user_model = get_user_model()
        username = os.getenv('BILLAR_INIT_ADMIN_USERNAME', 'gerente')
        password = os.getenv('BILLAR_INIT_ADMIN_PASSWORD', 'admin123')

        user, created = user_model.objects.get_or_create(
            username=username,
            defaults={
                'role': 'gerente',
                'is_staff': True,
                'is_superuser': True,
            },
        )

        if created:
            user.set_password(password)
            user.save(update_fields=['password'])
            self.stdout.write(self.style.SUCCESS(f'Usuário inicial criado: {username}'))
            self.stdout.write(self.style.WARNING(f'Senha inicial: {password}'))
            return

        self.stdout.write(f'Usuário inicial já existe: {username}')
