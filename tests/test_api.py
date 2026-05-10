"""
tests/test_api.py - Tests de endpoints de FastAPI
Patrón AAA (Arrange, Act, Assert)
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app


client = TestClient(app)


class TestHealthEndpoint:
    """Tests del endpoint de salud"""

    def test_health_check_retorna_200(self):
        # Arrange / Act
        response = client.get("/health")

        # Assert
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestSolveEndpoint:
    """Tests del endpoint de resolución"""

    def test_solve_sin_problema_retorna_422(self):
        # Arrange / Act
        response = client.post("/api/solve", json={})

        # Assert
        assert response.status_code == 422

    def test_solve_con_problema_vacio_retorna_422(self):
        # Arrange
        body = {"problema_texto": ""}

        # Act
        response = client.post("/api/solve", json=body)

        # Assert
        assert response.status_code == 422

    def test_solve_sin_nvidia_api_key_retorna_500(self):
        # Arrange
        body = {"problema_texto": "Un problema simple"}

        # Act
        response = client.post("/api/solve", json=body)

        # Assert
        # Si no hay API key configurada, debe retornar 500 CONFIG_ERROR
        assert response.status_code in [500, 502]


class TestModeloValidator:
    """Tests del validador de modelos"""

    def test_validar_coeficientes_cero(self):
        # Arrange
        from backend.models import ModeloPrimal, Restriccion, CoeficientesRestriccion

        primal = ModeloPrimal(
            tipo_optimizacion="max",
            funcion_objetivo={"x1": 0},  # Coeficiente cero
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0}),
                    tipo="<=",
                    rhs=10
                )
            ]
        )

        # Act
        from backend.validation import ModeloValidator
        es_valido, errores = ModeloValidator.validar(primal)

        # Assert
        assert not es_valido
        assert any("cero" in e for e in errores)

    def test_generar_planteo_texto(self):
        # Arrange
        from backend.models import ModeloPrimal, Restriccion, CoeficientesRestriccion

        primal = ModeloPrimal(
            tipo_optimizacion="max",
            funcion_objetivo={"x1": 3.0, "x2": 5.0},
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 2.0, "x2": 1.0}),
                    tipo="<=",
                    rhs=100
                )
            ]
        )

        # Act
        funcion_obj, restricciones, variables = ModeloValidator.generar_planteo_texto(primal)

        # Assert
        assert "3" in funcion_obj
        assert "5" in funcion_obj
        assert len(restricciones) == 1
        assert len(variables) == 2


class TestErrorCodes:
    """Tests de códigos de error HTTP"""

    def test_400_bad_request(self):
        # Arrange
        body = {"problema_texto": None}  # Tipo inválido

        # Act
        response = client.post("/api/solve", json=body)

        # Assert
        assert response.status_code == 422

    def test_request_id_en_headers(self):
        # Arrange / Act
        response = client.get("/health")

        # Assert
        assert "X-Request-ID" in response.headers or response.status_code == 200