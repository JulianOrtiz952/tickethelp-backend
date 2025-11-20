from django.test import TestCase


from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
from tickets.models import Ticket, Estado, TicketHistory, StateChangeRequest

class TicketHistoryTests(APITestCase):
    def setUp(self):
        # crear usuarios
        self.admin = User.objects.create_user(
            email='admin@test.com',
            password='Admin123!',
            document='100',
            role=User.Role.ADMIN,
            is_active=True
        )
        self.tech1 = User.objects.create_user(
            email='tech1@test.com',
            password='Tech123!',
            document='200',
            role=User.Role.TECH,
            is_active=True,
            first_name='Técnico',
            last_name='Uno'
        )
        self.tech2 = User.objects.create_user(
            email='tech2@test.com',
            password='Tech123!',
            document='201',
            role=User.Role.TECH,
            is_active=True,
            first_name='Técnico',
            last_name='Dos'
        )
        self.client_user = User.objects.create_user(
            email='client@test.com',
            password='Client123!',
            document='300',
            role=User.Role.CLIENT,
            is_active=True,
            first_name='Cliente',
            last_name='Test'
        )

        # crear estados
        self.estado_open = Estado.objects.create(
            codigo='open',
            nombre='Abierto',
            es_activo=True,
            es_final=False
        )
        self.estado_diag = Estado.objects.create(
            codigo='diagnosis',
            nombre='En diagnóstico',
            es_activo=True,
            es_final=False
        )
        self.estado_repair = Estado.objects.create(
            codigo='in_repair',
            nombre='En reparación',
            es_activo=True,
            es_final=False
        )
        self.estado_trial = Estado.objects.create(
            codigo='trial',
            nombre='En prueba',
            es_activo=True,
            es_final=False
        )
        self.estado_trial_pending = Estado.objects.create(
            codigo='trial_pending_approval',
            nombre='En pruebas pendiente de aprobación',
            es_activo=True,
            es_final=False
        )
        self.estado_fin = Estado.objects.create(
            codigo='closed',
            nombre='Finalizado',
            es_activo=False,
            es_final=True
        )

        # autenticar como admin para las requests
        self.client.force_authenticate(self.admin)

    # =============================================================================
    # ESCENARIO 3: Crear ticket debe guardar en historial con técnico y todos los datos
    # =============================================================================
    def test_01_crear_ticket_crea_historial_con_tecnico_y_datos(self):
        """Escenario 3: Al crear un ticket, se guarda en historial con técnico y todos los datos"""
        url = reverse('ticket-list')
        data = {
            "administrador": self.admin.document,
            "tecnico": self.tech1.document,
            "cliente": self.client_user.document,
            "estado": self.estado_diag.id,
            "titulo": "PC no enciende",
            "descripcion": "La PC no enciende desde ayer",
            "equipo": "Lenovo ThinkPad"
        }
        resp = self.client.post(url, data, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        ticket_id = resp.data['id']
        
        # Verificar que existe el historial
        history = TicketHistory.objects.filter(ticket_id=ticket_id, accion__icontains='Creación')
        self.assertTrue(history.exists(), "Debe existir una entrada en el historial para la creación")
        
        history_entry = history.first()
        # Verificar que tiene el técnico asignado
        self.assertEqual(history_entry.tecnico, self.tech1, "El historial debe tener el técnico asignado")
        
        # Verificar que tiene todos los datos del ticket
        self.assertIsNotNone(history_entry.datos_ticket, "Debe tener datos del ticket guardados")
        datos = history_entry.datos_ticket
        self.assertEqual(datos.get('titulo'), "PC no enciende", "Debe guardar el título")
        self.assertEqual(datos.get('descripcion'), "La PC no enciende desde ayer", "Debe guardar la descripción")
        self.assertEqual(datos.get('equipo'), "Lenovo ThinkPad", "Debe guardar el equipo")
        self.assertEqual(datos.get('tecnico'), self.tech1.document, "Debe guardar el documento del técnico")
        self.assertEqual(datos.get('administrador'), self.admin.document, "Debe guardar el documento del administrador")
        self.assertEqual(datos.get('cliente'), self.client_user.document, "Debe guardar el documento del cliente")
        
        # Verificar quién realizó la acción
        self.assertEqual(history_entry.realizado_por, self.admin, "El historial debe registrar quién creó el ticket")

    # =============================================================================
    # ESCENARIO 2: Cambiar técnico debe guardar en historial con estado actual
    # =============================================================================
    def test_02_cambiar_tecnico_registra_historial_con_estado(self):
        """Escenario 2: Al cambiar técnico, se guarda en historial el técnico cambiado con el estado actual"""
        # primero creamos el ticket
        ticket = Ticket.objects.create(
            administrador=self.admin,
            tecnico=self.tech1,
            cliente=self.client_user,
            estado=self.estado_diag,
            titulo="Ticket prueba",
            descripcion="Descripción del ticket",
            equipo="Equipo de prueba"
        )

        url = reverse('change-technician', args=[ticket.pk])
        
        # Realizar el cambio de técnico
        resp = self.client.put(
            f"{url}?user_document={self.admin.document}",
            {"documento_tecnico": self.tech2.document}, 
            format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Verificar que existe el historial del cambio
        history = TicketHistory.objects.filter(
            ticket=ticket, 
            accion__icontains='técnico'
        ).order_by('-fecha')
        
        self.assertTrue(history.exists(), "Debe existir una entrada en el historial para el cambio de técnico")
        
        history_entry = history.first()
        # Verificar que guarda el técnico anterior y el nuevo
        self.assertEqual(history_entry.tecnico_anterior, self.tech1, "Debe guardar el técnico anterior")
        self.assertEqual(history_entry.tecnico, self.tech2, "Debe guardar el técnico nuevo")
        
        # Verificar que guarda el estado actual del ticket
        self.assertEqual(history_entry.estado, self.estado_diag.nombre, "Debe guardar el estado actual del ticket")
        self.assertEqual(history_entry.estado_anterior, self.estado_diag.nombre, "El estado anterior debe ser el mismo si no cambió")
        
        # Verificar quién realizó el cambio
        self.assertEqual(history_entry.realizado_por, self.admin, "Debe registrar quién hizo el cambio")

    # =============================================================================
    # ESCENARIO 1: Consultar historial por ticket ID muestra historial con técnico relacionado
    # =============================================================================
    def test_03_listar_historial_por_ticket_muestra_tecnicos(self):
        """Escenario 1: Consultar historial por ID muestra historial con técnico relacionado en cada estado"""
        # crear ticket
        ticket = Ticket.objects.create(
            administrador=self.admin,
            tecnico=self.tech1,
            cliente=self.client_user,
            estado=self.estado_diag,
            titulo="Ticket prueba 2",
            descripcion="Descripción",
            equipo="Equipo"
        )
        
        # Crear entrada inicial en historial (simulando creación)
        TicketHistory.objects.create(
            ticket=ticket,
            estado='Diagnóstico',
            tecnico=self.tech1,
            accion='Creación del ticket',
            realizado_por=self.admin
        )
        
        # Cambiar técnico y crear entrada en historial
        ticket.tecnico = self.tech2
        ticket.save()
        TicketHistory.objects.create(
            ticket=ticket,
            estado='Diagnóstico',
            estado_anterior='Diagnóstico',
            tecnico=self.tech2,
            tecnico_anterior=self.tech1,
            accion='Cambio de técnico de Técnico Uno a Técnico Dos',
            realizado_por=self.admin
        )

        # Consultar historial
        url = reverse('ticket-history-detail', args=[ticket.pk])
        resp = self.client.get(f"{url}?user_document={self.admin.document}")
        
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('historial', resp.data, "La respuesta debe incluir el campo 'historial'")
        
        historial = resp.data['historial']
        self.assertGreaterEqual(len(historial), 2, "Debe tener al menos 2 entradas en el historial")
        
        # Verificar que cada entrada tiene el técnico relacionado
        for entrada in historial:
            self.assertIn('tecnico', entrada, "Cada entrada debe tener el campo 'tecnico'")
            self.assertIn('tecnico_nombre', entrada, "Cada entrada debe tener el nombre del técnico")
            self.assertIn('estado', entrada, "Cada entrada debe tener el estado")
            self.assertIn('accion', entrada, "Cada entrada debe tener la acción realizada")
            self.assertIn('realizado_por_nombre', entrada, "Cada entrada debe tener quién realizó la acción")
            self.assertIn('fecha', entrada, "Cada entrada debe tener la fecha")
        
        # Verificar la primera entrada (cambio de técnico)
        primera_entrada = historial[0]  # Ordenado por fecha descendente
        self.assertEqual(primera_entrada['tecnico_documento'], self.tech2.document, "La primera entrada debe tener el técnico actual")
        self.assertIn('técnico', primera_entrada['accion'].lower(), "La acción debe mencionar el cambio de técnico")

    # =============================================================================
    # ESCENARIO 4: No permitir cambios después de finalizar ticket
    # =============================================================================
    def test_04_ticket_finalizado_no_permite_cambios(self):
        """Escenario 4: Al finalizar un ticket, no se permiten más cambios en el historial"""
        # Crear ticket y finalizarlo directamente cambiando el estado
        ticket = Ticket.objects.create(
            administrador=self.admin,
            tecnico=self.tech1,
            cliente=self.client_user,
            estado=self.estado_diag,
            titulo="Ticket para finalizar",
            descripcion="Descripción",
            equipo="Equipo"
        )
        
        # Finalizar el ticket cambiando directamente el estado
        ticket.estado = self.estado_fin
        ticket.save()
        
        # Registrar en historial la finalización
        TicketHistory.crear_entrada_historial(
            ticket=ticket,
            accion=f"Cambio de estado a '{self.estado_fin.nombre}'",
            realizado_por=self.admin,
            estado_anterior=self.estado_diag.nombre
        )
        
        # Verificar que el ticket está finalizado
        ticket.refresh_from_db()
        self.assertEqual(ticket.estado, self.estado_fin, "El ticket debe estar en estado finalizado")
        
        # Verificar que existe entrada en historial para la finalización
        history_finalizado = TicketHistory.objects.filter(
            ticket=ticket,
            accion__icontains='finalizado'
        )
        self.assertTrue(history_finalizado.exists(), "Debe existir entrada en historial para la finalización")
        
        # Intentar cambiar el técnico (debe fallar)
        url_change = reverse('change-technician', args=[ticket.pk])
        resp_change = self.client.put(
            f"{url_change}?user_document={self.admin.document}",
            {"documento_tecnico": self.tech2.document},
            format='json'
        )
        
        self.assertEqual(resp_change.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('finalizado', resp_change.data.get('error', '').lower() or '', 
                     "Debe rechazar el cambio porque el ticket está finalizado")
        
        # Verificar que NO se creó nueva entrada en historial
        history_count_before = TicketHistory.objects.filter(ticket=ticket).count()
        
        # Intentar cambiar estado (debe fallar)
        self.client.force_authenticate(self.tech1)
        url_state = reverse('change-state', args=[ticket.pk])
        resp_state = self.client.put(
            f"{url_state}?user_document={self.tech1.document}",
            {"to_state": self.estado_diag.id},
            format='json'
        )
        
        self.assertEqual(resp_state.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('finalizado', resp_state.data.get('error', '').lower() or '',
                     "Debe rechazar el cambio de estado porque el ticket está finalizado")
        
        # Verificar que NO se creó nueva entrada en historial después de los intentos
        history_count_after = TicketHistory.objects.filter(ticket=ticket).count()
        self.assertEqual(history_count_before, history_count_after, 
                        "No debe crear nuevas entradas en historial después de finalizar")

    # =============================================================================
    # Test: Verificar que todos los estados se reflejen en el historial, especialmente "En prueba"
    # =============================================================================
    def test_05_cambio_a_estado_pruebas_se_refleja_en_historial(self):
        """Verificar que al cambiar el estado a 'En prueba' (trial), se refleje correctamente en el historial"""
        # Crear ticket inicialmente en estado "En reparación"
        ticket = Ticket.objects.create(
            administrador=self.admin,
            tecnico=self.tech1,
            cliente=self.client_user,
            estado=self.estado_repair,
            titulo="Ticket para prueba de estados",
            descripcion="Verificar que todos los estados se reflejen en el historial",
            equipo="Equipo de prueba"
        )
        
        # Crear entrada inicial en el historial (simulando la creación del ticket)
        TicketHistory.crear_entrada_historial(
            ticket=ticket,
            accion="Creación del ticket",
            realizado_por=self.admin,
            estado_anterior=None
        )
        
        # Autenticar como técnico para poder cambiar estados
        self.client.force_authenticate(self.tech1)
        
        # Contar las entradas iniciales en el historial (debe tener la creación)
        history_count_inicial = TicketHistory.objects.filter(ticket=ticket).count()
        self.assertGreaterEqual(history_count_inicial, 1, "Debe tener al menos la entrada de creación")
        
        # Cambiar estado a "En prueba" (trial)
        url_change_state = reverse('change-state', args=[ticket.pk])
        resp_trial = self.client.put(
            f"{url_change_state}?user_document={self.tech1.document}",
            {"to_state": self.estado_trial.id},
            format='json'
        )
        
        self.assertEqual(resp_trial.status_code, status.HTTP_200_OK, 
                        "Debe permitir cambiar el estado a 'En prueba'")
        
        # Verificar que el ticket está en estado "En prueba"
        ticket.refresh_from_db()
        self.assertEqual(ticket.estado, self.estado_trial, 
                        "El ticket debe estar en estado 'En prueba'")
        
        # Verificar que se agregó una entrada en el historial para el cambio a "En prueba"
        history_after_trial = TicketHistory.objects.filter(ticket=ticket).order_by('-fecha')
        history_count_after_trial = history_after_trial.count()
        self.assertGreater(history_count_after_trial, history_count_inicial,
                          "Debe haber una nueva entrada en el historial después de cambiar a 'En prueba'")
        
        # Buscar la entrada específica del cambio a "En prueba"
        history_trial = history_after_trial.filter(
            accion__icontains='En prueba',
            estado__icontains='En prueba'
        )
        self.assertTrue(history_trial.exists(), 
                       "Debe existir una entrada en el historial que mencione 'En prueba'")
        
        history_entry_trial = history_trial.first()
        # Verificar que la entrada tiene la información correcta
        self.assertIn('En reparación', history_entry_trial.accion,
                     "La acción debe mencionar el estado anterior 'En reparación'")
        self.assertIn('En prueba', history_entry_trial.accion,
                     "La acción debe mencionar el nuevo estado 'En prueba'")
        self.assertEqual(history_entry_trial.estado, self.estado_trial.nombre,
                        "El estado en el historial debe ser 'En prueba'")
        self.assertEqual(history_entry_trial.realizado_por, self.tech1,
                        "Debe registrar que el técnico realizó el cambio")
        
        # Cambiar a otro estado para verificar que se siguen registrando cambios
        # Cambiar a "En pruebas pendiente de aprobación"
        resp_pending = self.client.put(
            f"{url_change_state}?user_document={self.tech1.document}",
            {"to_state": self.estado_trial_pending.id},
            format='json'
        )
        
        self.assertEqual(resp_pending.status_code, status.HTTP_200_OK,
                        "Debe permitir cambiar de 'En prueba' a 'En pruebas pendiente de aprobación'")
        
        # Verificar que el ticket está en el nuevo estado
        ticket.refresh_from_db()
        self.assertEqual(ticket.estado, self.estado_trial_pending,
                        "El ticket debe estar en estado 'En pruebas pendiente de aprobación'")
        
        # Verificar que se agregó otra entrada en el historial
        history_after_pending = TicketHistory.objects.filter(ticket=ticket).order_by('-fecha')
        history_count_after_pending = history_after_pending.count()
        self.assertGreater(history_count_after_pending, history_count_after_trial,
                          "Debe haber otra nueva entrada en el historial")
        
        # Buscar la entrada específica del cambio a "En pruebas pendiente de aprobación"
        history_pending = history_after_pending.filter(
            accion__icontains='En pruebas pendiente'
        )
        self.assertTrue(history_pending.exists(),
                       "Debe existir una entrada en el historial que mencione 'En pruebas pendiente de aprobación'")
        
        history_entry_pending = history_pending.first()
        self.assertIn('En prueba', history_entry_pending.accion,
                     "La acción debe mencionar el estado anterior 'En prueba'")
        self.assertIn('En pruebas pendiente', history_entry_pending.accion,
                     "La acción debe mencionar el nuevo estado")
        
        # Verificar que todos los estados del ticket están reflejados en el historial
        # Consultar el historial completo del ticket
        self.client.force_authenticate(self.admin)
        url_history = reverse('ticket-history-detail', args=[ticket.pk])
        resp_history = self.client.get(f"{url_history}?user_document={self.admin.document}")
        
        self.assertEqual(resp_history.status_code, status.HTTP_200_OK,
                        "Debe poder consultar el historial del ticket")
        
        historial_completo = resp_history.data.get('historial', [])
        self.assertGreaterEqual(len(historial_completo), 3,
                               "El historial debe tener al menos 3 entradas (creación, cambio a prueba, cambio a pendiente)")
        
        # Verificar que aparecen todos los estados por los que pasó el ticket
        estados_en_historial = [entrada['estado'] for entrada in historial_completo]
        
        # Verificar que está el estado "En reparación" (estado inicial)
        self.assertIn(self.estado_repair.nombre, estados_en_historial,
                     "El historial debe reflejar el estado inicial 'En reparación'")
        
        # Verificar que está el estado "En prueba"
        self.assertIn(self.estado_trial.nombre, estados_en_historial,
                     "El historial DEBE reflejar el estado 'En prueba' cuando se cambió a ese estado")
        
        # Verificar que está el estado "En pruebas pendiente de aprobación"
        self.assertIn(self.estado_trial_pending.nombre, estados_en_historial,
                     "El historial debe reflejar el estado 'En pruebas pendiente de aprobación'")
        
        # Verificar que todas las entradas del historial tienen la información necesaria
        for entrada in historial_completo:
            self.assertIn('estado', entrada, "Cada entrada debe tener el campo 'estado'")
            self.assertIn('accion', entrada, "Cada entrada debe tener el campo 'accion'")
            self.assertIn('fecha', entrada, "Cada entrada debe tener el campo 'fecha'")
            self.assertIn('realizado_por_nombre', entrada, 
                         "Cada entrada debe tener el campo 'realizado_por_nombre'")
            self.assertIn('tecnico_nombre', entrada,
                         "Cada entrada debe tener el campo 'tecnico_nombre'")
        
        # Verificar específicamente que la entrada de "En prueba" tiene todos los datos
        entrada_trial_en_respuesta = next(
            (e for e in historial_completo if self.estado_trial.nombre in e.get('estado', '')),
            None
        )
        self.assertIsNotNone(entrada_trial_en_respuesta,
                           "Debe existir una entrada en la respuesta del historial con el estado 'En prueba'")
        self.assertIn('En prueba', entrada_trial_en_respuesta.get('accion', ''),
                     "La acción de la entrada debe mencionar 'En prueba'")

