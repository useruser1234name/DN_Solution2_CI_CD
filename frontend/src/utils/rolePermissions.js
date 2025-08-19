/**
 * 역할 및 권한 관리 유틸리티
 * 
 * 사용자의 역할과 회사 타입에 따른 권한을 관리합니다.
 * 업체 코드 패턴 (A-YYMMDD-01, B-YYMMDD-01, C-YYMMDD-01) 기반 권한 체크 지원
 * 추후 세부 역할이 추가될 것을 고려한 확장 가능한 구조입니다.
 */

import { getCompanyTypeFromCode } from './companyUtils';

// 회사 타입별 기본 권한
const COMPANY_TYPE_PERMISSIONS = {
  headquarters: {
    // 본사 권한 (모든 권한)
    canViewAllCompanies: true,
    canManageAgencies: true,
    canManageDealers: true,
    canViewAllReports: true,
    canViewPolicies: true,          // 정책 목록 조회 가능
    canManagePolicies: true,        // 정책 관리(생성/수정/삭제) 가능
    canApproveOrders: true,         // 주문 승인 가능
    canViewAllOrders: true,
    canManageSettlements: true,
    canViewSystemLogs: true,
    canManageSystemSettings: true,
    canViewUserHierarchy: true,
  },
  agency: {
    // 협력사 권한
    canViewAllCompanies: false,
    canManageRetailers: true,
    canViewSubordinateReports: true,
    canViewAssignedPolicies: true,  // 할당된 정책 조회 가능
    canViewPolicies: true,          // 정책 목록 조회 가능 (정책 페이지 접근)
    canManagePolicies: false,       // 협력사는 정책 관리 불가
    canCreateOrders: false,
    canApproveOrders: false,        // 협력사는 주문 승인 불가
    canViewAllOrders: true,         // 협력사는 주문 확인 가능
    canViewOwnSettlements: true,
    canViewUserHierarchy: true,     // 협력사는 하위 판매점 관리 가능
  },
  dealer: {
    // 대리점 권한
    canViewAllCompanies: false,
    canManageRetailers: true,
    canViewSubordinateReports: true,
    canViewAssignedPolicies: true,  // 할당된 정책 조회 가능
    canViewPolicies: true,          // 정책 목록 조회 가능
    canManagePolicies: false,       // 대리점은 정책 관리 불가
    canCreateOrders: false,
    canApproveOrders: false,        // 대리점은 주문 승인 불가
    canViewAllOrders: false,
    canViewOwnSettlements: true,
  },
  retail: {
    // 판매점 권한 (주문 생성을 위한 정책 조회 가능)
    canViewAllCompanies: false,
    canCreateOrders: true,           // 주문 생성 가능
    canViewOwnReports: true,
    canViewAssignedPolicies: true,   // 할당된 정책 조회 가능
    canViewPolicies: true,           // 정책 목록 조회 가능 (주문 생성을 위해 필수)
    canManagePolicies: false,        // 판매점은 정책 관리 불가
    canApproveOrders: false,         // 판매점은 주문 승인 불가
    canViewAllOrders: false,
    canViewOwnSettlements: true,
    canViewUserHierarchy: false,     // 판매점은 사용자 목록 접근 불가
  },
};

// 역할별 추가 권한 (추후 확장용)
const ROLE_PERMISSIONS = {
  admin: {
    // 관리자 추가 권한
    canManageUsers: true,
    canApproveUsers: true,
    canDeleteData: true,
  },
  staff: {
    // 직원 권한
    canManageUsers: false,
    canApproveUsers: false,
    canDeleteData: false,
  },
  // 추후 추가될 역할들
  manager: {
    canManageUsers: true,
    canApproveUsers: false,
    canDeleteData: false,
  },
  operator: {
    canManageUsers: false,
    canApproveUsers: false,
    canDeleteData: false,
  },
};

// 메뉴 항목별 필요 권한
const MENU_PERMISSIONS = {
  dashboard: [], // 모든 사용자 접근 가능
  companies: ['canViewAllCompanies', 'canManageAgencies', 'canManageDealers', 'canManageRetailers'],
  users: ['canManageUsers', 'canViewUserHierarchy'],
  userApproval: ['canApproveUsers'], // 사용자 승인 권한 추가
  policies: ['canViewPolicies', 'canManagePolicies', 'canViewAssignedPolicies'], // 정책 조회 권한 추가
  orders: ['canCreateOrders', 'canApproveOrders', 'canViewOwnReports', 'canViewAllOrders'],
  settlements: ['canManageSettlements', 'canViewOwnSettlements'],
  settings: ['canManageSystemSettings'],
  logs: ['canViewSystemLogs'],
};

/**
 * 사용자의 전체 권한을 계산합니다.
 * @param {string} companyType - 회사 타입
 * @param {string} role - 사용자 역할
 * @returns {object} 권한 객체
 */
export const getUserPermissions = (companyType, role) => {
  const companyPermissions = COMPANY_TYPE_PERMISSIONS[companyType] || {};
  const rolePermissions = ROLE_PERMISSIONS[role] || {};
  
  // 회사 타입 권한과 역할 권한을 병합
  return {
    ...companyPermissions,
    ...rolePermissions,
  };
};

/**
 * 특정 권한이 있는지 확인합니다.
 * @param {object} user - 사용자 객체
 * @param {string} permission - 확인할 권한
 * @returns {boolean} 권한 여부
 */
export const hasPermission = (user, permission) => {
  if (!user || !user.company) return false;
  
  // 회사 타입 확인 (실제 타입 또는 코드 패턴 기반)
  let companyType = user.company.type;
  
  // company.type이 없으면 코드 패턴으로 타입 추정
  if (!companyType && user.company.code) {
    companyType = getCompanyTypeFromCode(user.company.code);
  }
  
  // unknown 타입인 경우 기본적으로 모든 권한을 false로 처리
  if (companyType === 'unknown') {
    console.warn(`Unknown company type for user ${user.username}. Company code: ${user.company.code}`);
    return false;
  }
  
  const permissions = getUserPermissions(companyType, user.role);
  return permissions[permission] === true;
};

/**
 * 여러 권한 중 하나라도 있는지 확인합니다.
 * @param {object} user - 사용자 객체
 * @param {array} permissions - 확인할 권한 배열
 * @returns {boolean} 권한 여부
 */
export const hasAnyPermission = (user, permissions) => {
  if (!user || !user.company || !Array.isArray(permissions)) return false;
  
  // 회사 타입 확인 (실제 타입 또는 코드 패턴 기반)
  let companyType = user.company.type;
  if (!companyType && user.company.code) {
    companyType = getCompanyTypeFromCode(user.company.code);
  }
  
  // unknown 타입인 경우 기본적으로 모든 권한을 false로 처리
  if (companyType === 'unknown') {
    console.warn(`Unknown company type for user ${user.username}. Company code: ${user.company.code}`);
    return false;
  }
  
  const userPermissions = getUserPermissions(companyType, user.role);
  return permissions.some(permission => userPermissions[permission] === true);
};

/**
 * 모든 권한이 있는지 확인합니다.
 * @param {object} user - 사용자 객체
 * @param {array} permissions - 확인할 권한 배열
 * @returns {boolean} 권한 여부
 */
export const hasAllPermissions = (user, permissions) => {
  if (!user || !user.company || !Array.isArray(permissions)) return false;
  
  // 회사 타입 확인 (실제 타입 또는 코드 패턴 기반)
  let companyType = user.company.type;
  if (!companyType && user.company.code) {
    companyType = getCompanyTypeFromCode(user.company.code);
  }
  
  // unknown 타입인 경우 기본적으로 모든 권한을 false로 처리
  if (companyType === 'unknown') {
    console.warn(`Unknown company type for user ${user.username}. Company code: ${user.company.code}`);
    return false;
  }
  
  const userPermissions = getUserPermissions(companyType, user.role);
  return permissions.every(permission => userPermissions[permission] === true);
};

/**
 * 메뉴 항목에 대한 접근 권한이 있는지 확인합니다.
 * @param {object} user - 사용자 객체
 * @param {string} menuKey - 메뉴 키
 * @returns {boolean} 접근 가능 여부
 */
export const canAccessMenu = (user, menuKey) => {
  // 사용자가 없거나 회사 정보가 없으면 접근 불가
  if (!user || !user.company) {
    return false;
  }
  
  const requiredPermissions = MENU_PERMISSIONS[menuKey];
  
  // 권한이 정의되지 않은 메뉴는 모두 접근 가능
  if (!requiredPermissions || requiredPermissions.length === 0) {
    return true;
  }
  
  // 필요한 권한 중 하나라도 있으면 접근 가능
  return hasAnyPermission(user, requiredPermissions);
};

/**
 * 사용자가 접근 가능한 메뉴 목록을 반환합니다.
 * @param {object} user - 사용자 객체
 * @returns {array} 접근 가능한 메뉴 키 배열
 */
export const getAccessibleMenus = (user) => {
  return Object.keys(MENU_PERMISSIONS).filter(menuKey => 
    canAccessMenu(user, menuKey)
  );
};

/**
 * 역할별 대시보드 위젯을 반환합니다.
 * @param {object} user - 사용자 객체
 * @returns {array} 표시할 위젯 목록
 */
export const getDashboardWidgets = (user) => {
  if (!user || !user.company) return [];
  
  // 회사 타입 확인 (실제 타입 또는 코드 패턴 기반)
  let companyType = user.company.type;
  if (!companyType && user.company.code) {
    companyType = getCompanyTypeFromCode(user.company.code);
  }
  
  const widgets = [];
  const permissions = getUserPermissions(companyType, user.role);
  
  // 공통 위젯
  widgets.push('statistics');
  widgets.push('recentActivities');
  
  // 권한별 위젯
  if (permissions.canManageAgencies || permissions.canManageDealers || permissions.canManageRetailers) {
    widgets.push('companyHierarchy');
  }
  
  if (permissions.canApproveOrders) {
    widgets.push('pendingOrders');
  }
  
  if (permissions.canManageSettlements || permissions.canViewOwnSettlements) {
    widgets.push('settlementSummary');
  }
  
  if (permissions.canManagePolicies) {
    widgets.push('policyStatus');
  }
  
  if (permissions.canApproveUsers) {
    widgets.push('pendingUsers');
  }
  
  if (permissions.canViewSystemLogs) {
    widgets.push('systemAlerts');
  }
  
  return widgets;
};

/**
 * 회사 타입 한글 변환
 * @param {string} type - 회사 타입
 * @returns {string} 한글 회사 타입
 */
export const getCompanyTypeLabel = (type) => {
  const labels = {
    headquarters: '본사',
    agency: '협력사',
    dealer: '대리점',
    retail: '판매점',
  };
  return labels[type] || type;
};

/**
 * 역할 한글 변환
 * @param {string} role - 역할
 * @returns {string} 한글 역할
 */
export const getRoleLabel = (role) => {
  const labels = {
    admin: '관리자',
    staff: '직원',
    manager: '매니저',
    operator: '운영자',
  };
  return labels[role] || role;
};

/**
 * 사용자의 회사 타입을 반환합니다. (업체 코드 패턴 지원)
 * @param {object} user - 사용자 객체
 * @returns {string} 회사 타입
 */
export const getUserCompanyType = (user) => {
  if (!user || !user.company) {
    return 'unknown';
  }
  
  // 실제 타입이 있으면 사용, 없으면 코드 패턴으로 추정
  if (user.company.type) {
    return user.company.type;
  }
  
  if (user.company.code) {
    return getCompanyTypeFromCode(user.company.code);
  }
  
  return 'unknown';
};

export default {
  getUserPermissions,
  hasPermission,
  hasAnyPermission,
  hasAllPermissions,
  canAccessMenu,
  getAccessibleMenus,
  getDashboardWidgets,
  getCompanyTypeLabel,
  getRoleLabel,
  getUserCompanyType,
};
