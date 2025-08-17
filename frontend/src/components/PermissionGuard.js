import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { hasPermission as utilsHasPermission, hasAnyPermission as utilsHasAnyPermission, hasAllPermissions as utilsHasAllPermissions } from '../utils/rolePermissions';

/**
 * 권한 기반 렌더링 컴포넌트
 * 
 * 사용자의 권한에 따라 자식 컴포넌트를 조건부 렌더링합니다.
 * 
 * @param {string} permission - 단일 권한
 * @param {array} anyPermissions - OR 조건 권한 배열
 * @param {array} allPermissions - AND 조건 권한 배열
 * @param {node} children - 렌더링할 자식 컴포넌트
 * @param {node} fallback - 권한이 없을 때 표시할 컴포넌트
 */
const PermissionGuard = ({ 
  permission, 
  anyPermissions, 
  allPermissions, 
  children, 
  fallback = null 
}) => {
  const { user } = useAuth();
  
  // 사용자가 없으면 fallback 렌더링
  if (!user) {
    return fallback;
  }
  
  let hasRequiredPermission = false;
  
  // 단일 권한 체크
  if (permission) {
    hasRequiredPermission = utilsHasPermission(user, permission);
  }
  // OR 조건 권한 체크
  else if (anyPermissions && anyPermissions.length > 0) {
    hasRequiredPermission = utilsHasAnyPermission(user, anyPermissions);
  }
  // AND 조건 권한 체크
  else if (allPermissions && allPermissions.length > 0) {
    hasRequiredPermission = utilsHasAllPermissions(user, allPermissions);
  }
  // 권한 조건이 없으면 항상 표시
  else {
    hasRequiredPermission = true;
  }
  
  return hasRequiredPermission ? children : fallback;
};

export default PermissionGuard;
