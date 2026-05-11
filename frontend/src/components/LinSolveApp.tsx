/**
 * LinSolveApp.tsx - Componente principal de LinSolve
 * Maneja el flujo completo: textarea -> LLM -> PuLP -> Visualización
 */

import React, { useState } from 'react';
import type {
  SolveRequest,
  SolveResponse,
  ErrorResponse,
  TabActiva,
  PlanteoValidacion
} from '../types';
import { PrimalDualTables } from './PrimalDualTables';
import { WhatIfAnalysis } from './WhatIfAnalysis';

export function LinSolveApp() {
  const [problemaTexto, setProblemaTexto] = useState<string>('');
  const [response, setResponse] = useState<SolveResponse | null>(null);
  const [error, setError] = useState<ErrorResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [tabActiva, setTabActiva] = useState<TabActiva>('validacion');
  const [plantoConfirmado, setPlantoConfirmado] = useState<boolean>(false);
  const [interpretacion, setInterpretacion] = useState<string | null>(null);
  const [loadingInterpretacion, setLoadingInterpretacion] = useState<boolean>(false);
  const [planteoValidacion, setPlanteoValidacion] = useState<PlanteoValidacion | null>(null);
  const [modeloExtraido, setModeloExtraido] = useState<any>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!problemaTexto.trim()) return;

    setLoading(true);
    setError(null);
    setResponse(null);
    setPlantoConfirmado(false);
    setTabActiva('validacion');
    setPlanteoValidacion(null);
    setModeloExtraido(null);

    try {
      const request = {
        problema_texto: problemaTexto,
        configuracion: {
          tolerancia: 0.0001,
          tiempo_maximo_seg: 30,
          presicion: 6
        }
      };

      const resp = await fetch('/api/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });

      const data = await resp.json();

      if (!resp.ok) {
        let errorMessage = `Error ${resp.status}`;
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (data.detail.detalle) {
            errorMessage = data.detail.detalle;
          } else if (data.detail.error) {
            errorMessage = data.detail.error;
          }
        }
        throw new Error(errorMessage);
      }

      setPlanteoValidacion(data.planteo as PlanteoValidacion);
      setModeloExtraido(data.modelo_primal);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError({
        codigo: 500,
        error: 'CLIENT_ERROR',
        detalle: message
      });
    } finally {
      setLoading(false);
    }
  };

  const confirmarPlanteo = async () => {
    if (!modeloExtraido) return;

    setLoading(true);
    try {
      const request = {
        modelo_primal: modeloExtraido,
        configuracion: {
          tolerancia: 0.0001,
          tiempo_maximo_seg: 30,
          presicion: 6
        }
      };

      const resp = await fetch('/api/resolve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });

      const data = await resp.json();

      if (!resp.ok) {
        let errorMessage = `Error ${resp.status}`;
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMessage = data.detail;
          } else if (data.detail.detalle) {
            errorMessage = data.detail.detalle;
          }
        }
        throw new Error(errorMessage);
      }

      setResponse(data as SolveResponse);
      setPlantoConfirmado(true);
      setTabActiva('primal');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error desconocido';
      setError({
        codigo: 500,
        error: 'CLIENT_ERROR',
        detalle: message
      });
    } finally {
      setLoading(false);
    }
  };

  const cargarInterpretacion = async () => {
    if (!response) return;
    setLoadingInterpretacion(true);

    try {
      const res = await fetch('/api/analisis-negocio', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(response.analisis_sensibilidad)
      });

      const data = await res.json();
      setInterpretacion(data.analisis_negocio);
    } catch (err) {
      setInterpretacion('Error al cargar interpretación');
    } finally {
      setLoadingInterpretacion(false);
    }
  };

  const renderPlanteoValidacion = (planteo: PlanteoValidacion) => (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <h3 className="text-lg font-semibold mb-4">Validación del Planteo</h3>
      <p className="text-sm text-gray-600 mb-4">
        Por favor, verificá que la interpretación del problema sea correcta antes de ver los resultados.
      </p>

      <div className="mb-4">
        <label className="block font-medium text-gray-700 mb-1">Función Objetivo</label>
        <div className="bg-blue-50 p-3 rounded border border-blue-200 font-mono">
          {planteo.funcion_objetivo_texto}
        </div>
      </div>

      <div className="mb-4">
        <label className="block font-medium text-gray-700 mb-1">Restricciones</label>
        <ul className="space-y-2">
          {planteo.restricciones_texto.map((rest, idx) => (
            <li key={idx} className="bg-gray-50 p-2 rounded border border-gray-200 font-mono text-sm">
              {rest}
            </li>
          ))}
        </ul>
      </div>

      <div className="mb-4">
        <label className="block font-medium text-gray-700 mb-1">Variables</label>
        <ul className="space-y-1">
          {planteo.variables_texto.map((v, idx) => (
            <li key={idx} className="text-gray-600 text-sm">
              {v}
            </li>
          ))}
        </ul>
      </div>

      <div className="flex gap-2">
        <button
          onClick={confirmarPlanteo}
          className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 transition-colors"
        >
          Confirmar y ver resultados
        </button>
        <button
          onClick={() => setProblemaTexto('')}
          className="bg-gray-200 text-gray-700 px-4 py-2 rounded hover:bg-gray-300 transition-colors"
        >
          Modificar problema
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-10 flex flex-col items-center gap-4">
          <picture className="w-auto h-25 object-contain">
            <img
              src="/logo-header.png"
              alt="LinSolve Logo"
              className="w-full h-full object-contain"
            />
          </picture>
          <p className="text-gray-600 font-medium">
            Plataforma de Programación Lineal con análisis Primal-Dual
          </p>
        </header>

        {!response && !error && (
          <form onSubmit={handleSubmit} className="bg-white p-6 rounded-lg shadow-md">
            <label htmlFor="problema" className="block font-medium text-gray-700 mb-2">
              Describe tu problema de optimización en lenguaje natural
            </label>
            <textarea
              id="problema"
              value={problemaTexto}
              onChange={(e) => setProblemaTexto(e.target.value)}
              placeholder="Ej: Una empresa produce dos productos A y B. Cada unidad de A genera $3 de ganancia y requiere 2 horas de mano de obra. Cada unidad de B genera $5 de ganancia y requiere 3 horas de mano de obra. Hay disponibles 100 horas de mano de obra."
              className="w-full h-40 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !problemaTexto.trim()}
              className="mt-4 bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? 'Procesando...' : 'Resolver problema'}
            </button>
          </form>
        )}

        {loading && (
          <div className="bg-white p-6 rounded-lg shadow-md text-center">
            <div className="animate-spin h-8 w-8 border-4 border-blue-600 border-t-transparent rounded-full mx-auto mb-4"></div>
            <p className="text-gray-600">Procesando problema con IA y resolviendo modelo...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 p-4 rounded-lg">
            <h3 className="text-red-800 font-semibold">Error</h3>
            <p className="text-red-600">{error.detalle}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-red-700 underline"
            >
              Intentar de nuevo
            </button>
          </div>
        )}

        {planteoValidacion && !plantoConfirmado && (
          <div>
            {renderPlanteoValidacion(planteoValidacion)}
          </div>
        )}

        {response && plantoConfirmado && (
          <div>
            <div className="flex gap-2 mb-4">
              <button
                onClick={() => setTabActiva('validacion')}
                className={`px-4 py-2 rounded ${tabActiva === 'validacion' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
              >
                Validación
              </button>
              <button
                onClick={() => setTabActiva('primal')}
                className={`px-4 py-2 rounded ${tabActiva === 'primal' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
              >
                Tabla Primal
              </button>
              <button
                onClick={() => setTabActiva('dual')}
                className={`px-4 py-2 rounded ${tabActiva === 'dual' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
              >
                Tabla Dual
              </button>
              <button
                onClick={() => setTabActiva('sensibilidad')}
                className={`px-4 py-2 rounded ${tabActiva === 'sensibilidad' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
              >
                Análisis Sensibilidad
              </button>
              <button
                onClick={() => setTabActiva('whatif')}
                className={`px-4 py-2 rounded ${tabActiva === 'whatif' ? 'bg-orange-600 text-white' : 'bg-orange-200'}`}
              >
                What-If
              </button>
              <button
                onClick={() => {
                  setTabActiva('interpretacion');
                  if (!interpretacion) cargarInterpretacion();
                }}
                className={`px-4 py-2 rounded ${tabActiva === 'interpretacion' ? 'bg-purple-600 text-white' : 'bg-purple-200'}`}
              >
                Interpretación IA
              </button>
            </div>

            {tabActiva === 'whatif' ? (
              <WhatIfAnalysis response={response} />
            ) : tabActiva === 'interpretacion' ? (
              <div className="bg-white p-6 rounded-lg shadow-md">
                <h3 className="text-xl font-semibold mb-4 text-gray-800">Interpretación de Negocios</h3>
                {loadingInterpretacion ? (
                  <div className="flex justify-center items-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
                    <span className="ml-3 text-gray-600">Generando interpretación...</span>
                  </div>
                ) : interpretacion ? (
                  <div className="prose prose-sm max-w-none">
                    <p className="text-gray-700 whitespace-pre-wrap">{interpretacion}</p>
                  </div>
                ) : (
                  <p className="text-gray-500">Sin interpretación disponible</p>
                )}
              </div>
            ) : (
              <PrimalDualTables
                response={response}
                tabActiva={tabActiva}
              />
            )}
          </div>
        )}

        {response && (
          <div className="mt-4 text-sm text-gray-500">
            Request ID: {response.request_id} | Tiempo: {response.tiempo_resolucion_ms}ms | Estado: {response.estado}
          </div>
        )}
      </div>
    </div>
  );
}