from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from .api.views import (
    ClienteViewSet,
    FuncionarioViewSet,
    ServicoViewSet,
    HorarioViewSet,
    DadosPagamentoViewSet,
    PagamentoViewSet,
    AgendamentoViewSet,
    AgendamentoProcessoViewSet
)

schema_view = get_schema_view(
    openapi.Info(
        title="Salão de Beleza API",
        default_version='v1',
        description="API para sistema de salão de beleza",
    ),
    public=True,
)


router = DefaultRouter()
router.register(r'clientes', ClienteViewSet)
router.register(r'funcionarios', FuncionarioViewSet)
router.register(r'servicos', ServicoViewSet)
router.register(r'horarios', HorarioViewSet)
router.register(r'dados-pagamento', DadosPagamentoViewSet)
router.register(r'pagamentos', PagamentoViewSet)
router.register(r'agendamentos', AgendamentoViewSet)
router.register(r'agendamento-processo', AgendamentoProcessoViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0)),
]