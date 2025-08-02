import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ children }) => {
    const { user, loading } = useAuth();

    console.log('[ProtectedRoute] 컴포넌트 렌더링', { 
        user: user?.username, 
        loading, 
        isAuthenticated: !!user 
    });

    if (loading) {
        console.log('[ProtectedRoute] 로딩 중 - 로딩 화면 표시');
        return (
            <div style={{ 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center', 
                height: '100vh',
                fontSize: '18px'
            }}>
                인증 확인 중...
            </div>
        );
    }

    if (!user) {
        console.log('[ProtectedRoute] 인증되지 않은 사용자 - 로그인 페이지로 리다이렉트');
        return <Navigate to="/login" replace />;
    }

    console.log('[ProtectedRoute] 인증된 사용자 - 보호된 페이지 표시');
    return children;
};

export default ProtectedRoute; 