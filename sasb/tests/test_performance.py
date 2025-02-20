from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
import time

class PerformanceTestCase(TestCase):
    def test_query_count(self):
        with CaptureQueriesContext(connection) as context:
            # Fazer alguma operação
            response = self.client.get('/api/agendamentos/')
            
            # Verificar número de queries
            self.assertLess(len(context), 10)

    def test_response_time(self):
        start_time = time.time()
        response = self.client.get('/api/servicos/')
        end_time = time.time()
        
        # Verificar se resposta é rápida o suficiente
        self.assertLess(end_time - start_time, 0.5)