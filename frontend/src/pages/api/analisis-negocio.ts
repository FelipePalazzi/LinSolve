/**
 * analisis-negocio.ts - BFF (Backend for Frontend) para análisis de negocio con IA
 */

import type { APIRoute } from 'astro';
import type { AnalisisSensibilidad, ErrorResponse } from '../../types';

export const POST: APIRoute = async ({ request }) => {
  try {
    const body = await request.json();

    const backendUrl = import.meta.env.PUBLIC_BACKEND_URL || 'http://localhost:8000';

    const response = await fetch(`${backendUrl}/api/analisis-negocio`, {
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
      JSON.stringify(data),
      {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }
    );

  } catch (error) {
    console.error('Error en BFF analisis-negocio:', error);

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