"""
models.py - Esquemas Pydantic para LinSolve
Define los schemas de validación de entrada/salida siguiendo rigor matemático de Hillier & Lieberman.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Dict, List, Literal, Optional
import re


class CoeficientesRestriccion(BaseModel):
    """
    Coeficientes tecnológicos de una restricción.
    Cada entrada representa el coeficiente de una variable en la restricción.
    """
    variables: Dict[str, float]

    @field_validator('variables')
    @classmethod
    def validar_coeficientes(cls, v: Dict[str, float]) -> Dict[str, float]:
        for var, coef in v.items():
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var):
                raise ValueError(f"Nombre de variable inválido: {var}")
        return v


class Restriccion(BaseModel):
    """
    Representa una restricción en el modelo de Programación Lineal.
    Nombre debe seguir el patrón R1, R2, ..., Rn según Hillier & Lieberman.
    """
    nombre: str = Field(..., pattern=r"^[R][0-9]+$")
    coeficientes: CoeficientesRestriccion
    tipo: Literal["<=", ">=", "="]
    rhs: float
    nombre_variable_holgura: Optional[str] = None

    @field_validator('rhs')
    @classmethod
    def rhs_no_nulo(cls, v: float) -> float:
        return v


class FuncionObjetivo(BaseModel):
    """Función objetivo del modelo primal"""
    coeficientes: Dict[str, float]
    tipo: Literal["max", "min"]

    @field_validator('coeficientes')
    @classmethod
    def validar_coeficientes(cls, v: Dict[str, float]) -> Dict[str, float]:
        if not v:
            raise ValueError("La función objetivo debe tener al menos una variable")
        for var, coef in v.items():
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', var):
                raise ValueError(f"Nombre de variable inválido: {var}")
        return v


class ModeloPrimal(BaseModel):
    """
    Modelo Primal completo según la formulación estándar de Hillier & Lieberman.
    Variables continuas, maximización o minimización, restricciones de desigualdad/igualdad.
    """
    tipo_optimizacion: Literal["max", "min"]
    funcion_objetivo: Dict[str, float]
    restricciones: List[Restriccion]
    nombre_variable_objetivo: str = "Z"

    @field_validator('restricciones')
    @classmethod
    def validar_restricciones_no_vacias(cls, v: List[Restriccion]) -> List[Restriccion]:
        if not v:
            raise ValueError("Debe haber al menos una restricción")
        return v


class PlanteoValidacion(BaseModel):
    """
    Devuelve el planteo interpretado para que el usuario valide antes de resolver.
    Fase crítica para evitar que la IA interprete mal el problema.
    """
    funcion_objetivo_texto: str
    restricciones_texto: List[str]
    variables_texto: List[str]


class ResultadoVariable(BaseModel):
    """Resultado de una variable en la solución óptima"""
    nombre: str
    valor: float
    holgura: Optional[float] = None
    precio_sombra: Optional[float] = None
    costo_reducido: Optional[float] = None


class RestriccionResultado(BaseModel):
    """Resultado de una restricción en la solución óptima"""
    nombre: str
    tipo: str
    RHS_original: float
    RHS_actualizado: Optional[float] = None
    holgura: float
    precio_sombra: float
    activa: bool


class RestriccionDual(BaseModel):
    """Una restricción del modelo dual explícito"""
    nombre: str
    coeficientes: Dict[str, float]
    tipo: Literal[">=", "<=", "="]
    rhs: float


class ModeloDualExplícito(BaseModel):
    """
    Modelo Dual explícito con matriz transpuesta.
    Generado algorítmicamente a partir del primal según las reglas de dualidad de Hillier & Lieberman:
    - Si primal es max, dual es min (y viceversa)
    - Los coeficientes RHS del primal se convierten en coeficientes de la función objetivo dual
    - La matriz A se transpone
    """
    tipo_optimizacion: Literal["max", "min"]
    funcion_objetivo: str
    variable_objetivo: str = "W"
    restricciones: List[RestriccionDual]
    interpretacion: str


class RangoOptimo(BaseModel):
    """Rango de optimalidad para una variable"""
    variable: str
    min: float
    max: float


class AnalisisSensibilidad(BaseModel):
    """Análisis de sensibilidad completo según Hillier & Lieberman"""
    rango_optimos: List[RangoOptimo]
    costo_reducido_interpretacion: str
    holguras_interpretacion: str
    relacion_Z_equals_W: str


class TableauColumna(BaseModel):
    """Una columna del tableau simplex"""
    nombre: str
    ck: float
    tipo: Literal["variable_original", "slack", "artificial"]


class TableauFila(BaseModel):
    """Una fila de restricción del tableau"""
    nombre: str
    ck: float
    variables_basicas: str
    bk: float
    coeficientes: List[float]
    zj_cj: float


class TableauIteracion(BaseModel):
    """Tableau de una iteración específica del simplex"""
    iteracion: int
    nombre_objetivo: str
    tipo_optimizacion: Literal["max", "min"]
    nombres_columnas: List[str]
    nombres_vars_originales: List[str]
    nombres_slack: List[str]
    ck: List[float]
    variables_basicas: List[str]
    rhs: List[float]
    fila_z: List[float]
    matriz: List[List[float]]
    num_filas: int
    num_columnas: int


class TableauRespuesta(BaseModel):
    """Tableaux (inicial y óptimo) para primal y dual"""
    primal_inicial: TableauIteracion
    primal_optimo: TableauIteracion
    dual_optimo: TableauIteracion
    Z_valor: float
    W_valor: float


class WhatIfModificacion(BaseModel):
    """Modificación a aplicar para análisis What-If"""
    tipo: Literal["coef_objetivo", "rhs", "coef_tecnologico", "nueva_restriccion"]
    variable: str
    restriccion: Optional[str] = None
    valor_nuevo: float
    restriccion_nueva: Optional["Restriccion"] = None


class WhatIfRequest(BaseModel):
    """Request para análisis What-If"""
    modelo_original: ModeloPrimal
    modificaciones: List[WhatIfModificacion]


class WhatIfResponse(BaseModel):
    """Respuesta del análisis What-If"""
    Z_original: float
    Z_nuevo: float
    diferencia: float
    cambio_porcentual: float
    restricciones_afectadas: List[str]
    tableau_optimo_nuevo: Optional[TableauIteracion] = None
    dual_optimo_nuevo: Optional[TableauIteracion] = None


class SolveResponse(BaseModel):
    """
    Respuesta completa del solver con primal, dual y análisis de sensibilidad.
    Incluye request_id para trazabilidad en logs.
    """
    estado: Literal["OPTIMO", "INFEASIBLE", "NO_ACOTADO", "ERROR"]
    modelo_primal_valido: PlanteoValidacion
    modelo_primal: Optional[ModeloPrimal] = None  # Para What-If
    resultado_variables: List[ResultadoVariable]
    resultado_restricciones: List[RestriccionResultado]
    modelo_dual: ModeloDualExplícito
    analisis_sensibilidad: AnalisisSensibilidad
    tiempo_resolucion_ms: float
    request_id: str
    Z_valor: float = 0.0
    W_valor: float = 0.0
    tableaux: Optional[TableauRespuesta] = None


class SolveRequest(BaseModel):
    """
    Request desde el frontend (Astro BFF -> FastAPI)
    """
    problema_texto: str
    configuracion: Optional[Dict[str, float]] = None

    @property
    def tolerancia(self) -> float:
        return self.configuracion.get('tolerancia', 0.0001) if self.configuracion else 0.0001

    @property
    def tiempo_maximo_seg(self) -> int:
        return int(self.configuracion.get('tiempo_maximo_seg', 30)) if self.configuracion else 30

    @property
    def presicion(self) -> int:
        return int(self.configuracion.get('presicion', 6)) if self.configuracion else 6


class ErrorResponse(BaseModel):
    """Respuesta de error estandarizada con código HTTP"""
    codigo: int
    error: str
    detalle: str
    request_id: Optional[str] = None