"""
tests/test_solver.py - Tests unitarios del motor PuLP
Patrón AAA (Arrange, Act, Assert)
"""

import pytest
from backend.models import ModeloPrimal, Restriccion, CoeficientesRestriccion
from backend.solver import PuLPSolver


class TestPuLPSolver:
    """Tests del solver de Programación Lineal"""

    def test_resolver_problema_simple_max(self):
        # Arrange
        primal = ModeloPrimal(
            tipo_optimizacion="max",
            funcion_objetivo={"x1": 3.0, "x2": 5.0},
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 2.0, "x2": 1.0}),
                    tipo="<=",
                    rhs=100
                ),
                Restriccion(
                    nombre="R2",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0, "x2": 3.0}),
                    tipo="<=",
                    rhs=150
                )
            ],
            nombre_variable_objetivo="Z"
        )

        # Act
        solver = PuLPSolver(tolerancia=0.0001, tiempo_maximo=30, precision=6)
        resultado = solver.resolver(primal, "test-request-id")

        # Assert
        assert resultado.estado == "OPTIMO"
        assert len(resultado.resultado_variables) == 2
        assert resultado.request_id == "test-request-id"
        assert resultado.tiempo_resolucion_ms > 0

    def test_resolver_problema_simple_min(self):
        # Arrange
        primal = ModeloPrimal(
            tipo_optimizacion="min",
            funcion_objetivo={"x1": 2.0, "x2": 3.0},
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0, "x2": 1.0}),
                    tipo=">=",
                    rhs=10
                )
            ],
            nombre_variable_objetivo="Z"
        )

        # Act
        solver = PuLPSolver()
        resultado = solver.resolver(primal, "test-min-id")

        # Assert
        assert resultado.estado == "OPTIMO"
        assert resultado.modelo_dual.tipo_optimizacion == "max"

    def test_extraer_holguras_y_precios_sombra(self):
        # Arrange
        primal = ModeloPrimal(
            tipo_optimizacion="max",
            funcion_objetivo={"x1": 1.0, "x2": 2.0},
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0, "x2": 0.0}),
                    tipo="<=",
                    rhs=10
                ),
                Restriccion(
                    nombre="R2",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 0.0, "x2": 1.0}),
                    tipo="<=",
                    rhs=8
                )
            ],
            nombre_variable_objetivo="Z"
        )

        # Act
        solver = PuLPSolver()
        resultado = solver.resolver(primal, "test-slack-id")

        # Assert
        assert len(resultado.resultado_restricciones) == 2
        for restr in resultado.resultado_restricciones:
            assert restr.holgura >= 0
            assert restr.precio_sombra is not None

    def test_generar_planteo_validacion(self):
        # Arrange
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
            ],
            nombre_variable_objetivo="Z"
        )

        # Act
        solver = PuLPSolver()
        resultado = solver.resolver(primal, "test-validate-id")

        # Assert
        planteo = resultado.modelo_primal_valido
        assert "MAX" in planteo.funcion_objetivo_texto or "max" in planteo.funcion_objetivo_texto.upper()
        assert len(planteo.restricciones_texto) == 1
        assert len(planteo.variables_texto) == 2