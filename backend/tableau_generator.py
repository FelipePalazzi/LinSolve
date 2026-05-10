"""
tableau_generator.py - Generador de Tableaux Simplex (Inicial y Óptimo)
Reconstruye el tableau completo a partir del modelo y solución PuLP.

El tableau tiene formato:
| ck | xk | bk | x1 | x2 | ... | xn | s1 | s2 | ... | sm | Zj-Cj |
|----|----|----|----|----|-----|----|----|----|----|----|-------|
| c1 | xB1| b1 | a11| a12| ... | a1n| 1  | 0  | ... | 0  | z1-c1 |
| c2 | xB2| b2 | a21| a22| ... | a2n| 0  | 1  | ... | 0  | z2-c2 |
...
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
from pulp import LpProblem
from backend.models import ModeloPrimal


class TableauGenerator:
    """
    Genera tableaux simplex (inicial y óptimo) reconstruyendo la matriz
    y calculando B⁻¹ a partir de la información disponible en PuLP.
    """

    def __init__(self, precision: int = 6):
        self.precision = precision

    def generar_tableau_inicial(self, modelo: ModeloPrimal) -> Dict:
        """
        Genera el tableau de la iteración 0 (tabla inicial).
        En iteración 0, la base es la identidad (variables de holgura).
        """
        num_vars = len(modelo.funcion_objetivo)
        num_restricciones = len(modelo.restricciones)

        nombres_vars = list(modelo.funcion_objetivo.keys())
        nombres_slack = [f"S{i+1}" for i in range(num_restricciones)]

        ck_originales = [modelo.funcion_objetivo.get(v, 0.0) for v in nombres_vars]
        ck_slack = [0.0] * num_restricciones
        ck = ck_originales + ck_slack

        matriz = []
        for i, restr in enumerate(modelo.restricciones):
            fila = []
            for var in nombres_vars:
                coef = restr.coeficientes.variables.get(var, 0.0)
                fila.append(coef)
            for j in range(num_restricciones):
                fila.append(1.0 if j == i else 0.0)
            matriz.append(fila)

        fila_z = []
        for var in nombres_vars:
            coef = modelo.funcion_objetivo.get(var, 0.0)
            if modelo.tipo_optimizacion == "max":
                fila_z.append(-coef)
            else:
                fila_z.append(coef)
        for _ in range(num_restricciones):
            fila_z.append(0.0)

        rhs = [restr.rhs for restr in modelo.restricciones]
        vars_basicas = nombres_slack.copy()

        return self._construir_response(
            iteracion=0,
            nombres_vars=nombres_vars,
            nombres_slack=nombres_slack,
            matriz=matriz,
            rhs=rhs,
            fila_z=fila_z,
            ck=ck,
            variables_basicas=vars_basicas,
            nombre_objetivo=modelo.nombre_variable_objetivo,
            tipo_optimizacion=modelo.tipo_optimizacion
        )

    def generar_tableau_optimo(
        self,
        modelo: ModeloPrimal,
        problema: LpProblem
    ) -> Dict:
        """
        Genera el tableau óptimo reconstruido desde la solución de PuLP.
        """
        num_vars = len(modelo.funcion_objetivo)
        num_restricciones = len(modelo.restricciones)

        nombres_vars = list(modelo.funcion_objetivo.keys())
        nombres_slack = [f"S{i+1}" for i in range(num_restricciones)]
        todos_nombres = nombres_vars + nombres_slack

        A = self._construir_matriz_A(modelo, nombres_vars)
        I = np.eye(num_restricciones)
        A_completa = np.hstack([A, I])

        basicas, no_basicas = self._identificar_base(problema, todos_nombres)

        indices_basicas = [todos_nombres.index(v) for v in basicas]

        B = A_completa[:, indices_basicas]

        try:
            B_inv = np.linalg.inv(B)
        except np.linalg.LinAlgError:
            return self._generar_fallback(modelo, nombres_vars, nombres_slack)

        b = np.array([r.rhs for r in modelo.restricciones])

        bk = B_inv @ b

        tableau_optimal = B_inv @ A_completa

        rhs_final = bk.tolist()
        matriz_final = tableau_optimal.tolist()

        ck_originales = [modelo.funcion_objetivo.get(v, 0.0) for v in nombres_vars]
        ck_slack = [0.0] * num_restricciones
        todos_ck = ck_originales + ck_slack

        ck_por_fila = [todos_ck[todos_nombres.index(var)] for var in basicas]

        fila_z = self._calcular_zj_cj(matriz_final, ck_por_fila, modelo.tipo_optimizacion, todos_ck)

        return self._construir_response(
            iteracion=-1,
            nombres_vars=nombres_vars,
            nombres_slack=nombres_slack,
            matriz=matriz_final,
            rhs=rhs_final,
            fila_z=fila_z,
            ck=ck_por_fila,
            variables_basicas=basicas,
            nombre_objetivo=modelo.nombre_variable_objetivo,
            tipo_optimizacion=modelo.tipo_optimizacion
        )

    def _identificar_base(self, problema: LpProblem, todos_nombres: List[str]) -> Tuple[List[str], List[str]]:
        """
        Identifica variables básicas y no básicas basándose en:
        - Variables con valor > 0 y dj ≈ 0 son básicas
        - Variables con dj ≠ 0 son no básicas (valor = 0)
        """
        var_dict = problema.variablesDict()

        basicas = []
        no_basicas = []

        for nombre in todos_nombres:
            if nombre in var_dict:
                var = var_dict[nombre]
                valor = getattr(var, 'varValue', 0) or 0
                dj = getattr(var, 'dj', 0) or 0

                if abs(valor) > 1e-9 and abs(dj) < 1e-6:
                    basicas.append(nombre)
                else:
                    no_basicas.append(nombre)
            else:
                no_basicas.append(nombre)

        num_restricciones = len([r for r in getattr(problema, 'constraints', {}).values()])

        if len(basicas) < num_restricciones:
            for nombre in todos_nombres:
                if nombre.startswith('S') and nombre not in basicas:
                    basicas.append(nombre)
                    if len(basicas) >= num_restricciones:
                        break

        basicas = basicas[:num_restricciones]

        return basicas, no_basicas

    def _construir_matriz_A(self, modelo: ModeloPrimal, nombres_vars: List[str]) -> np.ndarray:
        """Construye la matriz de coeficientes tecnológicos A"""
        num_restricciones = len(modelo.restricciones)
        num_vars = len(nombres_vars)
        A = np.zeros((num_restricciones, num_vars))

        for i, restr in enumerate(modelo.restricciones):
            for j, var in enumerate(nombres_vars):
                A[i, j] = restr.coeficientes.variables.get(var, 0.0)

        return A

    def _calcular_zj_cj(
        self,
        matriz: List[List[float]],
        ck_fila: List[float],
        tipo_optimizacion: str,
        ck_todos: List[float]
    ) -> List[float]:
        """
        Calcula Zj - Cj para cada columna.
        Zj = sum(ck_fila[i] * a[i][j]) para i = 0..m-1
        Zj - Cj = Zj - Cj_columna para max
        Cj - Zj para min
        """
        if not matriz:
            return []

        num_filas = len(matriz)
        num_columnas = len(matriz[0]) if matriz[0] else len(ck_todos)

        fila_z = []
        for j in range(num_columnas):
            zj = sum(ck_fila[i] * matriz[i][j] for i in range(num_filas))
            cj = ck_todos[j] if j < len(ck_todos) else 0.0

            if tipo_optimizacion == "max":
                zj_cj = zj - cj
            else:
                zj_cj = cj - zj

            fila_z.append(round(zj_cj, self.precision))

        return fila_z

    def _generar_fallback(
        self,
        modelo: ModeloPrimal,
        nombres_vars: List[str],
        nombres_slack: List[str]
    ) -> Dict:
        """Fallback usando el tableau inicial si no se puede calcular B⁻¹"""
        return self.generar_tableau_inicial(modelo)

    def _construir_response(
        self,
        iteracion: int,
        nombres_vars: List[str],
        nombres_slack: List[str],
        matriz: List[List[float]],
        rhs: List[float],
        fila_z: List[float],
        ck: List[float],
        variables_basicas: List[str],
        nombre_objetivo: str,
        tipo_optimizacion: str
    ) -> Dict:
        """Construye el dictionary de respuesta del tableau"""
        return {
            "iteracion": iteracion,
            "nombre_objetivo": nombre_objetivo,
            "tipo_optimizacion": tipo_optimizacion,
            "nombres_columnas": nombres_vars + nombres_slack,
            "nombres_vars_originales": nombres_vars,
            "nombres_slack": nombres_slack,
            "ck": [round(c, self.precision) for c in ck],
            "variables_basicas": variables_basicas,
            "rhs": [round(r, self.precision) for r in rhs],
            "fila_z": fila_z,
            "matriz": [[round(v, self.precision) for v in fila] for fila in matriz],
            "num_filas": len(matriz),
            "num_columnas": len(matriz[0]) if matriz else len(nombres_vars) + len(nombres_slack)
        }


def generar_tableau_inicial(modelo: ModeloPrimal) -> Dict:
    """Función de conveniencia para generar tableau inicial"""
    generator = TableauGenerator()
    return generator.generar_tableau_inicial(modelo)


def generar_tableau_optimo(modelo: ModeloPrimal, problema: LpProblem) -> Dict:
    """Función de conveniencia para generar tableau óptimo"""
    generator = TableauGenerator()
    return generator.generar_tableau_optimo(modelo, problema)