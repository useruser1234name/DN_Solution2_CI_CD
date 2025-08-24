/**
 * 보호된 라우트 컴포넌트
 * 인증 및 권한 확인 후 컴포넌트 렌더링
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin, Alert } from 'antd';
import { useAuth } from '../../contexts/AuthContext';

const ProtectedRoute = ({ 
  children, 
  requiredPermissions = [], 
  requireAuth = true,
  fallbackPath = '/login'
}) => {
  const { user, loading, isAuthenticated } = useAuth();
  const location = useLocation();

  console.log('[ProtectedRoute] 컴포넌트 렌더링', {
    user,
    loading,
    isAuthenticated: isAuthenticated(),
    requiredPermissions,
    currentPath: location.pathname
  });

  // 로딩 중일 때
  if (loading) {
    return (
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center', 
        height: '100vh' 
      }}>
        <Spin size="large" tip="인증 정보를 확인하는 중..." />
      </div>
    );
  }

  // 인증이 필요한데 인증되지 않은 경우
  if (requireAuth && !isAuthenticated()) {
    console.log('[ProtectedRoute] 인증되지 않은 사용자, 로그인 페이지로 리다이렉트');
    return <Navigate to={fallbackPath} state={{ from: location }} replace />;
  }

  // 특정 권한이 필요한 경우 권한 확인
  if (requiredPermissions.length > 0 && user) {
    const hasAllPermissions = requiredPermissions.every(permission => {
      // 사용자의 계산된 권한에서 확인
      if (user.calculatedPermissions && user.calculatedPermissions[permission]) {
        return true;
      }
      
      // 기본 권한에서 확인
      if (user.permissions && user.permissions.includes(permission)) {
        return true;
      }
      
      // 업체 타입 기반 권한 확인
      const companyType = user.companyType || user.company?.type;
      
      // 본사는 모든 권한 허용
      if (companyType === 'headquarters') {
        return true;
      }
      
      // 특정 권한별 체크
      switch (permission) {
        case 'canViewDashboard':
          return ['headquarters', 'agency', 'retail'].includes(companyType);
        case 'canManagePolicies':
          return companyType === 'headquarters';
        case 'canManageCompanies':
          return ['headquarters', 'agency'].includes(companyType);
        case 'canViewOrders':
          return ['headquarters', 'agency', 'retail'].includes(companyType);
        case 'canCreateOrders':
          return ['agency', 'retail'].includes(companyType);
        case 'canApproveOrders':
          return ['headquarters', 'agency'].includes(companyType);
        case 'canViewSettlements':
          return ['headquarters', 'agency', 'retail'].includes(companyType);
        case 'canProcessSettlements':
          return companyType === 'headquarters';
        default:
          return false;
      }
    });

    if (!hasAllPermissions) {
      console.log('[ProtectedRoute] 권한 부족', {
        requiredPermissions,
        userPermissions: user.calculatedPermissions,
        companyType: user.companyType || user.company?.type
      });
      
      return (
        <div style={{ padding: '20px' }}>
          <Alert
            message="접근 권한이 없습니다"
            description="이 페이지에 접근할 권한이 없습니다. 관리자에게 문의하세요."
            type="error"
            showIcon
          />
        </div>
      );
    }
  }

  // 모든 조건을 만족하면 자식 컴포넌트 렌더링
  console.log('[ProtectedRoute] 접근 허용, 컴포넌트 렌더링');
  return children;
};

export default ProtectedRoute;