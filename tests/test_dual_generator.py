"""
tests/test_dual_generator.py - Tests del generador de modelo dual
Patrón AAA (Arrange, Act, Assert)
Verifica la transposición matricial correcta según Hillier & Lieberman
"""

import pytest
from backend.models import ModeloPrimal, Restriccion, CoeficientesRestriccion
from backend.dual_generator import DualGenerator


class TestDualGenerator:
    """Tests del generador de modelo dual"""

    def test_generar_dual_max_to_min(self):
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
        nombres_vars = ["x1", "x2"]

        # Act
        dual = DualGenerator.generar(nombres_vars, primal)

        # Assert
        assert dual.tipo_optimizacion == "min"
        assert dual.variable_objetivo == "W"
        assert "100" in dual.funcion_objetivo
        assert "150" in dual.funcion_objetivo

    def test_generar_dual_min_to_max(self):
        # Arrange
        primal = ModeloPrimal(
            tipo_optimizacion="min",
            funcion_objetivo={"x1": 100.0, "x2": 150.0},
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 2.0, "x2": 1.0}),
                    tipo=">=",
                    rhs=3
                )
            ],
            nombre_variable_objetivo="Z"
        )
        nombres_vars = ["x1", "x2"]

        # Act
        dual = DualGenerator.generar(nombres_vars, primal)

        # Assert
        assert dual.tipo_optimizacion == "max"

    def test_transposicion_matriz_coeficientes(self):
        # Arrange
        # Primal:
        # R1: 2x1 + 1x2 <= 100
        # R2: 1x1 + 3x2 <= 150
        # Matriz A = [[2, 1], [1, 3]]
        # A^T debe dar restricciones Y1, Y2 con coeficientes de columnas
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
        nombres_vars = ["x1", "x2"]

        # Act
        dual = DualGenerator.generar(nombres_vars, primal)

        # Assert - Y1 debe tener coeficientes de x1 en todas las restricciones (columna 1 de A)
        y1_coefs = dual.restricciones[0].coeficientes
        assert y1_coefs["y1"] == 2.0  # A[0,0] = 2
        assert y1_coefs["y2"] == 1.0  # A[1,0] = 1

        # Y2 debe tener coeficientes de x2 en todas las restricciones (columna 2 de A)
        y2_coefs = dual.restricciones[1].coeficientes
        assert y2_coefs["y1"] == 1.0  # A[0,1] = 1
        assert y2_coefs["y2"] == 3.0  # A[1,1] = 3

    def test_inversion_operadores(self):
        # Arrange
        primal = ModeloPrimal(
            tipo_optimizacion="max",
            funcion_objetivo={"x1": 1.0},
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0}),
                    tipo="<=",
                    rhs=10
                ),
                Restriccion(
                    nombre="R2",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0}),
                    tipo=">=",
                    rhs=5
                )
            ],
            nombre_variable_objetivo="Z"
        )
        nombres_vars = ["x1"]

        # Act
        dual = DualGenerator.generar(nombres_vars, primal)

        # Assert
        assert dual.restricciones[0].tipo == ">="  # <= invertido
        assert dual.restricciones[1].tipo == "<="  # >= invertido

    def test_funcion_objetivo_dual_rhs_como_coeficientes(self):
        # Arrange
        # min W = b1*y1 + b2*y2 donde b = RHS del primal
        primal = ModeloPrimal(
            tipo_optimizacion="max",
            funcion_objetivo={"x1": 3.0},
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0}),
                    tipo="<=",
                    rhs=100
                ),
                Restriccion(
                    nombre="R2",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0}),
                    tipo="<=",
                    rhs=150
                )
            ],
            nombre_variable_objetivo="Z"
        )
        nombres_vars = ["x1"]

        # Act
        dual = DualGenerator.generar(nombres_vars, primal)

        # Assert
        assert "100" in dual.funcion_objetivo
        assert "150" in dual.funcion_objetivo

    def test_interpretacion_dual_generada(self):
        # Arrange
        primal = ModeloPrimal(
            tipo_optimizacion="max",
            funcion_objetivo={"x1": 1.0},
            restricciones=[
                Restriccion(
                    nombre="R1",
                    coeficientes=CoeficientesRestriccion(variables={"x1": 1.0}),
                    tipo="<=",
                    rhs=10
                )
            ],
            nombre_variable_objetivo="Z"
        )
        nombres_vars = ["x1"]

        # Act
        dual = DualGenerator.generar(nombres_vars, primal)

        # Assert
        assert len(dual.interpretacion) > 0
        assert "transposición" in dual.interpretacion.lower() or "A^T" in dual.interpretacion