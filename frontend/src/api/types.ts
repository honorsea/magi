export interface ConfigState {
  cw_worker_id: string;
  mw_worker_id: string;
  robot_speed_factor: number;
  takt_time_seconds: number;
  buffer_capacity: number;
  simulation_speed_factor: number;
  inter_arrival_jitter_cv: number;
}

export interface SimulationSession {
  id: string;
  label: string;
  mode: string;
  status: 'queued' | 'running' | 'paused' | 'completed' | 'error';
  config: ConfigState;
  result: Record<string, any> | null;
  error_msg: string | null;
  created_at: number;
  started_at: number | null;
  completed_at: number | null;
}

export interface Settings {
  [key: string]: any;
}
