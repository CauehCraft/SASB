from django.core.mail import send_mail
from django.conf import settings

class NotificationService:
    @staticmethod
    def enviar_confirmacao_agendamento(agendamento):
        send_mail(
            'Confirmação de Agendamento',
            f'Seu agendamento para {agendamento.servico.nome} foi confirmado.',
            settings.DEFAULT_FROM_EMAIL,
            [agendamento.cliente.email],
            fail_silently=False,
        )

    @staticmethod
    def enviar_lembrete(agendamento):
        # Enviar lembrete 24h antes
        pass