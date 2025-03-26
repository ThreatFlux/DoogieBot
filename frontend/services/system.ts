import { get, put } from './api';
import { ApiResponse } from '@/types';

export type LogLevel = 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL';

export interface SystemSettings {
  disable_sql_logs?: boolean;
  log_level?: LogLevel;
}

export interface SystemSettingsResponse {
  settings: SystemSettings;
  message: string;
}

/**
 * Get current system settings
 */
export const getSystemSettings = async (): Promise<ApiResponse<SystemSettingsResponse>> => {
  return await get<SystemSettingsResponse>('/system');
};

/**
 * Update system settings
 */
export const updateSystemSettings = async (
  settings: SystemSettings
): Promise<ApiResponse<SystemSettingsResponse>> => {
  return await put<SystemSettingsResponse>('/system', settings);
};