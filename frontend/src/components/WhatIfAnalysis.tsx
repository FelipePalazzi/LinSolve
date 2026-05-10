/**
 * WhatIfAnalysis.tsx - Componente de análisis What-If interactivo
 * Permite modificar coeficientes y RHS para ver cómo afecta al modelo
 */

import React, { useState } from 'react';
import type {
  SolveResponse,
  WhatIfRequest,
  WhatIfResponse,
  ModeloPrimal,
  WhatIfModificacion
} from '../types';

interface Props {
  response: SolveResponse;
}

export function WhatIfAnalysis({ response }: Props) {
  const [modificaciones, setModificaciones] = useState<WhatIfModificacion[]>([]);
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<WhatIfResponse | null>(null);
  const [nuevaModificacion, setNuevaModificacion] = useState<WhatIfModificacion>({
    tipo: 'coef_objetivo',
    variable: '',
    valor_nuevo: 0
  });

  const variablesOriginales = Object.keys(response.modelo_primal_valido.variables_texto.map(v => v.split(' ')[0]));

  const agregarModificacion = () => {
    if (!nuevaModificacion.variable) return;

    const existe = modificaciones.find(m => m.variable === nuevaModificacion.variable && m.tipo === nuevaModificacion.tipo);
    if (existe) {
      setModificaciones(modificaciones.map(m =>
        m.variable === nuevaModificacion.variable && m.tipo === nuevaModificacion.tipo
          ? nuevaModificacion
          : m
      ));
    } else {
      setModificaciones([...modificaciones, nuevaModificacion]);
    }
    setNuevaModificacion({ tipo: 'coef_objetivo', variable: '', valor_nuevo: 0 });
  };

  const eliminarModificacion = (index: number) => {
    setModificaciones(modificaciones.filter((_, i) => i !== index));
  };

  const enviarWhatIf = async () => {
    setLoading(true);
    setResultado(null);

    try {
      const request: WhatIfRequest = {
        modelo_original: response.modelo_primal!,
        modificaciones
      };

      const res = await fetch('/api/whatif', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });

      const data = await res.json();
      if (res.ok) {
        setResultado(data as WhatIfResponse);
      } else {
        alert(data.detail?.detalle || 'Error en el análisis What-If');
      }
    } catch (err) {
      alert('Error al realizar el análisis What-If');
    } finally {
      setLoading(false);
    }
  };

  const getValorOriginal = (variable: string) => {
    if (response.resultado_variables) {
      const found = response.resultado_variables.find(v => v.nombre === variable);
      return found?.valor || 0;
    }
    return 0;
  };

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-800">Análisis What-If</h3>
        <p className="text-sm text-gray-600 mb-4">
          Modificá coeficientes de la función objetivo o RHS de las restricciones para ver cómo afecta la solución óptima.
        </p>

        <div className="bg-green-50 border border-green-200 p-4 rounded-lg mb-6">
          <div className="flex justify-between items-center">
            <span className="font-semibold text-green-800">Z Actual (Óptimo)</span>
            <span className="text-2xl font-bold text-green-600">{response.Z_valor?.toFixed(4)}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de modificación</label>
            <select
              value={nuevaModificacion.tipo}
              onChange={(e) => setNuevaModificacion({ ...nuevaModificacion, tipo: e.target.value as any })}
              className="w-full border border-gray-300 rounded-lg p-2"
            >
              <option value="coef_objetivo">Coeficiente de Función Objetivo</option>
              <option value="rhs">RHS de Restricción</option>
              <option value="nueva_restriccion">Nueva Restricción</option>
            </select>
          </div>
          {nuevaModificacion.tipo !== 'nueva_restriccion' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Variable/Restricción</label>
                <select
                  value={nuevaModificacion.variable}
                  onChange={(e) => setNuevaModificacion({ ...nuevaModificacion, variable: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg p-2"
                >
                  <option value="">Seleccionar...</option>
                  {nuevaModificacion.tipo === 'coef_objetivo' &&
                    response.resultado_variables?.map(v => (
                      <option key={v.nombre} value={v.nombre}>{v.nombre}</option>
                    ))
                  }
                  {nuevaModificacion.tipo === 'rhs' &&
                    response.resultado_restricciones?.map(r => (
                      <option key={r.nombre} value={r.nombre}>{r.nombre}</option>
                    ))
                  }
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nuevo valor</label>
                <input
                  type="number"
                  value={nuevaModificacion.valor_nuevo}
                  onChange={(e) => setNuevaModificacion({ ...nuevaModificacion, valor_nuevo: parseFloat(e.target.value) || 0 })}
                  className="w-full border border-gray-300 rounded-lg p-2"
                />
              </div>
            </>
          )}
        </div>

        {nuevaModificacion.tipo === 'nueva_restriccion' && (
          <div className="bg-purple-50 border border-purple-200 p-4 rounded-lg mb-4">
            <p className="text-sm text-purple-700 mb-2">
              Definí la nueva restricción en formato: a1*x1 + a2*x2 + ... &lt;= RHS
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Nombre RHS (nueva restricción)</label>
                <input
                  type="text"
                  placeholder="R4"
                  value={nuevaModificacion.variable}
                  onChange={(e) => setNuevaModificacion({ ...nuevaModificacion, variable: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">RHS Valor</label>
                <input
                  type="number"
                  value={nuevaModificacion.valor_nuevo}
                  onChange={(e) => setNuevaModificacion({ ...nuevaModificacion, valor_nuevo: parseFloat(e.target.value) || 0 })}
                  className="w-full border border-gray-300 rounded-lg p-2"
                />
              </div>
            </div>
          </div>
        )}

        <button
          onClick={agregarModificacion}
          disabled={!nuevaModificacion.variable}
          className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          Agregar Modificación
        </button>

        {modificaciones.length > 0 && (
          <div className="mt-6">
            <h4 className="font-medium text-gray-700 mb-2">Modificaciones Pendientes</h4>
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border p-2 text-left">Tipo</th>
                  <th className="border p-2 text-left">Variable</th>
                  <th className="border p-2 text-right">Nuevo Valor</th>
                  <th className="border p-2 text-center">Acción</th>
                </tr>
              </thead>
              <tbody>
                {modificaciones.map((mod, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="border p-2 text-sm">
                      {mod.tipo === 'coef_objetivo' ? 'Coef. Objetivo' : 'RHS'}
                    </td>
                    <td className="border p-2 font-mono">{mod.variable}</td>
                    <td className="border p-2 text-right font-mono">{mod.valor_nuevo}</td>
                    <td className="border p-2 text-center">
                      <button
                        onClick={() => eliminarModificacion(index)}
                        className="text-red-600 hover:text-red-800"
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <button
              onClick={enviarWhatIf}
              disabled={loading}
              className="mt-4 bg-green-600 text-white px-6 py-2 rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
            >
              {loading ? 'Calculando...' : 'Re-calcular Modelo'}
            </button>
          </div>
        )}
      </div>

      {resultado && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-semibold mb-4 text-gray-800">Resultados del Análisis What-If</h3>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-gray-100 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Z Original</div>
              <div className="text-xl font-bold">{resultado.Z_original?.toFixed(4)}</div>
            </div>
            <div className="bg-blue-100 p-4 rounded-lg">
              <div className="text-sm text-gray-600">Z Nuevo</div>
              <div className="text-xl font-bold text-blue-600">{resultado.Z_nuevo?.toFixed(4)}</div>
            </div>
            <div className={`p-4 rounded-lg ${resultado.diferencia >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
              <div className="text-sm text-gray-600">Diferencia</div>
              <div className={`text-xl font-bold ${resultado.diferencia >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {resultado.diferencia >= 0 ? '+' : ''}{resultado.diferencia?.toFixed(4)}
                ({resultado.cambio_porcentual?.toFixed(2)}%)
              </div>
            </div>
          </div>

          {resultado.restricciones_afectadas.length > 0 && (
            <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
              <h4 className="font-semibold text-yellow-800 mb-2">Restricciones Afectadas</h4>
              <ul className="list-disc list-inside text-sm text-yellow-700">
                {resultado.restricciones_afectadas.map((r, i) => (
                  <li key={i}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}