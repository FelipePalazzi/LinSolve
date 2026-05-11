"""
main.py - API FastAPI con Rate Limiting, CORS y Logging estructurado
Punto de entrada del motor matemático LinSolve.
"""

import uuid
import os
import json
import sys
import httpx
from loguru import logger
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from typing import Dict, List, Any

load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from backend.models import (
    SolveRequest, SolveResponse, ErrorResponse,
    ModeloPrimal, PlanteoValidacion, ResultadoVariable,
    RestriccionResultado, ModeloDualExplícito, AnalisisSensibilidad,
    WhatIfRequest, WhatIfResponse, WhatIfModificacion,
    Restriccion, CoeficientesRestriccion, ModeloPrimalRequest, ExtraerResponse
)
from backend.solver import PuLPSolver, SolverError
from backend.validation import ModeloValidator, ValidationError

logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="DEBUG"
)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LinSolve API iniciada")
    yield
    logger.info("LinSolve API apagada")


app = FastAPI(
    title="LinSolve API",
    description="Motor matemático de Programación Lineal con análisis Primal-Dual",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:4321,http://localhost:3000").split(",")

# Configuración Nvidia NIM (vía .env)
# 1. Extracción de modelo (Text-to-Math)
NVIDIA_EXTRACT_URL = os.getenv("NVIDIA_EXTRACT_URL", os.getenv("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1/chat/completions"))
NVIDIA_EXTRACT_MODEL = os.getenv("NVIDIA_EXTRACT_MODEL", os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro"))

# 2. Análisis de negocio (Math-to-Business)
NVIDIA_ANALYSIS_URL = os.getenv("NVIDIA_ANALYSIS_URL", os.getenv("NVIDIA_API_URL", "https://integrate.api.nvidia.com/v1/chat/completions"))
NVIDIA_ANALYSIS_MODEL = os.getenv("NVIDIA_ANALYSIS_MODEL", os.getenv("NVIDIA_MODEL", "deepseek-ai/deepseek-v4-pro"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
)


@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    """Middleware que genera X-Request-ID por cada petición"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id

    logger.info(
        f"[ReqID: {request_id}] {request.method} {request.url.path} - IP: {get_remote_address(request)}"
    )

    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health_check():
    """Endpoint de salud para monitoring"""
    return {"status": "healthy", "service": "LinSolve"}


@app.post("/api/solve", response_model=ExtraerResponse, responses={
    400: {"model": ErrorResponse, "description": "JSON malformado"},
    422: {"model": ErrorResponse, "description": "Esquema Pydantic no válido"},
    429: {"model": ErrorResponse, "description": "Rate limit excedido"},
    500: {"model": ErrorResponse, "description": "Error interno del solver"},
    502: {"model": ErrorResponse, "description": "Error en comunicación con LLM"}
})
@limiter.limit(os.getenv("RATE_LIMIT", "10/minute"))
async def extraer_modelo(request: Request, solve_request: SolveRequest) -> ExtraerResponse:
    """
    Endpoint para extraer el modelo primal usando el LLM.
    Retorna el planteo para validación del usuario (no resuelve).
    """
    request_id = request.state.request_id

    logger.info(f"[ReqID: {request_id}] Extrayendo modelo con LLM")

    try:
        modelo_primal = await _extraer_modelo_primal(solve_request.problema_texto, request_id)

        errores = ModeloValidator.validar(modelo_primal)
        if not errores[0]:
            logger.warning(f"[ReqID: {request_id}] Validación fallida: {errores[1]}")
            raise HTTPException(
                status_code=422,
                detail={
                    "codigo": 422,
                    "error": "VALIDATION_ERROR",
                    "detalle": errores[1],
                    "request_id": request_id
                }
            )

        solver = PuLPSolver()
        planteo = solver._generar_planteo_validacion(modelo_primal)

        logger.info(f"[ReqID: {request_id}] Modelo extraído exitosamente")
        return ExtraerResponse(planteo=planteo, modelo_primal=modelo_primal)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[ReqID: {request_id}] Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "codigo": 500,
            "error": "INTERNAL_ERROR",
            "detalle": "Error inesperado en extracción de modelo",
            "request_id": request_id
        })


@app.post("/api/resolve", response_model=SolveResponse, responses={
    400: {"model": ErrorResponse, "description": "JSON malformado"},
    422: {"model": ErrorResponse, "description": "Esquema Pydantic no válido"},
    429: {"model": ErrorResponse, "description": "Rate limit excedido"},
    500: {"model": ErrorResponse, "description": "Error interno del solver"}
})
@limiter.limit(os.getenv("RATE_LIMIT", "10/minute"))
async def resolver_modelo(request: Request, model_request: ModeloPrimalRequest) -> SolveResponse:
    """
    Endpoint para resolver un modelo primal ya validado.
    No llama al LLM, recibe el modelo directamente.
    """
    request_id = request.state.request_id

    logger.info(f"[ReqID: {request_id}] Resolviendo modelo primal")

    try:
        modelo_primal = model_request.modelo_primal

        errores = ModeloValidator.validar(modelo_primal)
        if not errores[0]:
            logger.warning(f"[ReqID: {request_id}] Validación fallida: {errores[1]}")
            raise HTTPException(
                status_code=422,
                detail={
                    "codigo": 422,
                    "error": "VALIDATION_ERROR",
                    "detalle": errores[1],
                    "request_id": request_id
                }
            )

        solver = PuLPSolver(
            tolerancia=model_request.configuracion.get('tolerancia', 0.0001) if model_request.configuracion else 0.0001,
            tiempo_maximo=model_request.configuracion.get('tiempo_maximo_seg', 30) if model_request.configuracion else 30
        )
        resultado = solver.resolver(modelo_primal, request_id)

        logger.info(f"[ReqID: {request_id}] Resolución exitosa - Estado: {resultado.estado}")
        return resultado

    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"[ReqID: {request_id}] ValidationError: {e.mensaje}")
        raise HTTPException(status_code=422, detail={
            "codigo": 422,
            "error": "VALIDATION_ERROR",
            "detalle": e.mensaje,
            "request_id": request_id
        })
    except SolverError as e:
        logger.error(f"[ReqID: {request_id}] SolverError: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "codigo": 500,
            "error": "SOLVER_ERROR",
            "detalle": str(e),
            "request_id": request_id
        })
    except Exception as e:
        logger.error(f"[ReqID: {request_id}] Error inesperado: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "codigo": 500,
            "error": "INTERNAL_ERROR",
            "detalle": "Error inesperado en el motor matemático",
            "request_id": request_id
        })


class DualRequest(BaseModel):
    """Request para calcular el dual de un modelo ya resuelto"""
    modelo_primal: ModeloPrimal
    resultado_variables: List[Dict[str, Any]]
    resultado_restricciones: List[Dict[str, Any]]


class DualResponse(BaseModel):
    """Respuesta con el tableau dual"""
    dual_optimo: Dict
    W_valor: float


@app.post("/api/dual", response_model=DualResponse, responses={
    422: {"model": ErrorResponse, "description": "Esquema no válido"},
    500: {"model": ErrorResponse, "description": "Error interno"}
})
@limiter.limit(os.getenv("RATE_LIMIT", "10/minute"))
async def calcular_dual(request: Request, dual_request: DualRequest):
    """
    Calcula el tableau dual bajo demanda.
    Recibe el modelo primal ya resuelto y retorna el tableau dual.
    """
    request_id = request.state.request_id
    logger.info(f"[ReqID: {request_id}] Calculando tableau dual bajo demanda")

    try:
        solver = PuLPSolver()
        modelo = dual_request.modelo_primal

        problema = solver._crear_problema_pulp(modelo)
        problema.solve(PULP_CBC_CMD(msg=0))

        dual_data = solver._generar_tableau_dual_optimo(modelo, problema)

        W_valor = dual_request.resultado_variables[0].get('valor', 0) * 0 if len(dual_request.resultado_variables) > 0 else 0

        return DualResponse(
            dual_optimo=dual_data,
            W_valor=round(W_valor, 6)
        )

    except Exception as e:
        logger.error(f"[ReqID: {request_id}] Error calculando dual: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "codigo": 500,
            "error": "DUAL_ERROR",
            "detalle": str(e),
            "request_id": request_id
        })


def _corregir_nombres_restricciones(json_str: str) -> ModeloPrimal | None:
    """
    Intenta corregir errores comunes del LLM:
    1. Nombres de restricciones que no siguen el patrón R1, R2
    2. coeficientes sin el campo "variables" anidado
    """
    import re
    try:
        data = json.loads(json_str)
        if "restricciones" in data:
            for i, restr in enumerate(data["restricciones"]):
                if "nombre" in restr:
                    restr["nombre"] = f"R{i + 1}"
                if "coeficientes" in restr:
                    coef = restr["coeficientes"]
                    if isinstance(coef, dict) and "variables" not in coef:
                        if any(k in coef for k in ["x1", "x2", "x3", "x4", "x5"]):
                            restr["coeficientes"] = {"variables": coef}
        return ModeloPrimal(**data)
    except Exception:
        return None


async def _extraer_modelo_primal(texto_problema: str, request_id: str) -> ModeloPrimal:
    """
    Envía el texto al LLM (Nvidia NIM) para extraer el modelo primal.

    Args:
        texto_problema: Descripción del problema en lenguaje natural
        request_id: UUID para trazabilidad

    Returns:
        ModeloPrimal validado

    Raises:
        HTTPException 502: Si la llamada al LLM falla
        HTTPException 422: Si el JSON devuelto no coincide con el esquema
    """
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")
    if not nvidia_api_key:
        raise HTTPException(status_code=500, detail={
            "codigo": 500,
            "error": "CONFIG_ERROR",
            "detalle": "NVIDIA_API_KEY no configurada",
            "request_id": request_id
        })

    prompt = f"""Eres un extractor de JSON. Responde SOLO con JSON válido.

Problema de Programación Lineal: {texto_problema}

Esquema JSON exacto (presta atención a los campos anidados):
{{
  "tipo_optimizacion": "max",
  "funcion_objetivo": {{"x1": 60, "x2": 30, "x3": 20}},
  "restricciones": [
    {{"nombre": "R1", "coeficientes": {{"variables": {{"x1": 8, "x2": 6, "x3": 1}}}}, "tipo": "<=", "rhs": 48}}
  ],
  "nombre_variable_objetivo": "Z",
  "descripcion_variables": {{"x1": "escritorios", "x2": "mesas", "x3": "sillas"}}
}}

OBSERVA bien: "coeficientes" contiene "variables" que contiene los coeficientes.
NO hagas: "coeficientes": {{"x1": 8}}
HACER: "coeficientes": {{"variables": {{"x1": 8}}}}

Solo JSON, sin texto adicional."""

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                NVIDIA_EXTRACT_URL,
                headers={
                    "Authorization": f"Bearer {nvidia_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": NVIDIA_EXTRACT_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 2048,
                    "stream": False
                }
            )

            if response.status_code != 200:
                logger.error(f"[ReqID: {request_id}] Nvidia API error: {response.status_code}")
                error_detail = response.text if response.text else f"HTTP {response.status_code}"
                raise HTTPException(status_code=502, detail={
                    "codigo": 502,
                    "error": "LLM_ERROR",
                    "detalle": f"Error en comunicación con Nvidia API: {response.status_code}. Detalle: {error_detail[:200]}",
                    "request_id": request_id
                })

            data = response.json()
            contenido = data["choices"][0]["message"]["content"]

            contenido_limpio = contenido.strip()
            if contenido_limpio.startswith("```"):
                lines = contenido_limpio.split('\n')
                contenido_limpio = '\n'.join(lines[1:-1])
            contenido_limpio = contenido_limpio.strip()

            try:
                modelo_dict = json.loads(contenido_limpio)
                modelo_primal = ModeloPrimal(**modelo_dict)
                logger.info(f"[ReqID: {request_id}] Modelo primal extraído del LLM")
                return modelo_primal
            except Exception as validation_error:
                error_str = str(validation_error) if str(validation_error) else repr(validation_error)
                logger.warning(f"[ReqID: {request_id}] Validación falló: {error_str[:500]}")
                logger.info(f"[ReqID: {request_id}] Contenido LLM (primeros 300 chars): {contenido_limpio[:300]}")
                if "string_pattern_mismatch" in error_str or "validation errors" in error_str.lower():
                    logger.warning(f"[ReqID: {request_id}] Intentando corregir nombres de restricciones")
                    modelo_corregido = _corregir_nombres_restricciones(contenido_limpio)
                    if modelo_corregido:
                        logger.info(f"[ReqID: {request_id}] Nombres de restricciones corregidos automáticamente")
                        return modelo_corregido
                logger.error(f"[ReqID: {request_id}] Error de validación final: {error_str[:500]}")
                raise HTTPException(status_code=422, detail={
                    "codigo": 422,
                    "error": "VALIDATION_ERROR",
                    "detalle": f"El modelo generado no es válido: {error_str[:500]}",
                    "request_id": request_id
                })

    except json.JSONDecodeError as e:
        logger.error(f"[ReqID: {request_id}] JSON del LLM malformado: {str(e)}")
        raise HTTPException(status_code=422, detail={
            "codigo": 422,
            "error": "MALFORMED_JSON",
            "detalle": f"El LLM devolvió un JSON inválido: {str(e)[:200]}",
            "request_id": request_id
        })
    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e) if str(e) else type(e).__name__
        logger.error(f"[ReqID: {request_id}] Error en llamada al LLM: {error_str[:300]}")
        logger.debug(f"[ReqID: {request_id}] Exception type: {type(e).__name__}")
        raise HTTPException(status_code=422, detail={
            "codigo": 422,
            "error": "VALIDATION_ERROR",
            "detalle": f"Error de validación del modelo: {error_str[:300] if error_str else type(e).__name__}",
            "request_id": request_id
        })


@app.post("/api/analisis-negocio", responses={
    502: {"model": ErrorResponse, "description": "Error en comunicación con LLM"}
})
@limiter.limit(os.getenv("RATE_LIMIT", "10/minute"))
async def generar_analisis_negocio(request: Request, analisis: AnalisisSensibilidad) -> Dict:
    """
    Genera análisis de sensibilidad en lenguaje de negocio usando el LLM.

    Args:
        analisis: Datos del análisis de sensibilidad de PuLP

    Returns:
        Diccionario con interpretación en lenguaje natural
    """
    request_id = request.state.request_id
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")

    if not nvidia_api_key:
        raise HTTPException(status_code=500, detail={
            "codigo": 500,
            "error": "CONFIG_ERROR",
            "detalle": "NVIDIA_API_KEY no configurada",
            "request_id": request_id
        })

    prompt = f"""Eres un analista de investigación de operaciones. Analiza los siguientes datos de sensibilidad y explica en lenguaje de negocio qué acciones debería tomar la empresa.

Datos del análisis:
- Rangos de optimalidad: {analisis.rango_optimos}
- Interpretación de costos reducidos: {analisis.costo_reducido_interpretacion}
- Interpretación de holguras: {analisis.holguras_interpretacion}
- Relación Z=W: {analisis.relacion_Z_equals_W}

Proporciona:
1. Qué recursos son limitantes (restricciones activas)
2. Cuánto puede incrementarse/decrementarse el uso de cada recurso
3. Recomendaciones de negocio basadas en los precios sombra
4. Riesgos si se modifican las restricciones

Responde en español, en formato estructurado con encabezados."""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                NVIDIA_ANALYSIS_URL,
                headers={
                    "Authorization": f"Bearer {nvidia_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": NVIDIA_ANALYSIS_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 1,
                    "top_p": 0.95,
                    "extra_body": {"chat_template_kwargs":{"thinking":False}},
                    "max_tokens": 16384
                }
            )

            if response.status_code != 200:
                raise HTTPException(status_code=502, detail={
                    "codigo": 502,
                    "error": "LLM_ERROR",
                    "detalle": "Error en comunicación con Nvidia API",
                    "request_id": request_id
                })

            data = response.json()
            return {
                "analisis_negocio": data["choices"][0]["message"]["content"],
                "request_id": request_id
            }

    except Exception as e:
        logger.error(f"[ReqID: {request_id}] Error en análisis de negocio: {str(e)}")
        raise HTTPException(status_code=502, detail={
            "codigo": 502,
            "error": "LLM_ERROR",
            "detalle": str(e),
            "request_id": request_id
        })


@app.post("/api/what-if", response_model=WhatIfResponse, responses={
    400: {"model": ErrorResponse, "description": "Modelo inválido"},
    422: {"model": ErrorResponse, "description": "Error de validación"},
    500: {"model": ErrorResponse, "description": "Error interno"}
})
@limiter.limit(os.getenv("RATE_LIMIT", "10/minute"))
async def what_if_analysis(request: Request, what_if_request: WhatIfRequest) -> WhatIfResponse:
    """
    Endpoint para análisis What-If.
    Modifica coeficientes del modelo y re-resuelve para ver el impacto en Z.
    """
    request_id = request.state.request_id
    logger.info(f"[ReqID: {request_id}] Análisis What-If con {len(what_if_request.modificaciones)} modificaciones")

    try:
        from copy import deepcopy
        modelo_modificado = deepcopy(what_if_request.modelo_original)

        for mod in what_if_request.modificaciones:
            if mod.tipo == "coef_objetivo":
                if mod.variable in modelo_modificado.funcion_objetivo:
                    modelo_modificado.funcion_objetivo[mod.variable] = mod.valor_nuevo
            elif mod.tipo == "rhs":
                for restr in modelo_modificado.restricciones:
                    if restr.nombre == mod.variable:
                        restr.rhs = mod.valor_nuevo
                        break
            elif mod.tipo == "coef_tecnologico":
                for restr in modelo_modificado.restricciones:
                    if restr.nombre == mod.restriccion:
                        if mod.variable in restr.coeficientes.variables:
                            restr.coeficientes.variables[mod.variable] = mod.valor_nuevo
                        break
            elif mod.tipo == "nueva_restriccion":
                if mod.restriccion_nueva:
                    modelo_modificado.restricciones.append(mod.restriccion_nueva)
            elif mod.tipo == "nueva_actividad":
                if mod.datos_actividad:
                    nueva_var = mod.variable
                    precio = mod.datos_actividad.get('precio', 0)
                    coef_tecnologicos = mod.datos_actividad.get('coeficientes', {})

                    modelo_modificado.funcion_objetivo[nueva_var] = precio

                    num_restricciones = len(modelo_modificado.restricciones)
                    nueva_restriccion = Restriccion(
                        nombre=f"R{num_restricciones + 1}",
                        coeficientes=CoeficientesRestriccion(variables=coef_tecnologicos),
                        tipo="<=",
                        rhs=mod.valor_nuevo
                    )
                    modelo_modificado.restricciones.append(nueva_restriccion)
            elif mod.tipo == "demanda_min":
                num_restricciones = len(modelo_modificado.restricciones)
                nueva_restriccion = Restriccion(
                    nombre=f"R{num_restricciones + 1}",
                    coeficientes=CoeficientesRestriccion(variables={mod.variable: 1.0}),
                    tipo=">=",
                    rhs=mod.valor_nuevo
                )
                modelo_modificado.restricciones.append(nueva_restriccion)

        solver = PuLPSolver()
        resultado_original = solver.resolver(
            what_if_request.modelo_original,
            f"{request_id}-original"
        )

        resultado_nuevo = solver.resolver(modelo_modificado, request_id)

        diferencia = resultado_nuevo.Z_valor - resultado_original.Z_valor
        cambio_porcentual = (diferencia / resultado_original.Z_valor * 100) if resultado_original.Z_valor != 0 else 0

        restricciones_afectadas = []
        for i, (orig, nuevo) in enumerate(zip(
            what_if_request.modelo_original.restricciones,
            modelo_modificado.restricciones
        )):
            if abs(orig.rhs - nuevo.rhs) > 0.001:
                restricciones_afectadas.append(f"{orig.nombre}: {orig.rhs} → {nuevo.rhs}")

        if len(modelo_modificado.restricciones) > len(what_if_request.modelo_original.restricciones):
            restricciones_afectadas.append(f"Nueva restricción agregada")

        logger.info(
            f"[ReqID: {request_id}] What-If completado: Z {resultado_original.Z_valor:.4f} → {resultado_nuevo.Z_valor:.4f}"
        )

        return WhatIfResponse(
            Z_original=resultado_original.Z_valor,
            Z_nuevo=resultado_nuevo.Z_valor,
            diferencia=round(diferencia, 6),
            cambio_porcentual=round(cambio_porcentual, 2),
            restricciones_afectadas=restricciones_afectadas,
            tableau_optimo_nuevo=resultado_nuevo.tableaux.primal_optimo if resultado_nuevo.tableaux else None,
            dual_optimo_nuevo=resultado_nuevo.tableaux.dual_optimo if resultado_nuevo.tableaux else None
        )

    except Exception as e:
        logger.error(f"[ReqID: {request_id}] Error en What-If: {str(e)}")
        raise HTTPException(status_code=500, detail={
            "codigo": 500,
            "error": "WHATIF_ERROR",
            "detalle": str(e),
            "request_id": request_id
        })