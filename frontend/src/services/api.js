/**
 * API 서비스 - 백엔드 최적화된 엔드포인트 연동
 * 다이얼로그 기반 UI를 위한 API 클라이언트
 */

import axios from 'axios';

// API 기본 설정
const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8001';

// Axios 인스턴스 생성
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 요청 인터셉터 - JWT 토큰 자동 첨부
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 응답 인터셉터 - 토큰 만료 처리
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/api/auth/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem('access_token', access);

          originalRequest.headers.Authorization = `Bearer ${access}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

// ======================
// 인증 관련 API
// ======================

export const authAPI = {
  // 로그인
  login: async (username, password) => {
    const response = await apiClient.post('/api/auth/login/', {
      username,
      password,
    });
    return response.data;
  },

  // 로그아웃
  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await apiClient.post('/api/auth/logout/', {
          refresh_token: refreshToken,
        });
      } catch (error) {
        console.error('로그아웃 API 오류:', error);
      }
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  },

  // 사용자 정보 조회
  getUserInfo: async () => {
    const response = await apiClient.get('/api/auth/token-info/');
    return response.data;
  },
};

// ======================
// 정책 관리 API
// ======================

export const policyAPI = {
  // 정책 목록 조회 (DRF 표준)
  getPolicies: async (params = {}) => {
    const response = await apiClient.get('/api/policies/', { params });
    return response.data;
  },

  // 정책 상세 조회
  getPolicy: async (id) => {
    const response = await apiClient.get(`/api/policies/${id}/`);
    return response.data;
  },

  // 정책 생성
  createPolicy: async (data) => {
    const response = await apiClient.post('/api/policies/', data);
    return response.data;
  },

  // 정책 수정
  updatePolicy: async (id, data) => {
    const response = await apiClient.put(`/api/policies/${id}/`, data);
    return response.data;
  },

  // 정책 삭제
  deletePolicy: async (id) => {
    const response = await apiClient.delete(`/api/policies/${id}/`);
    return response.data;
  },

  // 대시보드 데이터 (정책 통계가 필요하면 /api/policies/에 별도 엔드포인트 구성 예정)
  getDashboard: async () => {
    const response = await apiClient.get('/api/dashboard/stats/');
    return response.data;
  },

  // 배정된 업체 목록 조회
  getAssignedCompanies: async (policyId) => {
    const response = await apiClient.get(`/api/policies/${policyId}/assignments/`);
    return response.data;
  },

  // 업체 배정
  assignCompanies: async (policyId, data) => {
    const response = await apiClient.post(`/api/policies/${policyId}/assignments/`, data);
    return response.data;
  },

  // 업체 배정 해제
  unassignCompanies: async (policyId, companyIds) => {
    const response = await apiClient.delete(`/api/policies/${policyId}/assignments/`, { data: { company_ids: companyIds } });
    return response.data;
  },

  // 주문서 양식 조회
  getOrderForm: async (policyId) => {
    const response = await apiClient.get(`/api/policies/${policyId}/form-template/`);
    return response.data;
  },

  // 주문서 양식 생성/수정
  updateOrderForm: async (policyId, data) => {
    const response = await apiClient.put(`/api/policies/${policyId}/form-template/`, data);
    return response.data;
  },

  // 리베이트 매트릭스 조회
  getRebateMatrix: async (policyId) => {
    const response = await apiClient.get(`/api/policies/${policyId}/rebate-matrix/`);
    return response.data;
  },

  // 리베이트 매트릭스 수정
  updateRebateMatrix: async (policyId, data) => {
    const response = await apiClient.put(`/api/policies/${policyId}/rebate-matrix/`, data);
    return response.data;
  },
};

// ======================
// 업체 관리 API
// ======================

export const companyAPI = {
  // 업체 목록 조회 (배정용)
  getCompaniesForAssignment: async (params = {}) => {
    const response = await apiClient.get('/api/companies/', {
      params,
    });
    return response.data;
  },

  // 업체 목록 조회 (전체)
  getCompanies: async (params = {}) => {
    const response = await apiClient.get('/api/companies/', {
      params,
    });
    return response.data;
  },

  // 업체 상세 조회
  getCompany: async (id) => {
    const response = await apiClient.get(`/api/companies/${id}/`);
    return response.data;
  },

  // 업체 생성
  createCompany: async (data) => {
    const response = await apiClient.post('/api/companies/', data);
    return response.data;
  },

  // 업체 수정
  updateCompany: async (id, data) => {
    const response = await apiClient.put(`/api/companies/${id}/`, data);
    return response.data;
  },

  // 업체 삭제
  deleteCompany: async (id) => {
    const response = await apiClient.delete(`/api/companies/${id}/`);
    return response.data;
  },

  // 업체 사용자 목록
  getCompanyUsers: async (params = {}) => {
    const response = await apiClient.get('/api/companies/users/', {
      params,
    });
    return response.data;
  },

  // 사용자 승인
  approveUser: async (userId) => {
    const response = await apiClient.post(`/api/companies/users/${userId}/approve/`);
    return response.data;
  },

  // 사용자 거부
  rejectUser: async (userId) => {
    const response = await apiClient.post(`/api/companies/users/${userId}/reject/`);
    return response.data;
  },
};

// ======================
// 주문 관리 API
// ======================

export const orderAPI = {
  // 주문 목록 조회
  getOrders: async (params = {}) => {
    const response = await apiClient.get('/api/orders/', {
      params,
    });
    return response.data;
  },

  // 주문 상세 조회
  getOrder: async (id) => {
    const response = await apiClient.get(`/api/orders/${id}/`);
    return response.data;
  },

  // 주문 생성
  createOrder: async (data) => {
    const response = await apiClient.post('/api/orders/', data);
    return response.data;
  },

  // 주문 수정
  updateOrder: async (id, data) => {
    const response = await apiClient.put(`/api/orders/${id}/`, data);
    return response.data;
  },

  // 주문 승인
  approveOrder: async (id) => {
    const response = await apiClient.post(`/api/orders/${id}/approve/`);
    return response.data;
  },

  // 주문 거부
  rejectOrder: async (id, reason) => {
    const response = await apiClient.post(`/api/orders/${id}/reject/`, { reason });
    return response.data;
  },

  // 주문 통계 조회
  getOrderStats: async () => {
    const response = await apiClient.get('/api/orders/stats/');
    return response.data;
  },
};

// ======================
// 정산 관리 API
// ======================

export const settlementAPI = {
  // 정산 목록 조회
  getSettlements: async (params = {}) => {
    const response = await apiClient.get('/api/settlements/', {
      params,
    });
    return response.data;
  },

  // 정산 상세 조회
  getSettlement: async (id) => {
    const response = await apiClient.get(`/api/settlements/${id}/`);
    return response.data;
  },

  // 정산 처리
  processSettlement: async (id) => {
    const response = await apiClient.post(`/api/settlements/${id}/process/`);
    return response.data;
  },

  // 엑셀 내보내기 - 기존 API (파라미터 확장)
  exportExcel: async (startDate, endDate, status, dateColumn) => {
    const params = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    if (status) params.status = status;
    if (dateColumn) params.date_column = dateColumn;
    
    const response = await apiClient.get('/api/settlements/export_excel/', {
      params,
      responseType: 'blob'
    });
    return response.data;
  },

  // 고급 엑셀 내보내기 - 동적 필터 적용
  exportWithFilters: async (filters = {}, exportType = 'auto') => {
    const response = await apiClient.post('/api/settlements/excel/export_with_filters/', {
      filters,
      export_type: exportType
    }, {
      responseType: 'blob'
    });
    return response;
  },

  // 간단한 엑셀 내보내기
  exportSimple: async (params = {}) => {
    const response = await apiClient.get('/api/settlements/excel/export_simple/', {
      params,
      responseType: 'blob'
    });
    return response;
  },

  // 사용 가능한 엑셀 템플릿 조회
  getExportTemplates: async () => {
    const response = await apiClient.get('/api/settlements/excel/export_templates/');
    return response.data;
  },

  // 데이터 미리보기
  previewData: async (filters = {}, previewLimit = 100) => {
    const response = await apiClient.post('/api/settlements/excel/preview_data/', {
      filters,
      preview_limit: previewLimit
    });
    return response.data;
  },

  // 동적 필터링 - 필터 옵션 조회
  getFilterOptions: async () => {
    const response = await apiClient.get('/api/settlements/dynamic/filter_options/');
    return response.data;
  },

  // 동적 필터링 - 필터 적용
  applyFilters: async (filters = {}, page = 1, pageSize = 20) => {
    const response = await apiClient.post('/api/settlements/dynamic/apply_filters/', {
      filters,
      page,
      page_size: pageSize
    });
    return response.data;
  },

  // 요약 통계 조회
  getSummaryStats: async (params = {}) => {
    const response = await apiClient.get('/api/settlements/dynamic/summary_stats/', {
      params
    });
    return response.data;
  }
};

// ======================
// 대시보드 API
// ======================

export const dashboardAPI = {
  // 통계 정보
  getStats: async () => {
    const response = await apiClient.get('/api/dashboard/stats/');
    return response.data;
  },

  // 최근 활동
  getActivities: async () => {
    const response = await apiClient.get('/api/dashboard/activities/');
    return response.data;
  },

  // 본사용 정산 대시보드
  getHeadquartersDashboard: async (params = {}) => {
    const response = await apiClient.get('/api/settlements/dashboard/headquarters/', {
      params,
    });
    return response.data;
  },

  // 협력사용 정산 대시보드
  getAgencyDashboard: async (params = {}) => {
    const response = await apiClient.get('/api/settlements/dashboard/agency/', {
      params,
    });
    return response.data;
  },

  // 판매점용 정산 대시보드
  getRetailDashboard: async (params = {}) => {
    const response = await apiClient.get('/api/settlements/dashboard/retail/', {
      params,
    });
    return response.data;
  },

  // 정산 분석 대시보드
  getAnalyticsDashboard: async (params = {}) => {
    const response = await apiClient.get('/api/settlements/dashboard/analytics/', {
      params,
    });
    return response.data;
  },
};

// ======================
// 유틸리티 함수
// ======================

export const handleAPIError = (error) => {
  if (error.response?.data?.error) {
    return error.response.data.error;
  }
  if (error.response?.data?.message) {
    return error.response.data.message;
  }
  if (error.message) {
    return error.message;
  }
  return '알 수 없는 오류가 발생했습니다.';
};

// 기본 API 요청 함수들
export const get = async (endpoint, params = {}) => {
  try {
    const response = await apiClient.get(endpoint, { params });
    return { success: true, data: response.data, message: null };
  } catch (error) {
    console.error(`API GET 오류 (${endpoint}):`, error);
    return { success: false, data: null, message: handleAPIError(error) };
  }
};

export const post = async (endpoint, data = {}) => {
  try {
    const response = await apiClient.post(endpoint, data);
    return { success: true, data: response.data, message: null };
  } catch (error) {
    console.error(`API POST 오류 (${endpoint}):`, error);
    return { success: false, data: null, message: handleAPIError(error) };
  }
};

export const put = async (endpoint, data = {}) => {
  try {
    const response = await apiClient.put(endpoint, data);
    return { success: true, data: response.data, message: null };
  } catch (error) {
    console.error(`API PUT 오류 (${endpoint}):`, error);
    return { success: false, data: null, message: handleAPIError(error) };
  }
};

export const del = async (endpoint, data = {}) => {
  try {
    const response = await apiClient.delete(endpoint, { data });
    return { success: true, data: response.data, message: null };
  } catch (error) {
    console.error(`API DELETE 오류 (${endpoint}):`, error);
    return { success: false, data: null, message: handleAPIError(error) };
  }
};

// 기본 내보내기
export default apiClient;