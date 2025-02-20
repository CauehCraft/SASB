from django.contrib import admin
from .models import (
    Cliente,
    Funcionario,
    Servico,
    Horario,
    DadosPagamento,
    Pagamento,
    Agendamento
)

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', 'telefone', 'fidelidade_pontos']
    search_fields = ['nome', 'email']

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ['nome', 'email', 'telefone', 'cargo']
    search_fields = ['nome', 'cargo']

@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'duracao', 'valor']
    search_fields = ['nome']

@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ['data', 'disponivel']
    list_filter = ['disponivel']

@admin.register(DadosPagamento)
class DadosPagamentoAdmin(admin.ModelAdmin):
    list_display = ['valor', 'metodo']

@admin.register(Pagamento)
class PagamentoAdmin(admin.ModelAdmin):
    list_display = ['data', 'status']
    list_filter = ['status']

@admin.register(Agendamento)
class AgendamentoAdmin(admin.ModelAdmin):
    list_display = ['cliente', 'servico', 'data', 'status']
    list_filter = ['status']
    search_fields = ['cliente__nome', 'servico__nome']