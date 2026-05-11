"""
dual_generator.py - Generador del Modelo Dual según Hillier & Lieberman
Implementa las reglas de dualidad: transposición de matriz A, intercambio de objetivo,
e inversión de operadores de restricciones.
"""

from backend.models import ModeloPrimal, RestriccionDual, ModeloDualExplícito, FuncionObjetivo
from typing import List, Dict


class DualGenerator:
    """
    Genera el modelo dual a partir del primal siguiendo las transformaciones
    descritas en Hillier & Lieberman, Capítulo 6 (Teoría de Dualidad).
    """

    @staticmethod
    def generar(nombres_variables: List[str], modelo_primal: ModeloPrimal) -> ModeloDualExplícito:
        """
        Genera el modelo dual explícito a partir del modelo primal.

        Transformaciones según Hillier & Lieberman:
        1. Si primal es max -> dual es min (y viceversa)
        2. Variables duales Y = (y1, y2, ..., ym) donde m = número de restricciones del primal
        3. Función objetivo dual: min W = b^T * y (RHS del primal como coeficientes)
        4. Matriz transpuesta: A^T (columnas del primal se vuelven filas del dual)
        5. Operadores invertidos: <= -> >=, >= -> <=, = permanece

        Args:
            nombres_variables: Lista de nombres de variables primal (x1, x2, ..., xn)
            modelo_primal: Modelo primal validado con estructura Pydantic

        Returns:
            ModeloDualExplícito con estructura transpuesta completa
        """
        tipo_dual = "min" if modelo_primal.tipo_optimizacion == "max" else "max"
        restricciones_duales = DualGenerator._construir_restricciones_duales(
            modelo_primal.restricciones, nombres_variables, modelo_primal.funcion_objetivo
        )
        funcion_objetivo_dual = DualGenerator._construir_funcion_objetivo_dual(
            modelo_primal.restricciones
        )
        interpretacion = DualGenerator._generar_interpretacion(
            modelo_primal.tipo_optimizacion, tipo_dual
        )

        return ModeloDualExplícito(
            tipo_optimizacion=tipo_dual,
            funcion_objetivo=funcion_objetivo_dual,
            variable_objetivo="W",
            restricciones=restricciones_duales,
            interpretacion=interpretacion
        )

    @staticmethod
    def _construir_funcion_objetivo_dual(restricciones: List) -> str:
        """
        Construye la función objetivo dual: min W = b1*y1 + b2*y2 + ... + bm*ym
        donde b_i son los RHS de las restricciones del primal.

        Args:
            restricciones: Lista de restricciones del primal (con atributos .rhs)

        Returns:
            String con la función objetivo dual formateada, ej: "Min W = 100y1 + 150y2"
        """
        terminos = []
        for i, restriccion in enumerate(restricciones, 1):
            coef = restriccion.rhs
            if abs(coef) > 0:
                if coef == int(coef):
                    terminos.append(f"{int(coef)}y{i}")
                else:
                    terminos.append(f"{coef}y{i}")

        tipo_str = "Min" if len(terminos) > 0 else "Min"
        return f"{tipo_str} W = {' + '.join(terminos)}"

    @staticmethod
    def _construir_restricciones_duales(restricciones: List, nombres_variables: List[str], funcion_objetivo: Dict[str, float]) -> List[RestriccionDual]:
        """
        Construye las restricciones duales mediante transposición de la matriz A.

        Para cada variable primal x_j, se crea una restricción dual Y_j:
        La fila j del dual contiene los coeficientes A_ij de la columna j del primal.
        El RHS de cada restricción dual es el coeficiente de xj en la función objetivo primal.

        Args:
            restricciones: Lista de restricciones con .coeficientes.variables
            nombres_variables: Lista de nombres de variables [x1, x2, ..., xn]
            funcion_objetivo: Diccionario de coeficientes de la FO primal

        Returns:
            Lista de RestriccionDual con coeficientes transpuestos y RHS correcto
        """
        restricciones_duales = []

        for idx, nombre_var in enumerate(nombres_variables):
            coefs_transpuestos: Dict[str, float] = {}

            for i, restriccion in enumerate(restricciones, 1):
                coef = restriccion.coeficientes.variables.get(nombre_var, 0.0)
                coefs_transpuestos[f"y{i}"] = coef

            rhs_dual = funcion_objetivo.get(nombre_var, 0.0)

            restricciones_duales.append(
                RestriccionDual(
                    nombre=f"Y{idx + 1}",
                    coeficientes=coefs_transpuestos,
                    tipo=">=",
                    rhs=rhs_dual
                )
            )

        return restricciones_duales

    @staticmethod
    def _invertir_operador(tipo_primal: str) -> str:
        """
        Invierte el operador de restricción según las reglas de dualidad.

        Args:
            tipo_primal: "<=", ">=", "="

        Returns:
            Operador invertido: "<=" -> ">=", ">=" -> "<=", "=" -> "="
        """
        if tipo_primal == "<=":
            return ">="
        elif tipo_primal == ">=":
            return "<="
        else:
            return "="

    @staticmethod
    def _generar_interpretacion(tipo_primal: str, tipo_dual: str) -> str:
        """
        Genera una descripción textual de la transposición para el usuario.

        Args:
            tipo_primal: "max" o "min"
            tipo_dual: "min" o "max"

        Returns:
            String con la interpretación matemática
        """
        return (
            f"Modelo Dual generado mediante transposición de matriz A (A^T). "
            f"Donde el primal era {tipo_primal.upper()}, el dual es {tipo_dual.upper()}. "
            f"Cada restricción dual Y_i representa la contribución marginal del recurso i "
            f"al valor de la función objetivo, interpretándose como el 'precio sombra' de dicho recurso."
        )