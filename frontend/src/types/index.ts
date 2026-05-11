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

export interface ModeloPrimalRequest {
  modelo_primal: ModeloPrimal;
  configuracion?: Configuracion;
}

export interface ExtraerResponse {
  planteo: PlanteoValidacion;
  modelo_primal: ModeloPrimal;
}

export interface ErrorResponse {
  codigo: number;
  error: string;
  detalle: string;
  request_id?: string;
}

export type TabActiva = 'validacion' | 'primal' | 'dual' | 'sensibilidad' | 'whatif' | 'interpretacion';

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
  descripcion_variables?: Record<string, string>;
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
  rango_rhs: RangoOptimo[];
  costo_reducido_interpretacion: string;
  holguras_interpretacion: string;
  relacion_Z_equals_W: string;
}

export type EstadoSolucion = 'OPTIMO' | 'INFEASIBLE' | 'NO_ACOTADO' | 'ERROR';

export interface TableauColumna {
  nombre: string;
  ck: number;
  tipo: 'variable_original' | 'slack' | 'artificial';
}

export interface TableauIteracion {
  iteracion: number;
  nombre_objetivo: string;
  tipo_optimizacion: 'max' | 'min';
  nombres_columnas: string[];
  nombres_vars_originales: string[];
  nombres_slack: string[];
  ck: number[];
  variables_basicas: string[];
  rhs: number[];
  fila_z: number[];
  matriz: number[][];
  num_filas: number;
  num_columnas: number;
}

export interface TableauRespuesta {
  primal_inicial: TableauIteracion;
  primal_optimo: TableauIteracion;
  dual_optimo: TableauIteracion;
  Z_valor: number;
  W_valor: number;
}

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

export interface TooltipData {
  titulo: string;
  contenido: string;
}