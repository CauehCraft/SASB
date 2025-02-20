from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from datetime import datetime
from django.utils import timezone


class UsuarioSASB(AbstractUser):
    nome = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='usuario_sasb_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='usuario_sasb_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        abstract = True

    def listar_agendamentos(self, cliente=None):
        if cliente:
            return Agendamento.objects.filter(cliente=cliente)
        return Agendamento.objects.all()

    def selecionar_agendamento(self, id_agendamento):
        return Agendamento.objects.get(id=id_agendamento)

    def inserir_dados_pagamento(self, dados_pagamento):
        pass

    def cancelar_agendamento(self, id_agendamento):
        agendamento = self.selecionar_agendamento(id_agendamento)
        agendamento.status = 'CANCELADO'
        agendamento.save()


class Cliente(UsuarioSASB):
    fidelidade_pontos = models.IntegerField(default=0)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='cliente_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='cliente_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        db_table = 'cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'


class Funcionario(UsuarioSASB):
    cargo = models.CharField(max_length=100)
    horario_trabalho = models.CharField(max_length=255)
    servicos = models.ManyToManyField('Servico', related_name='funcionarios')

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='funcionario_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='funcionario_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    class Meta:
        db_table = 'funcionario'
        verbose_name = 'Funcionario'
        verbose_name_plural = 'Funcionarios'


class Servico(models.Model):
    nome = models.CharField(max_length=255)
    duracao = models.IntegerField(help_text='Duração em minutos')
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def buscar_horarios_disponiveis(self):
        return Horario.objects.filter(disponivel=True)

    class Meta:
        db_table = 'servico'
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'


class Horario(models.Model):
    data = models.DateTimeField()
    disponivel = models.BooleanField(default=True)

    class Meta:
        db_table = 'horario'
        verbose_name = 'Horário'
        verbose_name_plural = 'Horários'

    def esta_disponivel_para_funcionario(self, funcionario):
        return not Agendamento.objects.filter(
            horario=self,
            funcionario=funcionario,
            status__in=['AGENDADO', 'CONFIRMADO']
        ).exists()

    def esta_disponivel_para_cliente(self, cliente):
        return not Agendamento.objects.filter(
            horario=self,
            cliente=cliente,
            status__in=['AGENDADO', 'CONFIRMADO']
        ).exists()

    def buscar_profissionais_disponiveis(self):
        from .models import Funcionario
        funcionarios_ocupados = Agendamento.objects.filter(
            horario=self,
            status__in=['AGENDADO', 'CONFIRMADO']
        ).values_list('funcionario_id', flat=True)
        return Funcionario.objects.exclude(id__in=funcionarios_ocupados)


class DadosPagamento(models.Model):
    numero_cartao = models.CharField(max_length=16)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=50)

    class Meta:
        db_table = 'dados_pagamento'
        verbose_name = 'Dados de Pagamento'
        verbose_name_plural = 'Dados de Pagamentos'


class Pagamento(models.Model):
    data = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50)
    dados_pagamento = models.ForeignKey(DadosPagamento, on_delete=models.PROTECT)

    def registrar_pagamento(self, dados_pagamento):
        self.dados_pagamento = dados_pagamento
        self.status = 'CONFIRMADO'
        self.save()

    def gerar_comprovante(self):
        return f"Comprovante de pagamento #{self.id}"

    def enviar_comprovante(self, usuario):
        pass

    class Meta:
        db_table = 'pagamento'
        verbose_name = 'Pagamento'
        verbose_name_plural = 'Pagamentos'


class Agendamento(models.Model):
    STATUS_CHOICES = [
        ('AGENDADO', 'Agendado'),
        ('CONFIRMADO', 'Confirmado'),
        ('CANCELADO', 'Cancelado'),
        ('CONCLUIDO', 'Concluído'),
    ]

    data = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AGENDADO')
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='agendamentos')
    servico = models.ForeignKey('Servico', on_delete=models.PROTECT)
    horario = models.ForeignKey('Horario', on_delete=models.PROTECT)
    funcionario = models.ForeignKey('Funcionario', on_delete=models.PROTECT)
    pagamento = models.OneToOneField('Pagamento', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'agendamento'
        verbose_name = 'Agendamento'
        verbose_name_plural = 'Agendamentos'

    def clean(self):
        if not self.pk:  # Apenas para novos agendamentos
            # Verificar se o horário já está ocupado para este funcionário
            conflito_funcionario = Agendamento.objects.filter(
                horario=self.horario,
                funcionario=self.funcionario,
                status__in=['AGENDADO', 'CONFIRMADO']
            ).exists()

            if conflito_funcionario:
                raise ValidationError({
                    'horario': 'Este horário já está ocupado para o funcionário selecionado.'
                })

            # Verificar se o horário está disponível
            if not self.horario.disponivel:
                raise ValidationError({
                    'horario': 'Este horário não está mais disponível.'
                })

            # Verificar se o cliente já tem agendamento no mesmo horário
            conflito_cliente = Agendamento.objects.filter(
                horario=self.horario,
                cliente=self.cliente,
                status__in=['AGENDADO', 'CONFIRMADO']
            ).exists()

            if conflito_cliente:
                raise ValidationError({
                    'horario': 'Você já possui um agendamento neste horário.'
                })

            # Verificar se a data do agendamento é futura
            if self.horario.data <= timezone.now():
                raise ValidationError({
                    'horario': 'Não é possível fazer agendamentos em datas passadas.'
                })

            # Verificar se o horário está dentro do horário de trabalho do funcionário
            hora = self.horario.data.hour
            horario_trabalho = self.funcionario.horario_trabalho.split('-')
            hora_inicio = int(horario_trabalho[0].split(':')[0])
            hora_fim = int(horario_trabalho[1].split(':')[0])

            if hora < hora_inicio or hora >= hora_fim:
                raise ValidationError({
                    'horario': 'Este horário está fora do período de trabalho do funcionário.'
                })

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        
        # Atualizar disponibilidade do horário
        if self.status in ['AGENDADO', 'CONFIRMADO']:
            self.horario.disponivel = False
            self.horario.save()
        elif self.status == 'CANCELADO':
            self.horario.disponivel = True
            self.horario.save()

    def confirmar_agendamento(self):
        if self.status == 'AGENDADO':
            self.status = 'CONFIRMADO'
            self.save()
            return True
        return False

    def cancelar_agendamento(self):
        self.status = 'CANCELADO'
        self.save()

# class Avaliacao(models.Model):
#     agendamento = models.OneToOneField(Agendamento, on_delete=models.CASCADE)
#     nota = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
#     comentario = models.TextField(blank=True)
#     data = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         db_table = 'avaliacao'
#         verbose_name = 'Avaliação'
#         verbose_name_plural = 'Avaliações'

# class Promocao(models.Model):
#     servico = models.ForeignKey(Servico, on_delete=models.CASCADE)
#     desconto = models.DecimalField(max_digits=5, decimal_places=2)
#     data_inicio = models.DateTimeField()
#     data_fim = models.DateTimeField()
#     ativa = models.BooleanField(default=True)