from rest_framework import serializers
from django.core.exceptions import ValidationError
from ..models import (
    Cliente,
    Funcionario,
    Servico,
    Horario,
    DadosPagamento,
    Pagamento,
    Agendamento
)


class ClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = ['id', 'nome', 'email', 'telefone', 'fidelidade_pontos']


class FuncionarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Funcionario
        fields = ['id', 'nome', 'email', 'telefone', 'cargo', 'horario_trabalho']


class ServicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Servico
        fields = ['id', 'nome', 'duracao', 'valor']

    def validate(self, data):
        if data.get('duracao', 0) <= 0:
            raise serializers.ValidationError({'duracao': 'A duração deve ser maior que zero.'})
        if data.get('valor', 0) <= 0:
            raise serializers.ValidationError({'valor': 'O valor deve ser maior que zero.'})
        return data


class HorarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Horario
        fields = ['id', 'data', 'disponivel']


class DadosPagamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = DadosPagamento
        fields = ['id', 'numero_cartao', 'valor', 'metodo']


class PagamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pagamento
        fields = ['id', 'data', 'status', 'dados_pagamento']
        read_only_fields = ['data']

    def validate_status(self, value):
        valid_status = ['PENDENTE', 'CONFIRMADO', 'CANCELADO']
        if value not in valid_status:
            raise serializers.ValidationError(f"Status deve ser um dos seguintes: {', '.join(valid_status)}")
        return value

    def create(self, validated_data):
        if 'status' not in validated_data:
            validated_data['status'] = 'PENDENTE'
        return super().create(validated_data)


class AgendamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agendamento
        fields = [
            'id', 'data', 'status', 'cliente', 'servico',
            'horario', 'funcionario', 'pagamento'
        ]
        read_only_fields = ['status']

    def validate(self, data):
        try:
            # Criar uma instância temporária para usar o clean()
            instance = Agendamento(
                data=data.get('data'),
                cliente=data.get('cliente'),
                servico=data.get('servico'),
                horario=data.get('horario'),
                funcionario=data.get('funcionario')
            )
            instance.clean()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

        return data

    def create(self, validated_data):
        if 'cliente' not in validated_data and self.context['request'].user:
            validated_data['cliente'] = self.context['request'].user
        instance = super().create(validated_data)
        return instance