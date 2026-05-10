/**
 * solve.ts - BFF (Backend for Frontend) en Astro
 * Protege las variables de entorno y orquesta la comunicación con FastAPI
 */

import type { APIRoute } from 'astro';
import type { SolveRequest, SolveResponse, ErrorResponse } from '../../types';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body: SolveRequest = await request.json();

    if (!body.problema_texto || typeof body.problema_texto !== 'string') {
      return new Response(
        JSON.stringify({
          codigo: 400,
          error: 'BAD_REQUEST',
          detalle: 'El campo problema_texto es requerido y debe ser string'
        } as ErrorResponse),
        {
          status: 400,
          headers: { 'Content-Type': 'application/json' }
        }
      );
    }

    const backendUrl = import.meta.env.PUBLIC_BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/solve`, {
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
    console.error('Error en BFF solve:', error);

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