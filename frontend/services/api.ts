import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios';
import { ApiResponse, PaginatedResponse, PaginationParams, Token } from '@/types';
import { createAppError, handleError, isAuthError, ErrorCategory, AppError } from '@/utils/errorHandling';
import { jwtDecode } from 'jwt-decode';

// Define API base URL constants
export const API_BASE_URL = '/api/v1'; // Full path with version
export const API_STREAM_URL = '/api/v1'; // Same path for stream URLs

// Create axios instance with base configuration
const api = axios.create({
  headers: {
    'Content-Type': 'application/json'
  }
});

// Helper function to get the correct URL for different types of requests
export const getApiUrl = (path: string, useBaseUrl = true): string => {
  // Create the normalized path (with leading slash but NO trailing slash)
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const cleanPath = normalizedPath.endsWith('/') ? normalizedPath.slice(0, -1) : normalizedPath;
  
  if (useBaseUrl) {
    // Regular API requests through axios - use full API path
    return `${API_BASE_URL}${cleanPath}`;
  } else {
    // Direct requests (like EventSource) - use full API path
    return `${API_STREAM_URL}${cleanPath}`;
  }
};

// Flag to prevent multiple refresh requests
let isRefreshing = false;
// Queue of failed requests to retry after token refresh
let failedQueue: any[] = [];

// Process the queue of failed requests
const processQueue = (error: any = null, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
};

// Function to refresh the token
const refreshToken = async (): Promise<string | null> => {
  try {
    const refreshToken = localStorage.getItem('refreshToken');
    if (!refreshToken) {
      return null;
    }
    
    const refreshUrl = getApiUrl('/auth/refresh');
    console.log('Refreshing token at:', refreshUrl);
    
    const response = await axios.post<Token>(
      refreshUrl,
      { refresh_token: refreshToken },
      { headers: { 'Content-Type': 'application/json' } }
    );
    
    if (response.data) {
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('refreshToken', response.data.refresh_token);
      return response.data.access_token;
    }
    
    return null;
  } catch (error) {
    console.error('Error refreshing token:', error);
    return null;
  }
};

// Check if token is expired
const isTokenExpired = (token: string): boolean => {
  try {
    const decoded: any = jwtDecode(token);
    const currentTime = Date.now() / 1000;
    
    // Add a buffer of 30 seconds to refresh before actual expiration
    return decoded.exp < currentTime + 30;
  } catch (error) {
    return true;
  }
};

// Add request interceptor to add auth token
api.interceptors.request.use(
  async (config) => {
    console.log('API Request:', {
      method: config.method,
      url: config.url,
      baseURL: config.baseURL,
      fullUrl: config.baseURL && config.url ? `${config.baseURL}${config.url}` : 'unknown',
      data: config.data,
      headers: config.headers
    });
    
    const token = localStorage.getItem('token');
    
    if (token) {
      // Check if token is expired and needs refreshing
      if (isTokenExpired(token) && !config.url?.includes('/auth/refresh')) {
        if (!isRefreshing) {
          isRefreshing = true;
          
          const newToken = await refreshToken();
          
          isRefreshing = false;
          
          if (newToken) {
            config.headers.Authorization = `Bearer ${newToken}`;
            processQueue(null, newToken);
          } else {
            processQueue(new Error('Failed to refresh token'));
            // Clear tokens and redirect to login
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
            if (typeof window !== 'undefined') {
              window.location.href = '/login';
            }
          }
        } else {
          // Add request to queue if a refresh is already in progress
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then(token => {
              config.headers.Authorization = `Bearer ${token}`;
              return config;
            })
            .catch(error => {
              return Promise.reject(error);
            });
        }
      } else {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    
    return config;
  },
  (error) => Promise.reject(error)
);

// Add response interceptor to handle errors
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', {
      status: response.status,
      data: response.data,
      headers: response.headers,
      config: {
        method: response.config.method,
        url: response.config.url,
        baseURL: response.config.baseURL,
        fullUrl: response.config.baseURL && response.config.url 
          ? `${response.config.baseURL}${response.config.url}` 
          : 'unknown',
      }
    });
    return response;
  },
  async (error: AxiosError) => {
    console.error('API Error:', {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      config: {
        method: error.config?.method,
        url: error.config?.url,
        baseURL: error.config?.baseURL,
        fullUrl: error.config?.baseURL && error.config?.url 
          ? `${error.config.baseURL}${error.config.url}` 
          : 'unknown',
      }
    });
    
    const originalRequest: any = error.config;
    
    // Handle 401 Unauthorized errors
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Mark the request as retried
      originalRequest._retry = true;
      
      if (!isRefreshing) {
        isRefreshing = true;
        
        try {
          const newToken = await refreshToken();
          
          isRefreshing = false;
          
          if (newToken) {
            // Retry the original request with the new token
            originalRequest.headers.Authorization = `Bearer ${newToken}`;
            processQueue(null, newToken);
            return axios(originalRequest);
          } else {
            processQueue(new Error('Failed to refresh token'));
            // Clear tokens and redirect to login
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
            if (typeof window !== 'undefined') {
              window.location.href = '/login';
            }
          }
        } catch (refreshError) {
          processQueue(refreshError);
          // Clear tokens and redirect to login
          localStorage.removeItem('token');
          localStorage.removeItem('refreshToken');
          if (typeof window !== 'undefined') {
            window.location.href = '/login';
          }
        }
      } else {
        // Add request to queue if a refresh is already in progress
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(axios(originalRequest));
            },
            reject: (err: any) => {
              reject(err);
            }
          });
        });
      }
    }
    
    return Promise.reject(error);
  }
);

// Helper for handling API errors with our centralized error handling utility
const handleApiError = (error: any, apiPath: string): ApiResponse<any> => {
  // Check for network errors
  if (axios.isAxiosError(error) && !error.response) {
    // This is likely a network error (no response from server)
    console.error('Network error detected:', error.message);
    return {
      error: 'Please check your internet connection and try again',
      errorObject: {
        message: error.message,
        category: 'network',
        detail: 'Connection failed',
        source: `API:${apiPath}`,
        timestamp: new Date(),
        originalError: error
      }
    };
  }
  
  const appError = createAppError(error, `API:${apiPath}`, {
    url: apiPath,
    method: error.config?.method,
    data: error.config?.data
  });
  
  // Log the error
  console.error('API Error:', appError);
  
  // Handle authentication errors (token expired or invalid)
  if (isAuthError(appError) && typeof window !== 'undefined') {
    // Don't redirect if we're already on the login page or trying to refresh
    const isLoginPage = window.location.pathname === '/login';
    const isRefreshing = appError.context?.url?.includes('/auth/refresh');
    
    if (!isLoginPage && !isRefreshing) {
      localStorage.removeItem('token');
      localStorage.removeItem('refreshToken');
      window.location.href = '/login';
    }
  }
  
  // Return a standardized error response
  return { 
    error: appError.detail || appError.message,
    errorObject: appError
  };
};

// Generic GET request
export const get = async <T>(
  path: string,
  params?: any,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
    const url = getApiUrl(path);
    
    console.log('GET request details:', {
      url,
      params,
      authToken: localStorage.getItem('token') ? 'Present' : 'Missing',
      config
    });
    
    const response: AxiosResponse<T> = await api.get(url, { ...config, params });
    console.log('GET response status:', response.status);
    return { data: response.data };
  } catch (error) {
    return handleApiError(error, path);
  }
};

  // Generic POST request
export const post = async <T>(
  path: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
    const url = getApiUrl(path);
    
    console.log('POST request details:', {
      url,
      data,
      authToken: localStorage.getItem('token') ? 'Present' : 'Missing',
      config
    });
    
    const response: AxiosResponse<T> = await api.post(url, data, config);
    console.log('POST response:', response.status, response.statusText);
    return { data: response.data };
  } catch (error) {
    return handleApiError(error, path);
  }
};

// Generic PUT request
export const put = async <T>(
  path: string,
  data?: any,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
    const url = getApiUrl(path);
    
    console.log('PUT request details:', {
      url,
      data,
      authToken: localStorage.getItem('token') ? 'Present' : 'Missing',
      config
    });
    
    const response: AxiosResponse<T> = await api.put(url, data, config);
    console.log('PUT response status:', response.status);
    return { data: response.data };
  } catch (error) {
    return handleApiError(error, path);
  }
};

// Generic DELETE request
export const del = async <T>(
  path: string,
  config?: AxiosRequestConfig
): Promise<ApiResponse<T>> => {
  try {
    const url = getApiUrl(path);
    
    console.log('DELETE request details:', {
      url,
      authToken: localStorage.getItem('token') ? 'Present' : 'Missing',
      config
    });
    
    const response: AxiosResponse<T> = await api.delete(url, config);
    console.log('DELETE response status:', response.status);
    return { data: response.data };
  } catch (error) {
    return handleApiError(error, path);
  }
};

// Paginated GET request
export const getPaginated = async <T>(
  path: string,
  params?: PaginationParams & Record<string, any>,
  config?: AxiosRequestConfig
): Promise<ApiResponse<PaginatedResponse<T>>> => {
  try {
    const url = getApiUrl(path);
    console.log('Paginated GET request to:', url);
    const response: AxiosResponse<PaginatedResponse<T>> = await api.get(url, {
      ...config,
      params: {
        ...params,
        page: params?.page || 1,
        size: params?.size || 10,
      },
    });
    return { data: response.data };
  } catch (error) {
    return handleApiError(error, path);
  }
};

// Function to set tokens in storage (localStorage or sessionStorage)
export const setToken = (token: Token, rememberMe = false): void => {
  const storage = rememberMe ? localStorage : sessionStorage;
  storage.setItem('token', token.access_token);
  storage.setItem('refreshToken', token.refresh_token);
  
  // Store the storage preference
  localStorage.setItem('tokenStorage', rememberMe ? 'local' : 'session');
};

// Function to get access token from storage
export const getToken = (): string | null => {
  // Check which storage to use
  const storageType = localStorage.getItem('tokenStorage') || 'local';
  const storage = storageType === 'local' ? localStorage : sessionStorage;
  
  return storage.getItem('token');
};

// Function to get refresh token from storage
export const getRefreshToken = (): string | null => {
  // Check which storage to use
  const storageType = localStorage.getItem('tokenStorage') || 'local';
  const storage = storageType === 'local' ? localStorage : sessionStorage;
  
  return storage.getItem('refreshToken');
};

// Function to remove tokens from storage
export const removeToken = (): void => {
  // Remove from both to be safe
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('refreshToken');
  localStorage.removeItem('tokenStorage');
};

export default api;
