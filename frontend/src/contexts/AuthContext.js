import React, { createContext, useContext, useState, useEffect } from 'react';
import { post } from '../services/api';

const AuthContext = createContext();

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        console.error('[AuthContext] useAuth must be used within an AuthProvider');
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        console.log('[AuthContext] 초기화 시작');
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
            try {
                const userData = JSON.parse(savedUser);
                console.log('[AuthContext] 저장된 사용자 정보 로드:', userData);
                setUser(userData);
            } catch (error) {
                console.error('[AuthContext] 저장된 사용자 정보 파싱 오류:', error);
                localStorage.removeItem('user');
            }
        } else {
            console.log('[AuthContext] 저장된 사용자 정보 없음');
        }
        setLoading(false);
        console.log('[AuthContext] 초기화 완료');
    }, []);

    const login = async (username, password) => {
        console.log('[AuthContext] 로그인 시도:', { username, password: '***' });
        try {
            // JWT 토큰 발급 엔드포인트 호출
            console.log('[AuthContext] JWT 로그인 API 호출');
            const response = await post('auth/login/', {
                username: username,
                password: password
            });
            console.log('[AuthContext] JWT 응답:', response);
            if (response.success && response.data.access) {
                const userData = {
                    username: username,
                    token: response.data.access,
                };
                setUser(userData);
                localStorage.setItem('user', JSON.stringify(userData));
                localStorage.setItem('authToken', response.data.access);
                return { success: true, message: '로그인 성공' };
            } else {
                return { success: false, message: '아이디 또는 비밀번호가 올바르지 않습니다.' };
            }
        } catch (error) {
            console.error('[AuthContext] 로그인 중 오류:', error);
            return { success: false, message: '로그인 중 오류가 발생했습니다.' };
        }
    };

    const logout = () => {
        console.log('[AuthContext] 로그아웃 실행');
        setUser(null);
        localStorage.removeItem('user');
        localStorage.removeItem('authToken');
        console.log('[AuthContext] 로그아웃 완료');
    };

    const value = {
        user,
        login,
        logout,
        loading
    };

    console.log('[AuthContext] 현재 상태:', { user: user?.username, loading });

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}; 