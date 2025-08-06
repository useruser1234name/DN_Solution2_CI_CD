import axios from 'axios';

const API_BASE_URL = 'http://localhost:8001/api';

console.log('[API Service] 초기화 - API_BASE_URL:', API_BASE_URL);

// axios 인스턴스 생성
const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 10000,
    headers: {
        'Content-Type': 'application/json',
    },
    withCredentials: false, // JWT는 쿠키 필요 없음
});

// 요청 인터셉터 - 로깅 추가
api.interceptors.request.use(
    (config) => {
        console.log(`[API 요청] ${config.method?.toUpperCase()} ${config.url}`);
        console.log('[API 요청 헤더]', config.headers);
        if (config.data) {
            console.log('[API 요청 데이터]', config.data);
        }
        // CSRF 토큰 관련 코드 제거
        // 인증 토큰이 있으면 헤더에 추가
        const token = localStorage.getItem('authToken');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
            console.log('[API 요청] 인증 토큰 추가됨');
        } else {
            console.log('[API 요청] 인증 토큰 없음');
        }
        return config;
    },
    (error) => {
        console.error('[API 요청 오류]', error);
        return Promise.reject(error);
    }
);

// 응답 인터셉터 - 로깅 추가
api.interceptors.response.use(
    (response) => {
        console.log(`[API 응답 성공] ${response.config.method?.toUpperCase()} ${response.config.url}`);
        console.log('[API 응답 상태]', response.status);
        console.log('[API 응답 헤더]', response.headers);
        console.log('[API 응답 데이터]', response.data);
        return response;
    },
    (error) => {
        console.error(`[API 응답 오류] ${error.config?.method?.toUpperCase()} ${error.config?.url}`);
        console.error('[API 오류 상세]', {
            status: error.response?.status,
            statusText: error.response?.statusText,
            data: error.response?.data,
            message: error.message,
            config: error.config
        });
        
        // 401 오류 시 처리 - 로그인 페이지에서는 리다이렉트하지 않음
        if (error.response?.status === 401) {
            console.log('[API 오류] 401 인증 오류');
            // 현재 경로가 로그인 페이지가 아닐 때만 리다이렉트
            if (!window.location.pathname.includes('/login')) {
                console.log('[API 오류] 로그인 페이지로 리다이렉트');
                localStorage.removeItem('authToken');
                localStorage.removeItem('user');
                // window.location.href = '/login'; // 무한 루프 방지를 위해 주석 처리
            }
        }
        
        return Promise.reject(error);
    }
);

// API 함수들
export const get = async (endpoint) => {
    try {
        console.log(`[API GET 요청] ${endpoint}`);
        const response = await api.get(endpoint);
        console.log(`[API GET 성공] ${endpoint}`, response.data);
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        console.error(`[API GET 실패] ${endpoint}`, error);
        return {
            success: false,
            message: error.response?.data?.message || error.response?.data?.error || error.message || '알 수 없는 오류가 발생했습니다.'
        };
    }
};

export const post = async (endpoint, data) => {
    try {
        console.log(`[API POST 요청] ${endpoint}`, data);
        const response = await api.post(endpoint, data);
        console.log(`[API POST 성공] ${endpoint}`, response.data);
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        console.error(`[API POST 실패] ${endpoint}`, error);
        return {
            success: false,
            message: error.response?.data?.message || error.response?.data?.error || error.message || '알 수 없는 오류가 발생했습니다.'
        };
    }
};

export const put = async (endpoint, data) => {
    try {
        console.log(`[API PUT 요청] ${endpoint}`, data);
        const response = await api.put(endpoint, data);
        console.log(`[API PUT 성공] ${endpoint}`, response.data);
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        console.error(`[API PUT 실패] ${endpoint}`, error);
        return {
            success: false,
            message: error.response?.data?.message || error.response?.data?.error || error.message || '알 수 없는 오류가 발생했습니다.'
        };
    }
};

export const del = async (endpoint) => {
    try {
        console.log(`[API DELETE 요청] ${endpoint}`);
        const response = await api.delete(endpoint);
        console.log(`[API DELETE 성공] ${endpoint}`, response.data);
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        console.error(`[API DELETE 실패] ${endpoint}`, error);
        return {
            success: false,
            message: error.response?.data?.message || error.response?.data?.error || error.message || '알 수 없는 오류가 발생했습니다.'
        };
    }
};

// API 연결 테스트 함수
export const testConnection = async () => {
    try {
        console.log('[API 연결 테스트] 시작');
        const response = await api.get('dashboard/stats/');
        console.log('[API 연결 테스트] 성공', response.data);
        return { success: true, data: response.data };
    } catch (error) {
        console.error('[API 연결 테스트] 실패', error);
        return { success: false, error: error.message };
    }
};

export default api; 