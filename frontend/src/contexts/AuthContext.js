/**
 * 인증 컨텍스트
 * 사용자 정보, 권한, 로그인/로그아웃 관리
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { message } from 'antd';
import { authAPI, handleAPIError } from '../services/api';
import { getUserPermissions, getUserCompanyType } from '../utils/rolePermissions';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth는 AuthProvider 내에서 사용되어야 합니다.');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);

  // 권한 매트릭스 (백엔드의 권한 시스템과 연동)
  const PERMISSIONS = {
    // 정책 관리 권한
    'policy.create': ['headquarters_admin'],
    'policy.edit': ['headquarters_admin'],
    'policy.delete': ['headquarters_admin'],
    'policy.view': ['headquarters_admin', 'agency_admin', 'retail_admin', 'agency_staff', 'retail_staff'],
    'policy.assign': ['headquarters_admin'],
    
    // 업체 관리 권한
    'company.create': ['headquarters_admin'],
    'company.edit': ['headquarters_admin'],
    'company.delete': ['headquarters_admin'],
    'company.view': ['headquarters_admin', 'agency_admin', 'retail_admin'],
    'company.approve_user': ['headquarters_admin', 'agency_admin'],
    
    // 주문 관리 권한
    'order.create': ['agency_admin', 'retail_admin', 'agency_staff', 'retail_staff'],
    'order.edit': ['agency_admin', 'retail_admin', 'agency_staff', 'retail_staff'],
    'order.view': ['headquarters_admin', 'agency_admin', 'retail_admin', 'agency_staff', 'retail_staff'],
    'order.approve': ['headquarters_admin', 'agency_admin'],
    
    // 정산 관리 권한
    'settlement.view': ['headquarters_admin', 'agency_admin', 'retail_admin'],
    'settlement.process': ['headquarters_admin'],
    
    // 대시보드 권한
    'dashboard.view': ['headquarters_admin', 'agency_admin', 'retail_admin'],
    'dashboard.stats': ['headquarters_admin'],
    
    // 리베이트 관리 권한
    'rebate.view': ['headquarters_admin', 'agency_admin', 'retail_admin'],
    'rebate.edit_base': ['headquarters_admin'],
    'rebate.edit_custom': ['agency_admin'],
  };

  // 초기화
  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (token) {
        const tokenInfo = await authAPI.getUserInfo();
        
        // 토큰 정보에서 사용자 정보 구성
        if (tokenInfo.user && tokenInfo.is_valid) {
          const userInfo = {
            id: tokenInfo.user.id,
            username: tokenInfo.user.username,
            email: tokenInfo.user.email,
            company: tokenInfo.company,
            role: tokenInfo.role,
            permissions: tokenInfo.permissions || []
          };
          
          // rolePermissions.js와 일치시키기 위해 권한 재계산
          const companyType = getUserCompanyType(userInfo);
          const calculatedPermissions = getUserPermissions(companyType, userInfo.role);
          userInfo.calculatedPermissions = calculatedPermissions;
          userInfo.companyType = companyType;
          
          console.log('사용자 권한 정보:', {
            username: userInfo.username,
            company: userInfo.company,
            companyType: companyType,
            role: userInfo.role,
            calculatedPermissions: calculatedPermissions
          });
          
          setUser(userInfo);
        } else {
          throw new Error('유효하지 않은 토큰');
        }
      }
    } catch (error) {
      console.error('인증 초기화 오류:', error);
      // 토큰이 유효하지 않은 경우 제거
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setLoading(false);
      setInitialized(true);
    }
  };

  // 로그인
  const login = async (username, password) => {
    try {
      setLoading(true);
      const response = await authAPI.login(username, password);
      
      // 토큰 저장
      localStorage.setItem('access_token', response.access);
      localStorage.setItem('refresh_token', response.refresh);
      
      // 사용자 정보 구성
      const userInfo = {
        id: response.user_id,
        username: username,
        company: response.company,
        role: response.role,
        permissions: getUserPermissions(response.company.type, response.role),
      };
      
      // rolePermissions.js와 일치시키기 위해 권한 재계산
      const companyType = getUserCompanyType(userInfo);
      const calculatedPermissions = getUserPermissions(companyType, userInfo.role);
      userInfo.calculatedPermissions = calculatedPermissions;
      userInfo.companyType = companyType;
      
      console.log('로그인 후 사용자 권한 정보:', {
        username: userInfo.username,
        company: userInfo.company,
        companyType: companyType,
        role: userInfo.role,
        calculatedPermissions: calculatedPermissions
      });
      
      setUser(userInfo);
      message.success('로그인되었습니다.');
      
      return { success: true, user: userInfo };
      
    } catch (error) {
      console.error('로그인 오류:', error);
      const errorMessage = handleAPIError(error);
      message.error(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setLoading(false);
    }
  };

  // 로그아웃
  const logout = async () => {
    try {
      await authAPI.logout();
    } catch (error) {
      console.error('로그아웃 API 오류:', error);
    } finally {
      setUser(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      message.info('로그아웃되었습니다.');
    }
  };

  // 사용자 권한 계산
  const getUserPermissions = (companyType, userRole) => {
    const roleKey = `${companyType}_${userRole}`;
    const permissions = {};
    
    Object.keys(PERMISSIONS).forEach(permission => {
      permissions[permission] = PERMISSIONS[permission].includes(roleKey);
    });
    
    return permissions;
  };

  // 권한 확인 함수 (rolePermissions.js와 동일한 로직 사용)
  const hasPermission = (permission) => {
    if (!user || !user.calculatedPermissions) {
      return false;
    }
    return user.calculatedPermissions[permission] === true;
  };

  // 업체 타입별 권한 확인 (rolePermissions.js와 동일한 로직 사용)
  const isHeadquarters = () => user?.companyType === 'headquarters';
  const isAgency = () => user?.companyType === 'agency';
  const isRetail = () => user?.companyType === 'retail';

  // 역할별 권한 확인
  const isAdmin = () => user?.role === 'admin';
  const isStaff = () => user?.role === 'staff';

  // 복합 권한 확인 (rolePermissions.js와 일치)
  const canManagePolicies = () => hasPermission('canManagePolicies');
  const canManageCompanies = () => hasPermission('canManageAgencies') || hasPermission('canManageDealers');
  const canViewDashboard = () => true; // 모든 사용자가 대시보드 접근 가능

  // 사용자 정보 업데이트
  const updateUser = (updates) => {
    setUser(prev => ({ ...prev, ...updates }));
  };

  // 인증 상태 확인
  const isAuthenticated = () => !!user;

  const value = {
    // 상태
    user,
    loading,
    initialized,
    
    // 액션
    login,
    logout,
    updateUser,
    
    // 권한 확인
    hasPermission,
    isHeadquarters,
    isAgency,
    isRetail,
    isAdmin,
    isStaff,
    canManagePolicies,
    canManageCompanies,
    canViewDashboard,
    isAuthenticated,
    
    // 유틸리티
    getUserPermissions,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;