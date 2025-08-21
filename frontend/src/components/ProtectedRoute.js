import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { hasPermission } from '../utils/rolePermissions';

const ProtectedRoute = ({ children, requiredPermissions = [] }) => {
    const { user, loading } = useAuth();

    // 개발환경에서만 로그 출력
    if (process.env.NODE_ENV === 'development') {
        console.log('[ProtectedRoute] 컴포넌트 렌더링', { 
            user: user?.username, 
            loading, 
            isAuthenticated: !!user,
            requiredPermissions
        });
    }

    if (loading) {

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

        return <Navigate to="/login" replace />;
    }

    // 특정 권한이 필요한 경우 권한 확인
    if (requiredPermissions.length > 0) {
        const hasRequiredPermissions = requiredPermissions.every(permission => 
            hasPermission(user, permission)
        );
        
        if (!hasRequiredPermissions) {
            
            return (
                <div style={{ 
                    display: 'flex', 
                    flexDirection: 'column',
                    justifyContent: 'center', 
                    alignItems: 'center', 
                    height: '100vh',
                    fontSize: '18px',
                    color: '#dc3545'
                }}>
                    <h2>접근 권한이 없습니다</h2>
                    <p>이 페이지에 접근할 권한이 없습니다.</p>
                    <button 
                        onClick={() => window.location.href = '/dashboard'}
                        style={{
                            padding: '10px 20px',
                            backgroundColor: '#007bff',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            marginTop: '20px'
                        }}
                    >
                        대시보드로 이동
                    </button>
                </div>
            );
        }
    }


    return children;
};

export default ProtectedRoute; 