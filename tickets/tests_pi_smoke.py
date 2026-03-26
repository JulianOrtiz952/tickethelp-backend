from django.urls import get_resolver
from django.urls.resolvers import URLPattern
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
from tickets.models import Ticket, Estado

class GlobalSystemEndpointsTests(APITestCase):
    """
    Test suite masivo (Smoke Test Suite) que recorre dinámicamente TODAS 
    las URLs del sistema para asegurar que ningún endpoint devuelve un Error 500 (Internal Server Error).
    """
    
    def setUp(self):
        # Aseguramos que existan usuarios para probar autenticado
        self.admin = User.objects.create_user(
            email='admin_global@test.com', password='Password123!', document='1000', role=User.Role.ADMIN, is_active=True
        )
        self.tech = User.objects.create_user(
            email='tech_global@test.com', password='Password123!', document='2000', role=User.Role.TECH, is_active=True
        )
        self.client_user = User.objects.create_user(
            email='client_global@test.com', password='Password123!', document='3000', role=User.Role.CLIENT, is_active=True
        )
        
        # Objetos mínimos para que las URLs con parámetros no fallen en la base de datos
        self.e_open, _ = Estado.objects.get_or_create(codigo='open', defaults={'nombre': 'Abierto'})
        self.ticket = Ticket.objects.create(
            cliente=self.client_user,
            administrador=self.admin,
            tecnico=self.tech,
            estado=self.e_open,
            titulo="Ticket de Smoke Test",
            descripcion="Descripción test global"
        )
        
    def get_all_urls(self):
        """Obtiene todas las rutas (URLs) registradas en el proyecto Django"""
        urlconf = get_resolver()
        all_urls = []

        def retrieve_urls(patterns, prefix=''):
            for p in patterns:
                if isinstance(p, URLPattern):
                    url = prefix + str(p.pattern)
                    # Excluir rutas de admin o media que no nos interesan
                    if not url.startswith('admin') and not url.startswith('media'):
                        all_urls.append(url)
                else: # Es un URLResolver (como include('tickets.urls'))
                    retrieve_urls(p.url_patterns, prefix + str(p.pattern))

        retrieve_urls(urlconf.url_patterns)
        return all_urls

    def process_url(self, url):
        """Limpia los parámetros regex de las URLs de Django para inyectar IDs reales"""
        # Reemplazar todos los parámetros esperados por datos reales (el Ticket o Usuario)
        url = url.replace('^', '/').replace('$', '')
        
        # Inyectar IDs comunes si la URL los pide
        if '<int:ticket_id>' in url:
            url = url.replace('<int:ticket_id>', str(self.ticket.pk))
        if '<int:pk>' in url:
            url = url.replace('<int:pk>', str(self.ticket.pk))
        if '<str:pk>' in url:
            # Los usuarios manejan string en pk (el document)
            url = url.replace('<str:pk>', str(self.admin.document))
        if '<str:document>' in url:
            url = url.replace('<str:document>', str(self.client_user.document))
        if '<str:year>' in url:
            url = url.replace('<str:year>', '2026')
        if '<str:month>' in url:
            url = url.replace('<str:month>', '03')
        if '<str:correo>' in url:
            url = url.replace('<str:correo>', self.tech.email)
            
        return url

    def test_all_endpoints_sanity_check(self):
        """
        Recorre todos los endpoints, hace un GET (autenticado como admin) y se asegura
        de que la app no colapse (Status code no debe ser 500).
        """
        urls = self.get_all_urls()
        
        # Autenticamos como el admin global (el que tiene más permisos)
        self.client.force_authenticate(user=self.admin)
        
        for raw_url in urls:
            processed_url = self.process_url(raw_url)
            
            # Limpiar dobles slashes y probar
            processed_url = processed_url.replace('//', '/')
            
            try:
                response = self.client.get(processed_url, HTTP_ACCEPT='application/json')
                error_msg = f"El endpoint {processed_url} colapsó con un Error 500."
                self.assertNotEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)
            except AttributeError as e:
                # Bypass Django test.client.py vs Python 3.14 incompatibility
                if "dicts" not in str(e):
                    self.fail(f"El endpoint {processed_url} falló: {str(e)}")
            except Exception as e:
                self.fail(f"El endpoint {processed_url} generó un error de Python no controlado: {str(e)}")
