"""
validation.py - Validador de restricciones y modelo primal
Implementa validación matemática para detectar restricciones inválidas
según las reglas de Programación Lineal (Hillier & Lieberman).
"""

from backend.models import ModeloPrimal, Restriccion
from typing import List, Tuple, Optional, Dict


class ValidationError(Exception):
    """Excepción personalizada para errores de validación"""
    def __init__(self, mensaje: str, campo: Optional[str] = None):
        self.mensaje = mensaje
        self.campo = campo
        super().__init__(self.mensaje)


class ModeloValidator:
    """
    Validador de modelos de Programación Lineal.
    Detecta restricciones inválidas, redundantes o contradictorias.
    """

    @staticmethod
    def validar(modelo: ModeloPrimal) -> Tuple[bool, List[str]]:
        """
        Valida el modelo primal completo.

        Args:
            modelo: ModeloPrimal a validar

        Returns:
            Tupla (es_valido, lista_errores)
        """
        errores = []

        errores.extend(ModeloValidator._validar_coeficientes_objetivo(modelo.funcion_objetivo))
        errores.extend(ModeloValidator._validar_restricciones(modelo.restricciones))
        errores.extend(ModeloValidator._validar_contradicciones(modelo.restricciones))

        return (len(errores) == 0, errores)

    @staticmethod
    def _validar_coeficientes_objetivo(funcion_objetivo: dict) -> List[str]:
        """Valida que los coeficientes de la función objetivo sean válidos"""
        errores = []

        for var, coef in funcion_objetivo.items():
            if not isinstance(coef, (int, float)):
                errores.append(f"Coeficiente de '{var}' debe ser numérico")
            elif coef == 0:
                errores.append(f"Coeficiente de '{var}' no puede ser cero (variable inútil)")

        return errores

    @staticmethod
    def _validar_restricciones(restricciones: List[Restriccion]) -> List[str]:
        """Valida estructura y valores de restricciones"""
        errores = []

        for i, restr in enumerate(restricciones):
            if restr.rhs < 0 and restr.tipo == "<=":
                tiene_coef_positivos = any(c > 0 for c in restr.coeficientes.variables.values())
                if tiene_coef_positivos:
                    errores.append(
                        f"{restr.nombre}: RHS negativo ({restr.rhs}) con coeficientes positivos "
                        f"puede generar restricción infactible"
                    )

            for var, coef in restr.coeficientes.variables.items():
                if not isinstance(coef, (int, float)):
                    errores.append(f"{restr.nombre}: Coeficiente de '{var}' debe ser numérico")

        return errores

    @staticmethod
    def _validar_contradicciones(restricciones: List[Restriccion]) -> List[str]:
        """Detecta restricciones potencialmente contradictorias"""
        errores = []

        for i, r1 in enumerate(restricciones):
            for r2 in restricciones[i + 1:]:
                if r1.tipo == "<=" and r2.tipo == ">=":
                    coef_iguales = r1.coeficientes.variables == r2.coeficientes.variables
                    if coef_iguales and r1.rhs > r2.rhs:
                        errores.append(
                            f"Restricciones contradictorias: {r1.nombre} y {r2.nombre} "
                            f"con mismo coeficientes pero RHS incompatibles"
                        )

        return errores

    @staticmethod
    def generar_planteo_texto(modelo: ModeloPrimal) -> Tuple[str, List[str], List[str], Dict[str, str]]:
        """
        Genera representaciones textuales del planteo para validación del usuario.

        Args:
            modelo: ModeloPrimal validado

        Returns:
            Tupla (funcion_objetivo_texto, restricciones_texto, variables_texto, descripcion_variables)
        """
        tipo = modelo.tipo_optimizacion.upper()
        coef_str = " + ".join(
            f"{coef}* {var}" if coef != int(coef) else f"{int(coef)}*{var}"
            for var, coef in modelo.funcion_objetivo.items()
        )
        funcion_objetivo_texto = f"{tipo} {modelo.nombre_variable_objetivo} = {coef_str}"

        restricciones_texto = []
        for restr in modelo.restricciones:
            coef_str = " + ".join(
                f"{coef}*{var}" if coef != int(coef) else f"{int(coef)}*{var}"
                for var, coef in restr.coeficientes.variables.items()
                if coef != 0
            )
            restricciones_texto.append(f"{restr.nombre}: {coef_str} {restr.tipo} {restr.rhs}")

        variables = list(modelo.funcion_objetivo.keys())
        variables_texto = [f"{v} ≥ 0" for v in variables]

        descripcion_variables = getattr(modelo, 'descripcion_variables', {})
        if not descripcion_variables:
            descripcion_variables = {v: f"Cantidad de {v}" for v in variables}

        return funcion_objetivo_texto, restricciones_texto, variables_texto, descripcion_variables