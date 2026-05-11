/**
 * resolve.ts - BFF (Backend for Frontend) para resolución de modelos
 * Recibe modelo ya extraído y lo envía al solver
 */

import type { APIRoute } from 'astro';
import type { ModeloPrimalRequest, SolveResponse, ErrorResponse } from '../../types';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body: ModeloPrimalRequest = await request.json();

    if (!body.modelo_primal) {
      return new Response(
        JSON.stringify({
          codigo: 400,
          error: 'BAD_REQUEST',
          detalle: 'El campo modelo_primal es requerido'
        } as ErrorResponse),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    const backendUrl = import.meta.env.PUBLIC_BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/resolve`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': crypto.randomUUID()
      },
      body: JSON.stringify(body)
    });

    const data = await response.json();

    if (!response.ok) {
      const errorDetail = data.detail || data;
      return new Response(
        JSON.stringify({
          codigo: errorDetail.codigo || response.status,
          error: errorDetail.error || 'ERROR',
          detalle: errorDetail.detalle || 'Error desconocido',
          request_id: errorDetail.request_id
        } as ErrorResponse),
        {
          status: response.status,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    return new Response(
      JSON.stringify(data as SolveResponse),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }
    );

  } catch (error) {
    console.error('Error en BFF resolve:', error);

    return new Response(
      JSON.stringify({
        codigo: 500,
        error: 'INTERNAL_ERROR',
        detalle: error instanceof Error ? error.message : 'Error interno del BFF'
      } as ErrorResponse),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
};

export const config = {
  runtime: 'edge'
};