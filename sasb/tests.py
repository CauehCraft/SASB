from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from decimal import Decimal
from .models import (
    Cliente,
    Funcionario,
    Servico,
    Horario,
    DadosPagamento,
    Pagamento,
    Agendamento
)
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework.authtoken.models import Token
import json


class SASBTestCase(APITestCase):
    def setUp(self):
        # Configurar cliente API
        self.client = APIClient()

        # Criar superuser para autenticação
        self.superuser = Cliente.objects.create_superuser(
            username='MrUser',
            password='MrUser.123',
            email='mruser@example.com',
            nome='Mr User',
            telefone='1234567890'
        )

        # Autenticar cliente API usando force_authenticate
        self.client.force_authenticate(user=self.superuser)

        # Criar dados iniciais
        self.criar_dados_base()

    def criar_dados_base(self):
        # Criar cliente
        self.cliente = Cliente.objects.create_user(
            username='cliente1',
            password='senha123',
            email='cliente@teste.com',
            nome='Cliente Teste',
            telefone='999999999',
            fidelidade_pontos=0
        )

        # Criar serviço
        self.servico = Servico.objects.create(
            nome='Corte de Cabelo',
            duracao=60,
            valor=Decimal('50.00')
        )

        # Criar funcionário e add o service
        self.funcionario = Funcionario.objects.create_user(
            username='func1',
            password='senha123',
            email='funcionario@teste.com',
            nome='Funcionário Teste',
            telefone='888888888',
            cargo='Cabeleireiro',
            horario_trabalho='08:00-18:00'
        )
        self.funcionario.servicos.add(self.servico)

        # Criar horário
        self.horario_data = timezone.now().replace(
            hour=10, minute=0, second=0, microsecond=0
        ) + timedelta(days=1) 
        self.horario = Horario.objects.create(
            data=self.horario_data,
            disponivel=True
        )

    def test_1_criar_cliente(self):
        """Teste de criação de cliente"""
        data = {
            'username': 'novocliente',
            'password': 'senha123',
            'email': 'novo@cliente.com',
            'nome': 'Novo Cliente',
            'telefone': '777777777',
            'fidelidade_pontos': 0
        }
        response = self.client.post('/api/clientes/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Cliente.objects.count(), 3)

    def test_2_criar_funcionario(self):
        """Teste de criação de funcionário"""
        data = {
            'username': 'novofunc',
            'password': 'senha123',
            'email': 'novo@funcionario.com',
            'nome': 'Novo Funcionário',
            'telefone': '666666666',
            'cargo': 'Manicure',
            'horario_trabalho': '09:00-17:00'
        }
        response = self.client.post('/api/funcionarios/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Funcionario.objects.count(), 2)

    def test_3_criar_servico(self):
        """Teste de criação de serviço"""
        data = {
            'nome': 'Manicure',
            'duracao': 30,
            'valor': '35.00'
        }
        response = self.client.post('/api/servicos/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Servico.objects.count(), 2)

    def test_4_criar_horario(self):
        """Teste de criação de horário"""
        data = {
            'data': (timezone.now() + timedelta(days=2)).isoformat(),
            'disponivel': True
        }
        response = self.client.post('/api/horarios/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Horario.objects.count(), 2)

    def test_5_criar_agendamento(self):
        """Teste de criação de agendamento"""
        data = {
            'data': self.horario_data.isoformat(),  # Usando self.horario_data agora
            'cliente': self.cliente.id,
            'servico': self.servico.id,
            'horario': self.horario.id,
            'funcionario': self.funcionario.id
        }
        response = self.client.post('/api/agendamentos/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Agendamento.objects.count(), 1)

    def test_6_confirmar_agendamento(self):
        """Teste de confirmação de agendamento"""
        agendamento = Agendamento.objects.create(
            data=self.horario_data,  # Data controlada
            cliente=self.cliente,
            servico=self.servico,
            horario=self.horario,
            funcionario=self.funcionario,
            status='AGENDADO'
        )

        response = self.client.post(
            f'/api/agendamentos/{agendamento.id}/confirmar/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, 'CONFIRMADO')

    def test_7_criar_pagamento(self):
        """Teste de criação de pagamento"""
        # Criar dados de pagamento primeiro
        dados_pagamento_data = {
            'numero_cartao': '1234567890123456',
            'valor': '50.00',
            'metodo': 'CREDITO'
        }
        response = self.client.post('/api/dados-pagamento/', dados_pagamento_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        dados_pagamento_id = response.data['id']

        # Criar pagamento
        pagamento_data = {
            'status': 'PENDENTE',
            'dados_pagamento': dados_pagamento_id
        }
        response = self.client.post('/api/pagamentos/', pagamento_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Pagamento.objects.count(), 1)

    def test_8_listar_agendamentos(self):
        """Teste de listagem de agendamentos"""
        response = self.client.get('/api/agendamentos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_9_buscar_horarios_disponiveis(self):
        """Teste de busca de horários disponíveis"""
        response = self.client.get(f'/api/servicos/{self.servico.id}/horarios_disponiveis/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_10_atualizar_cliente(self):
        """Teste de atualização de dados do cliente"""
        data = {
            'nome': 'Cliente Atualizado',
            'telefone': '999999900'
        }
        response = self.client.patch(f'/api/clientes/{self.cliente.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.cliente.refresh_from_db()
        self.assertEqual(self.cliente.nome, 'Cliente Atualizado')

    def test_11_cancelar_agendamento(self):
        """Teste de cancelamento de agendamento"""
        agendamento = Agendamento.objects.create(
            data=self.horario_data,
            cliente=self.cliente,
            servico=self.servico,
            horario=self.horario,
            funcionario=self.funcionario,
            status='AGENDADO'
        )

        response = self.client.post(
            f'/api/agendamentos/{agendamento.id}/cancelar/'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        agendamento.refresh_from_db()
        self.assertEqual(agendamento.status, 'CANCELADO')
        self.assertTrue(agendamento.horario.disponivel)

    def test_12_deletar_servico(self):
        """Teste de exclusão de serviço"""
        response = self.client.delete(f'/api/servicos/{self.servico.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Servico.objects.count(), 0)

    def test_13_verificar_permissoes(self):
        """Teste de verificação de permissões"""
        # Criar um usuário comum
        cliente_comum = Cliente.objects.create_user(
            username='comum',
            password='senha123',
            email='comum@teste.com',
            nome='Cliente Comum',
            telefone='555555555'
        )
        
        # Salvar a autenticação atual
        current_user = self.client._credentials

        # Autenticar como usuário comum
        self.client.force_authenticate(user=cliente_comum)
        
        # Tentar acessar endpoint restrito
        response = self.client.delete(f'/api/servicos/{self.servico.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Restaurar a autenticação original
        self.client.credentials(HTTP_AUTHORIZATION=current_user)

    def test_14_buscar_agendamentos_cliente(self):
        """Teste de busca de agendamentos por cliente"""
        horarios = []
        base_time = timezone.now() + timedelta(days=1)
        base_time = base_time.replace(hour=9, minute=0, second=0, microsecond=0)  # Set to 9 AM
        for i in range(3):
            horario = Horario.objects.create(
                data=base_time + timedelta(hours=i),  # 9 AM, 10 AM, 11 AM
                disponivel=True
            )
            horarios.append(horario)

        for i in range(3):
            Agendamento.objects.create(
                data=horarios[i].data,
                cliente=self.cliente,
                servico=self.servico,
                horario=horarios[i],
                funcionario=self.funcionario,
                status='AGENDADO'
            )

        response = self.client.get(f'/api/agendamentos/?cliente={self.cliente.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    def test_15_validacao_dados(self):
        """Teste de validação de dados"""
        data = {
            'nome': 'Serviço Inválido',
            'duracao': -30,  # valor inválido
            'valor': '-35.00'  # valor inválido
        }
        response = self.client.post('/api/servicos/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_16_atualizacao_parcial_funcionario(self):
        """Teste de atualização parcial de funcionário"""
        data = {
            'cargo': 'Gerente'
        }
        response = self.client.patch(f'/api/funcionarios/{self.funcionario.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.funcionario.refresh_from_db()
        self.assertEqual(self.funcionario.cargo, 'Gerente')

    def test_17_filtro_agendamentos_data(self):
        """Teste de filtro de agendamentos por data"""
        data_futura = timezone.now() + timedelta(days=5)
        response = self.client.get(f'/api/agendamentos/?data={data_futura.date().isoformat()}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_18_fluxo_agendamento_completo(self):
        """Teste do fluxo completo de agendamento"""
        # Criar Horario
        # horario_teste = Horario.objects.create(
        #     data=timezone.now() + timedelta(days=1),
        #     disponivel=True
        # )
        # Buscar horários disponíveis
        response = self.client.get(
            '/api/agendamento-processo/buscar_horarios_disponiveis/',
            {'servico_id': self.servico.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        # horario_id = response.data[0]['id']

        # Buscar profissionais disponíveis
        response = self.client.get(
            '/api/agendamento-processo/buscar_profissionais_disponiveis/',
            {
                'horario_id': self.horario.id, # TESTESTESTE
                'servico_id': self.servico.id
            }
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) > 0)
        funcionario_id = response.data[0]['id']

        # Criar agendamento
        response = self.client.post(
            '/api/agendamento-processo/criar_agendamento/',
            {
                'servico_id': self.servico.id,
                'horario_id': self.horario.id,
                'funcionario_id': funcionario_id
            }
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

class SASBComplexTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        
        self.superuser = Cliente.objects.create_superuser(
            username='MrUser',
            password='MrUser.123',
            email='mruser@example.com',
            nome='Mr User',
            telefone='1234567890'
        )
        
        self.client.force_authenticate(user=self.superuser)
        self.criar_dados_complexos()

    def criar_dados_complexos(self):
        # Criar clientes
        self.clientes = []
        for i in range(5):
            cliente = Cliente.objects.create_user(
                username=f'cliente{i}',
                password='senha123',
                email=f'cliente{i}@teste.com',
                nome=f'Cliente Teste {i}',
                telefone=f'9999{i}9999',
                fidelidade_pontos=i * 10
            )
            self.clientes.append(cliente)

        # Criar funcionários com horários de trabalho mais amplos
        self.funcionarios = []
        cargos = ['Cabeleireiro', 'Manicure', 'Gerente', 'Esteticista', 'Massagista']
        for i, cargo in enumerate(cargos):
            funcionario = Funcionario.objects.create_user(
                username=f'func{i}',
                password='senha123',
                email=f'funcionario{i}@teste.com',
                nome=f'Funcionário {i}',
                telefone=f'8888{i}8888',
                cargo=cargo,
                horario_trabalho='08:00-20:00'  # Horário de trabalho mais amplo
            )
            self.funcionarios.append(funcionario)

        # Criar serviços
        self.servicos = []
        servicos_data = [
            ('Corte Simples', 30, '50.00'),
            ('Corte e Escova', 60, '80.00'),
            ('Manicure', 45, '35.00'),
            ('Pedicure', 45, '40.00'),
            ('Massagem', 60, '120.00')
        ]
        for nome, duracao, valor in servicos_data:
            servico = Servico.objects.create(
                nome=nome,
                duracao=duracao,
                valor=Decimal(valor)
            )
            self.servicos.append(servico)

        # Criar horários dentro do horário de trabalho
        self.horarios = []
        start_date = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=1)
        for i in range(7):  # próximos 7 dias
            for hour in range(9, 18):  # 9h às 18h
                horario = Horario.objects.create(
                    data=start_date + timedelta(days=i, hours=hour-9),
                    disponivel=True
                )
                self.horarios.append(horario)

    def test_1_agendamento_complexo(self):
        """Teste de criação de múltiplos agendamentos com validações"""
        horario = self.horarios[0]
        
        # Primeiro agendamento
        data = {
            'data': horario.data.isoformat(),
            'cliente': self.clientes[0].id,
            'servico': self.servicos[0].id,
            'horario': horario.id,
            'funcionario': self.funcionarios[0].id
        }
        response = self.client.post('/api/agendamentos/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Segundo agendamento (mesmo horário, deve falhar)
        data['cliente'] = self.clientes[1].id
        response = self.client.post('/api/agendamentos/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_2_filtros_complexos(self):
        """Teste de filtros complexos para agendamentos"""
        # Criar agendamentos em horários diferentes
        for i in range(5):
            horario = self.horarios[i]  # Usar horários diferentes
            Agendamento.objects.create(
                data=horario.data,
                cliente=self.clientes[i],
                servico=self.servicos[i],
                horario=horario,
                funcionario=self.funcionarios[i],
                status='AGENDADO'
            )

        # Testar filtros
        response = self.client.get('/api/agendamentos/', {
            'data': self.horarios[0].data.date().isoformat()
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response = self.client.get(f'/api/agendamentos/?cliente={self.clientes[0].id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_3_fluxo_completo_agendamento(self):
        """Teste do fluxo completo de agendamento, pagamento e cancelamento"""
        # 1. Criar agendamento
        agendamento_data = {
            'data': (timezone.now() + timedelta(days=1)).isoformat(),
            'cliente': self.clientes[0].id,
            'servico': self.servicos[0].id,
            'horario': self.horarios[0].id,
            'funcionario': self.funcionarios[0].id
        }
        response = self.client.post('/api/agendamentos/', agendamento_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        agendamento_id = response.data['id']

        # 2. Confirmar agendamento
        response = self.client.post(f'/api/agendamentos/{agendamento_id}/confirmar/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # 3. Criar dados de pagamento
        dados_pagamento_data = {
            'numero_cartao': '1234567890123456',
            'valor': '50.00',
            'metodo': 'CREDITO'
        }
        response = self.client.post('/api/dados-pagamento/', dados_pagamento_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        dados_pagamento_id = response.data['id']

        # 4. Criar pagamento
        pagamento_data = {
            'dados_pagamento': dados_pagamento_id,
            'status': 'PENDENTE'
        }
        response = self.client.post('/api/pagamentos/', pagamento_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 5. Verificar status do agendamento
        response = self.client.get(f'/api/agendamentos/{agendamento_id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'CONFIRMADO')

    def test_4_conflitos_horarios(self):
        """Teste de conflitos de horários entre agendamentos"""
        # Criar um agendamento inicial
        horario = self.horarios[0]
        primeiro_agendamento = {
            'data': horario.data.isoformat(),
            'cliente': self.clientes[0].id,
            'servico': self.servicos[0].id,
            'horario': horario.id,
            'funcionario': self.funcionarios[0].id
        }
        response = self.client.post('/api/agendamentos/', primeiro_agendamento, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Tentar criar outro agendamento no mesmo horário para o mesmo funcionário
        segundo_agendamento = {
            'data': horario.data.isoformat(),
            'cliente': self.clientes[1].id,
            'servico': self.servicos[1].id,
            'horario': horario.id,
            'funcionario': self.funcionarios[0].id
        }
        response = self.client.post('/api/agendamentos/', segundo_agendamento, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_5_estatisticas_servicos(self):
        """Teste de estatísticas de serviços mais populares"""
        # Criar agendamentos em horários diferentes
        for i in range(10):
            horario = self.horarios[i]  # Usar um horário diferente para cada agendamento
            servico = self.servicos[i % len(self.servicos)]
            cliente = self.clientes[i % len(self.clientes)]
            funcionario = self.funcionarios[i % len(self.funcionarios)]
            
            Agendamento.objects.create(
                data=horario.data,
                cliente=cliente,
                servico=servico,
                horario=horario,
                funcionario=funcionario,
                status='CONFIRMADO'
            )

        # Verificar contagem de agendamentos por serviço
        response = self.client.get('/api/servicos/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        servicos_count = {}
        for servico in self.servicos:
            count = Agendamento.objects.filter(servico=servico).count()
            servicos_count[servico.nome] = count
        
        # Verificar se o serviço mais popular tem mais agendamentos
        max_agendamentos = max(servicos_count.values())
        self.assertTrue(any(count == max_agendamentos for count in servicos_count.values()))
