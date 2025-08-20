import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { canAccessMenu, getCompanyTypeLabel, getRoleLabel, hasPermission as utilsHasPermission } from '../utils/rolePermissions';
import { getCompanyTypeFromCode } from '../utils/companyUtils';
import './Sidebar.css';

const Sidebar = () => {
    const { user, logout } = useAuth();
    const [collapsed, setCollapsed] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();



    const handleLogout = () => {
        logout();
    };

    const handleToggleCollapse = () => {
        setCollapsed(!collapsed);
    };

    const handleMenuClick = (path) => {
        navigate(path);
    };

    // 현재 활성 메뉴 확인
    const isActiveMenu = (path) => {
        return location.pathname === path || location.pathname.startsWith(path + '/');
    };

    // 메뉴 구성 - 권한에 따라 동적으로 표시
    const menuSections = [
        {
            title: '대시보드',
            key: 'dashboard',
            items: [
                { 
                    path: '/dashboard', 
                    label: '대시보드', 
                    icon: '📊',
                    permission: 'dashboard'
                }
            ]
        },
        {
            title: '업체 관리',
            key: 'companies',
            items: [
                { 
                    path: '/companies', 
                    label: '업체 목록', 
                    icon: '🏢',
                    permission: 'companies'
                },
                { 
                    path: '/companies/create', 
                    label: '새 업체 등록', 
                    icon: '➕',
                    permission: 'companies'
                }
            ]
        },

        {
            title: '정책 관리',
            key: 'policies',
            items: [
                { 
                    path: '/policies', 
                    label: '정책 목록', 
                    icon: '📋',
                    permission: 'canViewPolicies'
                },
                { 
                    path: '/policies/create', 
                    label: '새 정책 등록', 
                    icon: '➕',
                    permission: 'canManagePolicies'  // 본사만!
                }
            ]
        },
        {
            title: '주문 관리',
            key: 'orders',
            items: [
                { 
                    path: '/orders', 
                    label: '주문 목록', 
                    icon: '📦',
                    permission: 'canViewAllOrders'
                },
                { 
                    path: '/orders/create', 
                    label: '새 주문 등록', 
                    icon: '➕',
                    permission: 'canCreateOrders'  // 판매점만!
                }
            ]
        },
        {
            title: '정산 관리',
            key: 'settlements',
            items: [
                { 
                    path: '/settlements', 
                    label: '정산 목록', 
                    icon: '💰',
                    permission: 'settlements'
                },
                { 
                    path: '/settlements/report', 
                    label: '정산 보고서', 
                    icon: '📊',
                    permission: 'settlements'
                }
            ]
        },
        {
            title: '시스템',
            key: 'system',
            items: [
                { 
                    path: '/settings', 
                    label: '시스템 설정', 
                    icon: '⚙️',
                    permission: 'settings'
                },
                { 
                    path: '/logs', 
                    label: '로그 보기', 
                    icon: '📝',
                    permission: 'logs'
                }
            ]
        }
    ];

    // 권한에 따라 메뉴 필터링
    const getVisibleMenuSections = () => {
        return menuSections.map(section => {
            // 섹션 내 아이템 중 권한이 있는 것만 필터링
            const visibleItems = section.items.filter(item => {
                // item.permission이 없으면 모든 사용자에게 표시
                if (!item.permission) return true;
                
                // 회사 타입 제한 체크
                if (item.companyTypeRestriction) {
                    const userCompanyType = user?.company?.type || 
                        (user?.company?.code ? getCompanyTypeFromCode(user.company.code) : 'unknown');
                    
                    // 회사 타입이 일치하지 않으면 표시하지 않음
                    if (userCompanyType !== item.companyTypeRestriction) {
                        return false;
                    }
                }
                
                // 특정 메뉴 항목들은 개별 권한 체크
                if (item.path === '/policies/create') {
                    // "새 정책 등록"은 canManagePolicies 권한만 체크
                    return utilsHasPermission(user, 'canManagePolicies');
                }
                if (item.path === '/orders/create') {
                    // "새 주문 등록"은 canCreateOrders 권한만 체크
                    return utilsHasPermission(user, 'canCreateOrders');
                }
                
                // 나머지는 메뉴 접근 권한으로 체크 (OR 조건)
                return canAccessMenu(user, item.permission);
            });

            // 표시할 아이템이 있는 섹션만 반환
            if (visibleItems.length > 0) {
                return {
                    ...section,
                    items: visibleItems
                };
            }
            return null;
        }).filter(Boolean); // null 제거
    };

    const visibleMenuSections = getVisibleMenuSections();

    return (
        <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
            <div className="sidebar-header">
                <div className="sidebar-logo">
                    <h2 className="sidebar-title">
                        {collapsed ? '🏢' : '🏢 DN_Solution'}
                    </h2>
                    {!collapsed && <p className="sidebar-subtitle">통신업계 관리 솔루션</p>}
                </div>
                <button 
                    className="collapse-btn"
                    onClick={handleToggleCollapse}
                    title={collapsed ? '사이드바 확장' : '사이드바 축소'}
                >
                    {collapsed ? '📌' : '📍'}
                </button>
            </div>

            <div className="sidebar-menu">
                {visibleMenuSections.map(section => (
                    <div key={section.key} className="menu-section">
                        {!collapsed && <h3>{section.title}</h3>}
                        <ul>
                            {section.items.map(item => (
                                <li 
                                    key={item.path}
                                    className={isActiveMenu(item.path) ? 'active' : ''}
                                    onClick={() => handleMenuClick(item.path)}
                                    title={collapsed ? item.label : ''}
                                >
                                    <span className="menu-icon">{item.icon}</span>
                                    {!collapsed && <span className="menu-label">{item.label}</span>}
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>

            <div className="sidebar-footer">
                <div className="user-info">
                    <div className="user-avatar">
                        {user?.username?.charAt(0).toUpperCase() || '👤'}
                    </div>
                    {!collapsed && (
                        <div className="user-details">
                            <span className="username">{user?.username}</span>
                            <span className="company-info">
                                <span className="company-code">{user?.company?.code}</span>
                                <span className="company-type">
                                    {user?.company && getCompanyTypeLabel(
                                        user.company.type || getCompanyTypeFromCode(user.company.code)
                                    )}
                                </span>
                            </span>
                            <span className="role">
                                {user?.role && getRoleLabel(user.role)}
                            </span>
                        </div>
                    )}
                </div>
                <button 
                    className="logout-btn" 
                    onClick={handleLogout}
                    title="로그아웃"
                >
                    {collapsed ? '🚪' : '🚪 로그아웃'}
                </button>
            </div>
        </div>
    );
};

export default Sidebar;