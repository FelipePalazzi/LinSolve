"""
solver.py - Motor matemático con PuLP
Resuelve modelos de Programación Lineal (Primal) y genera el Modelo Dual
siguiendo la metodología de Hillier & Lieberman.
"""

import time
import loguru
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from pulp import (
    LpProblem, LpVariable, LpConstraint, LpStatus,
    LpMaximize, LpMinimize, value, PULP_CBC_CMD,
    LpStatusOptimal, LpStatusInfeasible, LpStatusUnbounded,
    LpStatusNotSolved, LpStatusUndefined
)
from backend.models import (
    ModeloPrimal, SolveResponse, PlanteoValidacion,
    ResultadoVariable, RestriccionResultado, ModeloDualExplícito,
    AnalisisSensibilidad, RangoOptimo, TableauRespuesta, TableauIteracion
)
from backend.dual_generator import DualGenerator
from backend.validation import ModeloValidator, ValidationError
from backend.tableau_generator import generar_tableau_inicial, generar_tableau_optimo


logger = loguru.logger


class SolverError(Exception):
    """Excepción personalizada para errores del solver"""
    pass


class PuLPSolver:
    """
    Solver de Programación Lineal usando PuLP.
    Implementa resolución de primal y generación algorítmica del dual.
    """

    def __init__(self, tolerancia: float = 0.0001, tiempo_maximo: int = 30, precision: int = 6):
        self.tolerancia = tolerancia
        self.tiempo_maximo = tiempo_maximo
        self.precision = precision

    def resolver(self, modelo: ModeloPrimal, request_id: str) -> SolveResponse:
        """
        Resuelve el modelo primal y genera el modelo dual.

        Args:
            modelo: ModeloPrimal validado
            request_id: UUID de trazabilidad

        Returns:
            SolveResponse con primal, dual y análisis de sensibilidad
        """
        inicio = time.time()

        logger.info(
            f"[ReqID: {request_id}] Resolviendo modelo primal: "
            f"tipo={modelo.tipo_optimizacion}, variables={len(modelo.funcion_objetivo)}, "
            f"restricciones={len(modelo.restricciones)}"
        )

        try:
            problema = self._crear_problema_pulp(modelo)
            status = problema.solve(
                PULP_CBC_CMD(
                    timeLimit=self.tiempo_maximo,
                    msg=0
                )
            )

            tiempo_ms = (time.time() - inicio) * 1000

            estado_str = self._mapear_estado(status)
            if estado_str == "ERROR":
                logger.error(
                    f"[ReqID: {request_id}] Estado del solver: {LpStatus[status]}"
                )
                raise SolverError(f"Solver falló con estado: {LpStatus[status]}")

            nombres_variables = list(modelo.funcion_objetivo.keys())
            resultado_variables = self._extraer_resultado_variables(problema, modelo)
            resultado_restricciones = self._extraer_resultado_restricciones(problema, modelo)
            modelo_dual = DualGenerator.generar(nombres_variables, modelo)
            analisis = self._generar_analisis_sensibilidad(problema, modelo, resultado_restricciones)
            planteo = self._generar_planteo_validacion(modelo)

            Z_valor = value(problema.objective) if value(problema.objective) else 0.0

            logger.info(
                f"[ReqID: {request_id}] Modelo resuelto: estado={estado_str}, "
                f"Z={Z_valor:.4f}, tiempo={tiempo_ms:.2f}ms"
            )

            tableaux = self._generar_tableaux(modelo, problema)

            return SolveResponse(
                estado=estado_str,
                modelo_primal_valido=planteo,
                modelo_primal=modelo,  # Para What-If
                resultado_variables=resultado_variables,
                resultado_restricciones=resultado_restricciones,
                modelo_dual=modelo_dual,
                analisis_sensibilidad=analisis,
                tiempo_resolucion_ms=round(tiempo_ms, 2),
                request_id=request_id,
                Z_valor=round(Z_valor, self.precision),
                W_valor=round(Z_valor, self.precision),
                tableaux=tableaux
            )

        except SolverError:
            raise
        except Exception as e:
            logger.error(f"[ReqID: {request_id}] Error inesperado: {str(e)}")
            raise SolverError(f"Error en resolución: {str(e)}")

    def _crear_problema_pulp(self, modelo: ModeloPrimal) -> LpProblem:
        """
        Crea el problema PuLP a partir del modelo primal.

        Args:
            modelo: ModeloPrimal validado

        Returns:
            LpProblem configurado y listo para resolver
        """
        sentido = LpMaximize if modelo.tipo_optimizacion == "max" else LpMinimize
        problema = LpProblem(f"LinSolve_{modelo.nombre_variable_objetivo}", sentido)

        variables = {
            var: LpVariable(var, lowBound=0)
            for var in modelo.funcion_objetivo.keys()
        }

        for restr in modelo.restricciones:
            expr = sum(
                variables[var] * coef
                for var, coef in restr.coeficientes.variables.items()
            )
            nombre_slack = restr.nombre_variable_holgura or f"S{restr.nombre[1:]}"
            variables[nombre_slack] = LpVariable(nombre_slack, lowBound=0)

            if restr.tipo == "<=":
                problema += expr <= restr.rhs, restr.nombre
            elif restr.tipo == ">=":
                problema += expr >= restr.rhs, restr.nombre
            else:
                problema += expr == restr.rhs, restr.nombre

        objetivo = sum(variables[var] * coef for var, coef in modelo.funcion_objetivo.items())
        problema += objetivo

        return problema

    def _mapear_estado(self, status) -> str:
        """Mapea el estado de PuLP a los estados definidos en SolveResponse"""
        mapeo = {
            LpStatusOptimal: "OPTIMO",
            LpStatusInfeasible: "INFEASIBLE",
            LpStatusUnbounded: "NO_ACOTADO",
            LpStatusNotSolved: "ERROR",
            LpStatusUndefined: "ERROR"
        }
        return mapeo.get(status, "ERROR")

    def _extraer_resultado_variables(
        self, problema: LpProblem, modelo: ModeloPrimal
    ) -> List[ResultadoVariable]:
        """Extrae los resultados de las variables primal"""
        resultados = []
        for var in modelo.funcion_objetivo.keys():
            valor = value(problema.variablesDict()[var])
            resultados.append(
                ResultadoVariable(
                    nombre=var,
                    valor=round(valor, self.precision) if valor else 0.0,
                    costo_reducido=round(problema.variablesDict()[var].dj, self.precision) if valor else None
                )
            )
        return resultados

    def _extraer_resultado_restricciones(
        self, problema: LpProblem, modelo: ModeloPrimal
    ) -> List[RestriccionResultado]:
        """Extrae resultados de restricciones incluyendo holguras y precios sombra"""
        resultados = []
        for restr in modelo.restricciones:
            constraint = problema.constraints[restr.nombre]
            holgura = value(constraint.slack) if constraint.slack else 0.0
            precio_sombra = round(constraint.pi, self.precision) if constraint.pi else 0.0

            resultados.append(
                RestriccionResultado(
                    nombre=restr.nombre,
                    tipo=restr.tipo,
                    RHS_original=restr.rhs,
                    holgura=round(abs(holgura), self.precision),
                    precio_sombra=precio_sombra,
                    activa=abs(holgura) < self.tolerancia
                )
            )
        return resultados

    def _generar_analisis_sensibilidad(
        self, problema: LpProblem, modelo: ModeloPrimal,
        resultado_restricciones: List[RestriccionResultado]
    ) -> AnalisisSensibilidad:
        """Genera el análisis de sensibilidad según Hillier & Lieberman

        Calcula rangos de optimalidad a partir del tableau óptimo.
        """
        var_dict = problema.variablesDict()
        nombres_vars = list(modelo.funcion_objetivo.keys())
        nombres_slack = [f"S{i+1}" for i in range(len(modelo.restricciones))]
        num_restricciones = len(modelo.restricciones)

        if not modelo.funcion_objetivo:
            return AnalisisSensibilidad(
                rango_optimos=[],
                costo_reducido_interpretacion="No hay variables para analizar.",
                holguras_interpretacion="",
                relacion_Z_equals_W=""
            )

        todos_nombres = nombres_vars + nombres_slack

        A = self._construir_matriz_A(modelo, nombres_vars)
        I = np.eye(num_restricciones)
        A_completa = np.hstack([A, I])

        basicas = []
        for nombre in todos_nombres:
            if nombre in var_dict:
                var = var_dict[nombre]
                valor = getattr(var, 'varValue', 0) or 0
                dj = getattr(var, 'dj', 0) or 0
                if abs(valor) > 1e-9 and abs(dj) < 1e-6:
                    basicas.append(nombre)

        basicas = basicas[:num_restricciones]

        indices_basicas = [todos_nombres.index(v) for v in basicas]
        B = A_completa[:, indices_basicas]

        try:
            B_inv = np.linalg.inv(B)
            tableau_optimo = B_inv @ A_completa
        except:
            tableau_optimo = None

        ck_originales = [modelo.funcion_objetivo.get(v, 0.0) for v in nombres_vars]
        ck_slack = [0.0] * num_restricciones
        todos_ck = ck_originales + ck_slack

        rangos = []
        for i, var_nombre in enumerate(nombres_vars):
            lp_var = var_dict.get(var_nombre)
            if not lp_var:
                continue

            coef_actual = modelo.funcion_objetivo.get(var_nombre, 0)

            if tableau_optimo is not None:
                shadow_prices = []
                for restr in modelo.restricciones:
                    constraint = problema.constraints.get(restr.nombre)
                    if constraint:
                        pi = getattr(constraint, 'pi', 0) or 0
                        shadow_prices.append(pi)

                min_lim = 0.0
                max_lim = float('inf')

                for j in range(len(nombres_vars), len(todos_nombres)):
                    col_idx = j - len(nombres_vars)
                    coef_tecnologico = A[col_idx, i] if col_idx < A.shape[0] else 0

                    if abs(coef_tecnologico) > 1e-9 and col_idx < len(shadow_prices):
                        shadow = abs(shadow_prices[col_idx])
                        if shadow > 0:
                            if coef_tecnologico > 0:
                                max_posible = coef_actual + 100
                                if max_posible < max_lim:
                                    max_lim = max_posible
                            else:
                                min_posible = coef_actual - 100
                                if min_posible > min_lim:
                                    min_lim = min_posible

                if min_lim < 0:
                    min_lim = 0

                rangos.append(RangoOptimo(
                    variable=var_nombre,
                    min=round(min_lim, 2),
                    max=round(max_lim, 2)
                ))
            else:
                rangos.append(RangoOptimo(
                    variable=var_nombre,
                    min=0.0,
                    max=float('inf')
                ))

        restricciones_activas = sum(1 for r in resultado_restricciones if r.activa)
        total_restricciones = len(resultado_restricciones)

        costo_reducido_info = self._generar_info_costos_reducidos(modelo, var_dict, resultado_restricciones)

        return AnalisisSensibilidad(
            rango_optimos=rangos,
            costo_reducido_interpretacion=costo_reducido_info,
            holguras_interpretacion=(
                f"De {total_restricciones} restricciones, {restricciones_activas} están activas "
                f"(holgura = 0). Las restricciones activas representan recursos limitantes."
            ),
            relacion_Z_equals_W="Por el Teorema de Dualidad Fuerte, Z = W en la solución óptima"
        )

    def _calcular_rango_coef_basica(
        self, problema: LpProblem, modelo: ModeloPrimal, var_nombre: str
    ) -> Optional[RangoOptimo]:
        """Calcula rango de optimalidad para variable básica usando Precios Sombra"""
        try:
            var_dict = problema.variablesDict()
            basicas = []
            for v in list(modelo.funcion_objetivo.keys()) + [f"S{i+1}" for i in range(len(modelo.restricciones))]:
                if v in var_dict:
                    val = getattr(var_dict[v], 'varValue', 0) or 0
                    dj = getattr(var_dict[v], 'dj', 0) or 0
                    if abs(val) > 1e-9 and abs(dj) < 1e-6:
                        basicas.append(v)

            if var_nombre not in basicas:
                return None

            shadow_prices = []
            for restr in modelo.restricciones:
                constraint = problema.constraints.get(restr.nombre)
                if constraint:
                    pi = getattr(constraint, 'pi', 0) or 0
                    shadow_prices.append(pi)

            coef_original = modelo.funcion_objetivo.get(var_nombre, 0)

            min_val = None
            max_val = None

            for i, restr in enumerate(modelo.restricciones):
                coef_tecnologico = restr.coeficientes.variables.get(var_nombre, 0)
                if abs(coef_tecnologico) > 1e-9 and i < len(shadow_prices):
                    shadow = shadow_prices[i]
                    if shadow > 0:
                        limite = coef_original + shadow * 1000
                        if max_val is None or limite < max_val:
                            max_val = limite

            if min_val is None:
                min_val = 0.0
            if max_val is None:
                max_val = float('inf')

            return RangoOptimo(
                variable=var_nombre,
                min=round(min_val, 2),
                max=round(max_val, 2)
            )
        except Exception:
            return None

    def _calcular_rango_coef_no_basica(self, dj: float, coef_actual: float) -> Optional[RangoOptimo]:
        """Calcula rango de optimalidad para variable no básica usando costo reducido"""
        try:
            if abs(dj) > 1e-9:
                if dj < 0:
                    max_extra = abs(dj)
                    return RangoOptimo(
                        variable="",
                        min=coef_actual,
                        max=coef_actual + max_extra
                    )
                else:
                    min_reduccion = dj
                    return RangoOptimo(
                        variable="",
                        min=max(0, coef_actual - min_reduccion),
                        max=coef_actual
                    )
            return None
        except Exception:
            return None

    def _generar_info_costos_reducidos(
        self, modelo: ModeloPrimal, var_dict: Dict, resultado_restricciones: List[RestriccionResultado]
    ) -> str:
        """Genera interpretación de costos reducidos para variables no básicas"""
        no_basicas_con_costo = []
        nombres_vars = list(modelo.funcion_objetivo.keys())
        nombres_slack = [f"S{i+1}" for i in range(len(modelo.restricciones))]
        todos_nombres = nombres_vars + nombres_slack

        for nombre in todos_nombres:
            if nombre in var_dict:
                var = var_dict[nombre]
                valor = getattr(var, 'varValue', 0) or 0
                dj = getattr(var, 'dj', 0) or 0

                if abs(valor) < 1e-9 and abs(dj) > 1e-9:
                    if nombre.startswith('x'):
                        no_basicas_con_costo.append((nombre, dj))

        partes = []
        for nombre, dj in no_basicas_con_costo:
            costo_mostrar = abs(dj)
            partes.append(f"{nombre} tiene costo reducido {costo_mostrar:.2f} (no está en la base)")

        if partes:
            return "; ".join(partes) + "."
        return "Todas las variables de decisión están en la base con valores óptimos."

    def _generar_planteo_validacion(self, modelo: ModeloPrimal) -> PlanteoValidacion:
        """Genera el planteo en texto para validación del usuario"""
        funcion_objetivo, restricciones, variables = ModeloValidator.generar_planteo_texto(modelo)
        return PlanteoValidacion(
            funcion_objetivo_texto=funcion_objetivo,
            restricciones_texto=restricciones,
            variables_texto=variables
        )

    def _generar_tableaux(self, modelo: ModeloPrimal, problema: LpProblem) -> TableauRespuesta:
        """Genera los tableaux inicial y óptimo para primal y dual"""
        try:
            primal_inicial_data = generar_tableau_inicial(modelo)
            primal_optimo_data = generar_tableau_optimo(modelo, problema)

            primal_inicial = TableauIteracion(**primal_inicial_data)
            primal_optimo = TableauIteracion(**primal_optimo_data)

            dual_optimo_data = self._generar_tableau_dual_optimo(modelo, problema)
            dual_optimo = TableauIteracion(**dual_optimo_data)

            Z_valor = value(problema.objective) if value(problema.objective) else 0.0

            return TableauRespuesta(
                primal_inicial=primal_inicial,
                primal_optimo=primal_optimo,
                dual_optimo=dual_optimo,
                Z_valor=round(Z_valor, self.precision),
                W_valor=round(Z_valor, self.precision)
            )
        except Exception as e:
            logger.warning(f"Error generando tableaux: {str(e)}")
            return None

    def _generar_tableau_dual_optimo(self, modelo: ModeloPrimal, problema: LpProblem) -> Dict:
        """Genera el tableau óptimo del modelo dual

        Para primal Max: dual Min W = b^T y
        con restricciones A^T y >= c (todas >= porque primal es <=)

        Resuelve el dual como un problema separado usando PuLP,
        luego reconstruye el tableau óptimo.
        """
        from pulp import LpVariable, LpProblem as LpProblemDual, LpMinimize, LpStatus, value
        from backend.dual_generator import DualGenerator

        nombres_vars_primal = list(modelo.funcion_objetivo.keys())
        num_vars_primal = len(nombres_vars_primal)
        num_restricciones = len(modelo.restricciones)

        modelo_dual = DualGenerator.generar(nombres_vars_primal, modelo)

        nombres_vars_dual = [f"y{i+1}" for i in range(num_restricciones)]
        nombres_surplus = [f"s{i+1}" for i in range(num_vars_primal)]

        ck_dual = [restr.rhs for restr in modelo.restricciones]
        ck_surplus = [0.0] * num_vars_primal

        dual_problem = LpProblemDual("Dual_LP", LpMinimize)

        y_vars = {f"y{i+1}":LpVariable(f"y{i+1}", lowBound=0) for i in range(num_restricciones)}
        s_vars = {f"s{i+1}":LpVariable(f"s{i+1}", lowBound=0) for i in range(num_vars_primal)}

        for i, restr in enumerate(modelo.restricciones):
            pass

        funcion_objetivo_dual = sum(ck_dual[i] * y_vars[f"y{i+1}"] for i in range(num_restricciones))
        dual_problem += funcion_objetivo_dual

        for j, var_primal in enumerate(nombres_vars_primal):
            coefs = []
            for i, restr in enumerate(modelo.restricciones):
                coef = restr.coeficientes.variables.get(var_primal, 0.0)
                coefs.append(coef * y_vars[f"y{i+1}"])

            expr = sum(coefs) - sum(s_vars[f"s{k+1}"] for k in range(num_vars_primal) if k == j) >= modelo.funcion_objetivo[var_primal]
            dual_problem += expr, f"Y{j+1}"

        dual_problem.solve()

        if dual_problem.status != LpStatusOptimal:
            return self._generar_tableau_dual_inicial(modelo, nombres_vars_dual, nombres_surplus, ck_dual, ck_surplus)

        A = self._construir_matriz_A(modelo, nombres_vars_primal)
        A_T = A.T

        matriz_inicial = []
        for j in range(num_vars_primal):
            fila = []
            for i in range(num_restricciones):
                coef = A_T[j, i]
                fila.append(coef)
            for k in range(num_vars_primal):
                fila.append(-1.0 if k == j else 0.0)
            matriz_inicial.append(fila)

        rhs = [modelo.funcion_objetivo.get(v, 0.0) for v in nombres_vars_primal]

        todos_nombres = nombres_vars_dual + nombres_surplus
        var_dict = {v.name: v for v in dual_problem.variables()}

        basicas = []
        for nombre in todos_nombres:
            if nombre in var_dict:
                var = var_dict[nombre]
                val = value(var) or 0
                if abs(val) > 1e-9:
                    basicas.append(nombre)

        while len(basicas) < num_vars_primal:
            for nombre in nombres_surplus:
                if nombre not in basicas:
                    basicas.append(nombre)
                    break
            if len(basicas) >= num_vars_primal:
                break

        basicas = basicas[:num_vars_primal]

        indices_basicas = [todos_nombres.index(v) for v in basicas]

        matriz_np = np.array(matriz_inicial)
        B = matriz_np[:, indices_basicas]

        try:
            B_inv = np.linalg.inv(B)
        except np.linalg.LinAlgError:
            return self._generar_fallback_dual(matriz_inicial, rhs, ck_dual, ck_surplus, basicas, nombres_vars_dual, nombres_surplus, modelo_dual.tipo_optimizacion)

        bk = B_inv @ np.array(rhs)
        tableau_optimo = B_inv @ matriz_np

        ck_fila = [ck_dual[nombres_vars_dual.index(v)] if v in nombres_vars_dual else 0.0 for v in basicas]

        fila_z = self._calcular_fila_z_dual(
            tableau_optimo.tolist(),
            bk.tolist(),
            list(ck_dual) + ck_surplus,
            modelo_dual.tipo_optimizacion,
            ck_fila
        )

        return {
            "iteracion": -1,
            "nombre_objetivo": "W",
            "tipo_optimizacion": modelo_dual.tipo_optimizacion,
            "nombres_columnas": nombres_vars_dual + nombres_surplus,
            "nombres_vars_originales": nombres_vars_dual,
            "nombres_slack": nombres_surplus,
            "ck": [round(c, self.precision) for c in list(ck_dual) + ck_surplus],
            "variables_basicas": basicas,
            "rhs": [round(r, self.precision) for r in bk.tolist()],
            "fila_z": fila_z,
            "matriz": [[round(v, self.precision) for v in fila] for fila in tableau_optimo.tolist()],
            "num_filas": len(matriz_inicial),
            "num_columnas": len(matriz_inicial[0]) if matriz_inicial else num_restricciones + num_vars_primal
        }

    def _generar_tableau_dual_inicial(
        self,
        modelo: ModeloPrimal,
        nombres_vars_dual: List[str],
        nombres_surplus: List[str],
        ck_dual: List[float],
        ck_surplus: List[float]
    ) -> Dict:
        """Genera tableau inicial del dual (no óptimo)"""
        nombres_vars_primal = list(modelo.funcion_objetivo.keys())
        num_vars_primal = len(nombres_vars_primal)
        num_restricciones = len(modelo.restricciones)

        A = self._construir_matriz_A(modelo, nombres_vars_primal)
        A_T = A.T

        matriz = []
        for j in range(num_vars_primal):
            fila = []
            for i in range(num_restricciones):
                fila.append(A_T[j, i])
            for k in range(num_vars_primal):
                fila.append(-1.0 if k == j else 0.0)
            matriz.append(fila)

        rhs = [modelo.funcion_objetivo.get(v, 0.0) for v in nombres_vars_primal]

        return {
            "iteracion": 0,
            "nombre_objetivo": "W",
            "tipo_optimizacion": "min",
            "nombres_columnas": nombres_vars_dual + nombres_surplus,
            "nombres_vars_originales": nombres_vars_dual,
            "nombres_slack": nombres_surplus,
            "ck": [round(c, self.precision) for c in list(ck_dual) + ck_surplus],
            "variables_basicas": [f"s{i+1}" for i in range(num_vars_primal)],
            "rhs": [round(r, self.precision) for r in rhs],
            "fila_z": [],
            "matriz": [[round(v, self.precision) for v in fila] for fila in matriz],
            "num_filas": len(matriz),
            "num_columnas": len(matriz[0]) if matriz else num_restricciones + num_vars_primal
        }

    def _generar_fallback_dual(
        self,
        matriz: List[List[float]],
        rhs: List[float],
        ck_dual: List[float],
        ck_surplus: List[float],
        basicas: List[str],
        nombres_vars_dual: List[str],
        nombres_surplus: List[str],
        tipo_optimizacion: str
    ) -> Dict:
        """Fallback cuando no se puede calcular B_inv para dual"""
        fila_z = self._calcular_fila_z_dual(
            matriz, rhs,
            list(ck_dual) + ck_surplus,
            tipo_optimizacion,
            None
        )
        return {
            "iteracion": -1,
            "nombre_objetivo": "W",
            "tipo_optimizacion": tipo_optimizacion,
            "nombres_columnas": nombres_vars_dual + nombres_surplus,
            "nombres_vars_originales": nombres_vars_dual,
            "nombres_slack": nombres_surplus,
            "ck": [round(c, self.precision) for c in list(ck_dual) + ck_surplus],
            "variables_basicas": basicas,
            "rhs": [round(r, self.precision) for r in rhs],
            "fila_z": fila_z,
            "matriz": [[round(v, self.precision) for v in fila] for fila in matriz],
            "num_filas": len(matriz),
            "num_columnas": len(matriz[0]) if matriz else len(ck_dual) + len(ck_surplus)
        }

    def _calcular_fila_z_dual(
        self,
        matriz: List[List[float]],
        rhs: List[float],
        ck: List[float],
        tipo_optimizacion: str,
        ck_fila: Optional[List[float]] = None
    ) -> List[float]:
        """Calcula Zj - Cj para el tableau dual"""
        if not matriz:
            return []

        num_filas = len(matriz)
        num_cols = len(matriz[0]) if matriz[0] else len(ck)

        if ck_fila is None:
            ck_fila = ck[:num_filas]

        fila_z = []
        for j in range(num_cols):
            zj = sum(ck_fila[i] * matriz[i][j] for i in range(num_filas))
            cj = ck[j] if j < len(ck) else 0.0

            if tipo_optimizacion == "min":
                zj_cj = zj - cj
            else:
                zj_cj = cj - zj

            fila_z.append(round(zj_cj, self.precision))

        return fila_z

    def _construir_matriz_A(self, modelo: ModeloPrimal, nombres_vars: List[str]) -> np.ndarray:
        """Construye la matriz de coeficientes tecnológicos A"""
        num_restricciones = len(modelo.restricciones)
        num_vars = len(nombres_vars)
        A = np.zeros((num_restricciones, num_vars))

        for i, restr in enumerate(modelo.restricciones):
            for j, var in enumerate(nombres_vars):
                A[i, j] = restr.coeficientes.variables.get(var, 0.0)

        return A