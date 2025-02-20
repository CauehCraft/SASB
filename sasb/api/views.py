from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings    
from django.utils import timezone
from datetime import timedelta, datetime
from ..models import (
    Cliente,
    Funcionario,
    Servico,
    Horario,
    DadosPagamento,
    Pagamento,
    Agendamento
)
from .serializers import (
    ClienteSerializer,
    FuncionarioSerializer,
    ServicoSerializer,
    HorarioSerializer,
    DadosPagamentoSerializer,
    PagamentoSerializer,
    AgendamentoSerializer
)


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff


class ClienteViewSet(viewsets.ModelViewSet):
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()


class FuncionarioViewSet(viewsets.ModelViewSet):
    queryset = Funcionario.objects.all()
    serializer_class = FuncionarioSerializer
    permission_classes = [permissions.IsAdminUser]


class ServicoViewSet(viewsets.ModelViewSet):
    queryset = Servico.objects.all()
    serializer_class = ServicoSerializer
    permission_classes = [IsAdminOrReadOnly]

    @action(detail=True, methods=['get'])
    def horarios_disponiveis(self, request, pk=None):
        servico = self.get_object()
        horarios = servico.buscar_horarios_disponiveis()
        serializer = HorarioSerializer(horarios, many=True)
        return Response(serializer.data)


class HorarioViewSet(viewsets.ModelViewSet):
    queryset = Horario.objects.all()
    serializer_class = HorarioSerializer
    permission_classes = [IsAdminOrReadOnly]


class DadosPagamentoViewSet(viewsets.ModelViewSet):
    queryset = DadosPagamento.objects.all()
    serializer_class = DadosPagamentoSerializer
    permission_classes = [permissions.IsAuthenticated]


class PagamentoViewSet(viewsets.ModelViewSet):
    queryset = Pagamento.objects.all()
    serializer_class = PagamentoSerializer
    permission_classes = [permissions.IsAuthenticated]


class AgendamentoViewSet(viewsets.ModelViewSet):
    queryset = Agendamento.objects.all()
    serializer_class = AgendamentoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
                headers=headers
            )
        except ValidationError as e:
            return Response(
                {'error': e.message_dict},
                status=status.HTTP_400_BAD_REQUEST
            )

    def get_queryset(self):
        queryset = super().get_queryset()
        cliente_id = self.request.query_params.get('cliente', None)
        data = self.request.query_params.get('data', None)
        
        if cliente_id:
            queryset = queryset.filter(cliente_id=cliente_id)
        if data:
            queryset = queryset.filter(data__date=data)
        
        return queryset

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        agendamento = self.get_object()
        agendamento.cancelar_agendamento()
        return Response({'status': 'agendamento cancelado'})

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        agendamento = self.get_object()
        if agendamento.confirmar_agendamento():
            return Response({'status': 'agendamento confirmado'})
        return Response(
            {'error': 'não foi possível confirmar o agendamento'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
class AgendamentoProcessoViewSet(viewsets.ModelViewSet):
    queryset = Agendamento.objects.all()
    serializer_class = AgendamentoSerializer

    @action(detail=False, methods=['get'])
    def buscar_horarios_disponiveis(self, request):
        """
        Busca horários disponíveis para um serviço específico
        Parâmetros esperados na query:
        - servico_id: ID do serviço selecionado
        - data_inicio: Data inicial para busca (opcional)
        - data_fim: Data final para busca (opcional)
        """
        servico_id = request.query_params.get('servico_id')
        if not servico_id:
            return Response(
                {'error': 'É necessário informar o serviço'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Define período de busca (padrão: próximos 7 dias)
        data_inicio = request.query_params.get('data_inicio', timezone.now())
        if isinstance(data_inicio, str):
            data_inicio = timezone.make_aware(datetime.fromisoformat(data_inicio))
        data_fim = request.query_params.get(
            'data_fim',
            (timezone.now() + timedelta(days=7))
        )
        if isinstance(data_fim, str):
            data_fim = timezone.make_aware(datetime.fromisoformat(data_fim))

        horarios_disponiveis = Horario.objects.filter(
            data__range=[data_inicio, data_fim],
            disponivel=True
        ).order_by('data')

        serializer = HorarioSerializer(horarios_disponiveis, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def buscar_profissionais_disponiveis(self, request):
        """
        Busca profissionais disponíveis para um horário e serviço específicos
        Parâmetros esperados na query:
        - horario_id: ID do horário selecionado
        - servico_id: ID do serviço selecionado
        """
        horario_id = request.query_params.get('horario_id')
        servico_id = request.query_params.get('servico_id')

        if not horario_id or not servico_id:
            return Response(
                {'error': 'Horário e serviço são obrigatórios'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            horario = Horario.objects.get(id=horario_id)
            servico = Servico.objects.get(id=servico_id)

            # Busca funcionários que:
            # 1. Não têm agendamento no horário
            # 2. Trabalham no horário do agendamento
            hora = horario.data.hour
            funcionarios = Funcionario.objects.exclude(
                agendamento__horario=horario,
                agendamento__status__in=['AGENDADO', 'CONFIRMADO']
            ).filter(servicos=servico)

            serializer = FuncionarioSerializer(funcionarios, many=True)
            return Response(serializer.data)

        except (Horario.DoesNotExist, Servico.DoesNotExist):
            return Response(
                {'error': 'Horário ou serviço não encontrado'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['post'])
    def criar_agendamento(self, request):
        """
        Cria um agendamento com base nas seleções do cliente
        Dados esperados no body:
        - servico_id: ID do serviço
        - horario_id: ID do horário
        - funcionario_id: ID do funcionário
        """
        servico_id = request.data.get('servico_id')
        horario_id = request.data.get('horario_id')
        funcionario_id = request.data.get('funcionario_id')

        # Verificar disponibilidade final
        try:
            horario = Horario.objects.get(id=horario_id, disponivel=True)
            funcionario = Funcionario.objects.get(id=funcionario_id)
            servico = Servico.objects.get(id=servico_id)

            # Verificar se funcionário já tem agendamento neste horário
            agendamento_existente = Agendamento.objects.filter(
                horario=horario,
                funcionario=funcionario,
                status__in=['AGENDADO', 'CONFIRMADO']
            ).exists()

            if agendamento_existente:
                # Buscar horários alternativos
                horarios_alternativos = Horario.objects.filter(
                    data__gt=horario.data,
                    data__lt=horario.data + timedelta(days=2),
                    disponivel=True
                ).order_by('data')[:3]

                return Response({
                    'error': 'Horário ou profissional indisponível',
                    'horarios_alternativos': HorarioSerializer(horarios_alternativos, many=True).data
                }, status=status.HTTP_400_BAD_REQUEST)

            # Criar agendamento
            agendamento = Agendamento.objects.create(
                cliente=request.user,
                servico=servico,
                horario=horario,
                funcionario=funcionario,
                status='AGENDADO',
                data=horario.data
            )

            # Atualizar disponibilidade do horário
            horario.disponivel = False
            horario.save()

            # Adicionar pontos de fidelidade
            if isinstance(request.user, Cliente):
                request.user.fidelidade_pontos += 10
                request.user.save()

            # Enviar email de confirmação
            try:
                send_mail(
                    'Confirmação de Agendamento',
                    f'''Seu agendamento foi confirmado!
                    Serviço: {servico.nome}
                    Data: {horario.data}
                    Profissional: {funcionario.nome}
                    ''',
                    settings.DEFAULT_FROM_EMAIL,
                    [request.user.email],
                    fail_silently=True,
                )
            except Exception as e:
                # Log do erro de envio de email, mas não impede a criação do agendamento
                print(f"Erro ao enviar email: {e}")

            serializer = self.get_serializer(agendamento)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except (Horario.DoesNotExist, Funcionario.DoesNotExist, Servico.DoesNotExist):
            return Response(
                {'error': 'Dados inválidos para agendamento'},
                status=status.HTTP_400_BAD_REQUEST
            )