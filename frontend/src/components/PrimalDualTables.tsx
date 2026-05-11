/**
 * PrimalDualTables.tsx - Componente de visualización Primal-Dual con Tableaux Simplex
 * Renderiza los tableaux (inicial y óptimo), resultados y análisis de sensibilidad
 * según la metodología de Hillier & Lieberman.
 */

import React from 'react';
import type {
  SolveResponse,
  TabActiva,
  ResultadoVariable,
  RestriccionResultado,
  TooltipData,
  TableauIteracion
} from '../types';

interface Props {
  response: SolveResponse;
  tabActiva: TabActiva;
}

interface TooltipState {
  visible: boolean;
  x: number;
  y: number;
  data: TooltipData | null;
}

export function PrimalDualTables({ response, tabActiva }: Props) {
  const [tooltip, setTooltip] = React.useState<TooltipState>({
    visible: false,
    x: 0,
    y: 0,
    data: null
  });

  const showTooltip = (event: React.MouseEvent, data: TooltipData) => {
    const rect = (event.target as HTMLElement).getBoundingClientRect();
    setTooltip({
      visible: true,
      x: rect.left + rect.width / 2,
      y: rect.top,
      data
    });
  };

  const hideTooltip = () => {
    setTooltip({ visible: false, x: 0, y: 0, data: null });
  };

  const renderTooltip = () => {
    if (!tooltip.visible || !tooltip.data) return null;
    return (
      <div
        className="fixed z-50 bg-gray-900 text-white p-3 rounded-lg shadow-xl max-w-xs text-sm pointer-events-none"
        style={{
          left: `${tooltip.x}px`,
          top: `${tooltip.y - 10}px`,
          transform: 'translate(-50%, -100%)'
        }}
      >
        <div className="font-semibold text-blue-300 mb-1">{tooltip.data.titulo}</div>
        <div>{tooltip.data.contenido}</div>
      </div>
    );
  };

  const getHolguraTooltip = (resultado: RestriccionResultado) => ({
    titulo: `Holgura ${resultado.nombre}`,
    contenido: resultado.activa
      ? `Restricción ACTIVA: holgura = 0. Este recurso está siendo utilizado completamente. Precio sombra: ${resultado.precio_sombra}`
      : `Restricción INACTIVA: holgura = ${resultado.holgura}. Este recurso tiene ${resultado.holgura} unidades no utilizadas.`
  });

  const getVariableTooltip = (variable: ResultadoVariable) => ({
    titulo: `Variable ${variable.nombre}`,
    contenido: variable.en_base
      ? `${variable.descripcion || variable.nombre} está en la base con valor ${variable.valor.toFixed(2)}. Costo reducido = 0 (solución óptima).`
      : `${variable.descripcion || variable.nombre} NO está en la base (valor = 0). Costo reducido: ${variable.costo_reducido?.toFixed(2) || 'N/A'}. Para que entre a la base, su coeficiente debe mejorar en al menos ${variable.costo_reducido?.toFixed(2) || 'N/A'}.`
  });

  const renderTableau = (tableau: TableauIteracion, titulo: string) => {
    if (!tableau || !tableau.matriz || tableau.matriz.length === 0) {
      return <p className="text-gray-500">Tableau no disponible</p>;
    }

    const todasColumnas = tableau.nombres_columnas || [];
    const numCols = tableau.num_columnas || todasColumnas.length;
    const esInicial = tableau.iteracion === 0;
    const ckInicial = esInicial ? Array(tableau.matriz.length).fill(0) : tableau.ck;

    return (
      <div className="overflow-x-auto">
        <h4 className="font-medium text-gray-700 mb-2">{titulo}</h4>

        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-blue-100">
              <th className="border p-2 text-center bg-blue-200">ck</th>
              <th className="border p-2 text-center bg-blue-200">xk</th>
              <th className="border p-2 text-center bg-blue-200">bk</th>
              {todasColumnas.map((col, idx) => (
                <th key={idx} className="border p-2 text-center bg-blue-200">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableau.matriz.map((fila, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="border p-2 text-center font-mono bg-gray-50">
                  {ckInicial[i]?.toFixed(2) || '0.00'}
                </td>
                <td className="border p-2 text-center font-mono font-semibold bg-blue-50">
                  {tableau.variables_basicas[i] || `R${i + 1}`}
                </td>
                <td className="border p-2 text-center font-mono bg-yellow-50">
                  {tableau.rhs[i]?.toFixed(4) || '0.00'}
                </td>
                {fila.map((val, j) => (
                  <td key={j} className="border p-2 text-center font-mono">
                    {val?.toFixed(4) || '0.00'}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="bg-gray-200 font-bold">
              <td className="border p-2"></td>
              <td className="border p-2 text-center font-mono">Z</td>
              <td className="border p-2 text-center font-mono">
                {response.Z_valor?.toFixed(4) || '0.00'}
              </td>
              {tableau.fila_z.map((zj_cj, j) => (
                <td key={j} className={`border p-2 text-center font-mono ${
                  zj_cj >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {zj_cj?.toFixed(4) || '0.00'}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    );
  };

  const renderTableauDual = (tableau: TableauIteracion, titulo: string) => {
    if (!tableau || !tableau.matriz || tableau.matriz.length === 0) {
      return <p className="text-gray-500">Tableau dual no disponible</p>;
    }

    const todasColumnas = tableau.nombres_columnas || [];
    const numCols = tableau.num_columnas || todasColumnas.length;

    return (
      <div className="overflow-x-auto">
        <h4 className="font-medium text-gray-700 mb-2">{titulo}</h4>
        <p className="text-xs text-purple-500 mb-2 font-semibold">Modelo Dual - Variables Y</p>

        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="bg-purple-100">
              <th className="border p-2 text-center bg-purple-200">bk</th>
              <th className="border p-2 text-center bg-purple-200">yk</th>
              <th className="border p-2 text-center bg-purple-200">ck</th>
              {todasColumnas.map((col, idx) => (
                <th key={idx} className="border p-2 text-center bg-purple-200">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tableau.matriz.map((fila, i) => (
              <tr key={i} className="hover:bg-gray-50">
                <td className="border p-2 text-center font-mono bg-yellow-50">
                  {tableau.rhs[i]?.toFixed(2) || '0.00'}
                </td>
                <td className="border p-2 text-center font-mono font-semibold bg-purple-50">
                  {tableau.variables_basicas[i] || `y${i + 1}`}
                </td>
                <td className="border p-2 text-center font-mono bg-gray-50">
                  {tableau.ck[i]?.toFixed(2) || '0.00'}
                </td>
                {fila.map((val, j) => (
                  <td key={j} className="border p-2 text-center font-mono">
                    {val?.toFixed(4) || '0.00'}
                  </td>
                ))}
              </tr>
            ))}
            <tr className="bg-gray-200 font-bold">
              <td className="border p-2 text-center font-mono">
                {response.W_valor?.toFixed(4) || '0.00'}
              </td>
              <td className="border p-2 text-center font-mono">W</td>
              <td className="border p-2"></td>
              {tableau.fila_z.map((zj_cj, j) => (
                <td key={j} className={`border p-2 text-center font-mono ${
                  zj_cj >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {zj_cj?.toFixed(4) || '0.00'}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>
    );
  };

  const renderTablaPrimal = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-gray-800">Modelo Primal - Tableau Óptimo</h3>
          <div className="bg-green-600 text-white px-4 py-2 rounded-lg font-bold text-lg">
            Z = {response.Z_valor?.toFixed(4) || '0.00'}
          </div>
        </div>

        {response.tableaux?.primal_optimo && (
          renderTableau(response.tableaux.primal_optimo, 'Tableau Final (Primal)')
        )}

        <div className="mt-6">
          <h4 className="font-medium text-gray-700 mb-2">Resumen de Variables</h4>
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Variable</th>
                <th className="border p-2 text-right">Valor Óptimo</th>
                <th className="border p-2 text-right">Costo Reducido</th>
                <th className="border p-2 text-center">¿En Base?</th>
              </tr>
            </thead>
            <tbody>
              {response.resultado_variables.map((var_) => {
                return (
                  <tr key={var_.nombre} className="hover:bg-gray-50">
                    <td className="border p-2">
                      <div className="font-mono">{var_.nombre}</div>
                      {var_.descripcion && (
                        <div className="text-xs text-gray-500">{var_.descripcion}</div>
                      )}
                    </td>
                    <td className="border p-2 text-right font-mono">{var_.valor.toFixed(2)}</td>
                    <td className="border p-2 text-right">
                      <span
                        className="cursor-help underline decoration-dotted"
                        onMouseEnter={(e) => showTooltip(e, getVariableTooltip(var_))}
                        onMouseLeave={hideTooltip}
                      >
                        {var_.costo_reducido}
                      </span>
                    </td>
                    <td className="border p-2 text-center">
                      <span className={`px-2 py-1 rounded text-xs ${var_.en_base ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
                        {var_.en_base ? 'SÍ' : 'NO'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-6">
          <h4 className="font-medium text-gray-700 mb-2">Restricciones</h4>
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Restricción</th>
                <th className="border p-2 text-right">RHS</th>
                <th className="border p-2 text-right">Holgura</th>
                <th className="border p-2 text-right">Precio Sombra</th>
                <th className="border p-2 text-center">Estado</th>
              </tr>
            </thead>
            <tbody>
              {response.resultado_restricciones.map((restr) => (
                <tr key={restr.nombre} className="hover:bg-gray-50">
                  <td className="border p-2 font-mono">{restr.nombre}</td>
                  <td className="border p-2 text-right font-mono">{restr.RHS_original}</td>
                  <td className="border p-2 text-right">
                    <span
                      className="cursor-help underline decoration-dotted"
                      onMouseEnter={(e) => showTooltip(e, getHolguraTooltip(restr))}
                      onMouseLeave={hideTooltip}
                    >
                      {restr.holgura?.toFixed(4)}
                    </span>
                  </td>
                  <td className="border p-2 text-right font-mono">{restr.precio_sombra?.toFixed(4)}</td>
                  <td className="border p-2 text-center">
                    <span className={`px-2 py-1 rounded text-xs ${restr.activa ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}`}>
                      {restr.activa ? 'ACTIVA' : 'INACTIVA'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );

  const renderTablaDual = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-semibold text-gray-800">Modelo Dual - Tableau Óptimo</h3>
          <div className="bg-purple-600 text-white px-4 py-2 rounded-lg font-bold text-lg">
            W = {response.W_valor?.toFixed(4) || '0.00'}
          </div>
        </div>

        {response.tableaux?.dual_optimo && (
          renderTableauDual(response.tableaux.dual_optimo, 'Tableau Final (Dual)')
        )}

        <div className="mt-6 bg-yellow-50 p-4 rounded-lg border border-yellow-200">
          <h4 className="font-semibold text-yellow-800 mb-2">Verificación: Z = W</h4>
          <p className="text-yellow-700">
            Z (Primal) = {response.Z_valor?.toFixed(4)} | W (Dual) = {response.W_valor?.toFixed(4)}
            {Math.abs((response.Z_valor || 0) - (response.W_valor || 0)) < 0.0001 && (
              <span className="text-green-600 font-bold ml-2"> ✓ Verificado</span>
            )}
          </p>
          <p className="text-sm text-yellow-600 mt-1">
            Por el Teorema de Dualidad Fuerte, ambos valores deben ser iguales en la solución óptima.
          </p>
        </div>
      </div>
    </div>
  );

  const renderValidacion = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-800">Tableau Inicial (Validación)</h3>
        <p className="text-sm text-gray-600 mb-4">
          Este es el tableau de la iteración 0, antes de aplicar el método Simplex.
          Las variables de holgura (S1, S2, ...) forman la base inicial.
        </p>

        {response.tableaux?.primal_inicial && (
          renderTableau(response.tableaux.primal_inicial, 'Tableau Iteración 0')
        )}

        <div className="mt-6 bg-blue-50 p-4 rounded-lg border border-blue-200">
          <h4 className="font-semibold text-blue-800 mb-2">Interpretación</h4>
          <p className="text-sm text-blue-700">
            En la iteración 0, las variables de decisión (x1, x2, ...) tienen valores 0
            y las variables de holgura (S1, S2, ...) tienen valores iguales a los RHS.
            La fila Zj-Cj muestra los coeficientes de la función objetivo.
          </p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-800">Planteo del Problema</h3>
        <div className="bg-gray-50 p-4 rounded-lg">
          <p className="font-mono font-semibold text-lg">{response.modelo_primal_valido.funcion_objetivo_texto}</p>
          <ul className="mt-2 space-y-1">
            {response.modelo_primal_valido.restricciones_texto.map((r, i) => (
              <li key={i} className="font-mono text-sm">{r}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );

  const renderAnalisisSensibilidad = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-xl font-semibold mb-4 text-gray-800">Análisis de Sensibilidad</h3>

        <div className="mb-6">
          <h4 className="font-medium text-gray-700 mb-2">Rangos de Optimalidad</h4>
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-gray-100">
                <th className="border p-2 text-left">Variable</th>
                <th className="border p-2 text-right">Mínimo</th>
                <th className="border p-2 text-right">Máximo</th>
                <th className="border p-2 text-left">Interpretación</th>
              </tr>
            </thead>
            <tbody>
              {response.analisis_sensibilidad.rango_optimos.map((rango) => (
                <tr key={rango.variable} className="hover:bg-gray-50">
                  <td className="border p-2 font-mono">{rango.variable}</td>
                  <td className="border p-2 text-right font-mono">{rango.min}</td>
                  <td className="border p-2 text-right font-mono">
                    {rango.max === Infinity ? '∞' : rango.max}
                  </td>
                  <td className="border p-2 text-sm text-gray-600">
                    Mientras el coeficiente de {rango.variable} esté entre {rango.min} y {rango.max === Infinity ? '∞' : rango.max}, la solución óptima no cambia.
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <h4 className="font-semibold text-green-800 mb-2">Costos Reducidos</h4>
            <p className="text-sm text-green-700">
              {response.analisis_sensibilidad.costo_reducido_interpretacion}
            </p>
          </div>

          <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
            <h4 className="font-semibold text-purple-800 mb-2">Holguras</h4>
            <p className="text-sm text-purple-700">
              {response.analisis_sensibilidad.holguras_interpretacion}
            </p>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="relative">
      {renderTooltip()}

      {tabActiva === 'validacion' && renderValidacion()}
      {tabActiva === 'primal' && renderTablaPrimal()}
      {tabActiva === 'dual' && renderTablaDual()}
      {tabActiva === 'sensibilidad' && renderAnalisisSensibilidad()}
    </div>
  );
}