// types/index.ts - Interfaces TypeScript para LinSolve
// Sincronizado con los modelos Pydantic del backend

export interface Configuracion {
  tolerancia: number;
  tiempo_maximo_seg: number;
  presicion: number;
}

export interface SolveRequest {
  problema_texto: string;
  configuracion?: Configuracion;
}

export interface CoeficientesRestriccion {
  variables: Record<string, number>;
}

export interface Restriccion {
  nombre: string;
  coeficientes: CoeficientesRestriccion;
  tipo: '<=' | '>=' | '=';
  rhs: number;
  nombre_variable_holgura?: string;
}

export interface ModeloPrimal {
  tipo_optimizacion: 'max' | 'min';
  funcion_objetivo: Record<string, number>;
  restricciones: Restriccion[];
  nombre_variable_objetivo: string;
}

export interface PlanteoValidacion {
  funcion_objetivo_texto: string;
  restricciones_texto: string[];
  variables_texto: string[];
  descripcion_variables: Record<string, string>;
}

export interface ResultadoVariable {
  nombre: string;
  descripcion?: string;
  valor: number;
  en_base: boolean;
  holgura?: number;
  precio_sombra?: number;
  costo_reducido?: number;
}

export interface RestriccionResultado {
  nombre: string;
  tipo: string;
  RHS_original: number;
  RHS_actualizado?: number;
  holgura: number;
  precio_sombra: number;
  activa: boolean;
}

export interface RestriccionDual {
  nombre: string;
  coeficientes: Record<string, number>;
  tipo: '>=' | '<=' | '=';
  rhs: number;
}

export interface ModeloDualExplícito {
  tipo_optimizacion: 'max' | 'min';
  funcion_objetivo: string;
  variable_objetivo: string;
  restricciones: RestriccionDual[];
  interpretacion: string;
}

export interface RangoOptimo {
  variable: string;
  min: number;
  max: number;
}

export interface AnalisisSensibilidad {
  rango_optimos: RangoOptimo[];
  costo_reducido_interpretacion: string;
  holguras_interpretacion: string;
  relacion_Z_equals_W: string;
}

export type EstadoSolucion = 'OPTIMO' | 'INFEASIBLE' | 'NO_ACOTADO' | 'ERROR';

export interface SolveResponse {
  estado: EstadoSolucion;
  modelo_primal_valido: PlanteoValidacion;
  modelo_primal?: ModeloPrimal;
  resultado_variables: ResultadoVariable[];
  resultado_restricciones: RestriccionResultado[];
  modelo_dual: ModeloDualExplícito;
  analisis_sensibilidad: AnalisisSensibilidad;
  tiempo_resolucion_ms: number;
  request_id: string;
  Z_valor: number;
  W_valor: number;
  tableaux?: TableauRespuesta;
}

export interface WhatIfModificacion {
  tipo: 'coef_objetivo' | 'rhs' | 'coef_tecnologico' | 'nueva_restriccion' | 'nueva_actividad' | 'demanda_min';
  variable: string;
  restriccion?: string;
  valor_nuevo: number;
  restriccion_nueva?: Restriccion;
  datos_actividad?: {
    precio: number;
    coeficientes: Record<string, number>;
  };
}

export interface WhatIfRequest {
  modelo_original: ModeloPrimal;
  modificaciones: WhatIfModificacion[];
}

export interface WhatIfResponse {
  Z_original: number;
  Z_nuevo: number;
  diferencia: number;
  cambio_porcentual: number;
  restricciones_afectadas: string[];
  tableau_optimo_nuevo?: TableauIteracion;
  dual_optimo_nuevo?: TableauIteracion;
}