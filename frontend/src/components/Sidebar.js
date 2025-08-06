import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './Sidebar.css';

const Sidebar = () => {
    const { user, logout } = useAuth();
    const [collapsed, setCollapsed] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();

    console.log('[Sidebar] 컴포넌트 렌더링', { user: user?.username, collapsed, currentPath: location.pathname });

    const handleLogout = () => {
        console.log('[Sidebar] 로그아웃 버튼 클릭');
        logout();
    };

    const handleToggleCollapse = () => {
        console.log('[Sidebar] 사이드바 토글', { currentState: collapsed, newState: !collapsed });
        setCollapsed(!collapsed);
    };

    const handleMenuClick = (menuName) => {
        console.log('[Sidebar] 메뉴 클릭:', menuName);
        
        // 메뉴별 라우팅
        switch (menuName) {
            case 'dashboard':
                navigate('/dashboard');
                break;
            case 'company-list':
                navigate('/companies');
                break;
            case 'company-create':
                navigate('/companies/create');
                break;
            case 'user-list':
                navigate('/users');
                break;
            case 'user-approval':
                navigate('/users/approval');
                break;
            case 'policies':
                navigate('/policies');
                break;
            case 'policy-create':
                navigate('/policies/create');
                break;
            case 'orders':
                navigate('/orders');
                break;
            case 'order-create':
                navigate('/orders/create');
                break;
            case 'inventory':
                navigate('/inventory');
                break;
            case 'inventory-create':
                navigate('/inventory/create');
                break;
            case 'messages':
                navigate('/messages');
                break;
            case 'message-create':
                navigate('/messages/create');
                break;
            case 'settings':
                navigate('/settings');
                break;
            case 'logs':
                navigate('/logs');
                break;
            default:
                console.log('[Sidebar] 알 수 없는 메뉴:', menuName);
        }
    };

    // 현재 활성 메뉴 확인
    const isActiveMenu = (menuName) => {
        const currentPath = location.pathname;
        switch (menuName) {
            case 'dashboard':
                return currentPath === '/dashboard';
            case 'company-list':
                return currentPath === '/companies';
            case 'user-list':
                return currentPath === '/users';
            case 'policies':
                return currentPath === '/policies';
            case 'orders':
                return currentPath === '/orders';
            case 'inventory':
                return currentPath === '/inventory';
            case 'messages':
                return currentPath === '/messages';
            case 'settings':
                return currentPath === '/settings';
            case 'logs':
                return currentPath === '/logs';
            default:
                return false;
        }
    };

    return (
        <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
            <div className="sidebar-header">
                <h2 className="sidebar-title">DN_Solution</h2>
                <button 
                    className="collapse-btn"
                    onClick={handleToggleCollapse}
                >
                    {collapsed ? '→' : '←'}
                </button>
            </div>

            <div className="sidebar-menu">
                <div className="menu-section">
                    <h3>대시보드</h3>
                    <ul>
                        <li 
                            className={isActiveMenu('dashboard') ? 'active' : ''}
                            onClick={() => handleMenuClick('dashboard')}
                        >
                            📊 대시보드
                        </li>
                    </ul>
                </div>

                <div className="menu-section">
                    <h3>업체 관리</h3>
                    <ul>
                        <li 
                            className={isActiveMenu('company-list') ? 'active' : ''}
                            onClick={() => handleMenuClick('company-list')}
                        >
                            🏢 업체 목록
                        </li>
                        <li onClick={() => handleMenuClick('company-create')}>
                            ➕ 새 업체 등록
                        </li>
                    </ul>
                </div>

                <div className="menu-section">
                    <h3>사용자 관리</h3>
                    <ul>
                        <li 
                            className={isActiveMenu('user-list') ? 'active' : ''}
                            onClick={() => handleMenuClick('user-list')}
                        >
                            👥 사용자 목록
                        </li>
                    </ul>
                </div>

                <div className="menu-section">
                    <h3>정책 관리</h3>
                    <ul>
                        <li 
                            className={isActiveMenu('policies') ? 'active' : ''}
                            onClick={() => handleMenuClick('policies')}
                        >
                            📋 정책 목록
                        </li>
                        <li onClick={() => handleMenuClick('policy-create')}>
                            ➕ 새 정책 등록
                        </li>
                    </ul>
                </div>

                <div className="menu-section">
                    <h3>주문 관리</h3>
                    <ul>
                        <li 
                            className={isActiveMenu('orders') ? 'active' : ''}
                            onClick={() => handleMenuClick('orders')}
                        >
                            📦 주문 목록
                        </li>
                        <li onClick={() => handleMenuClick('order-create')}>
                            ➕ 새 주문 등록
                        </li>
                    </ul>
                </div>

                <div className="menu-section">
                    <h3>재고 관리</h3>
                    <ul>
                        <li 
                            className={isActiveMenu('inventory') ? 'active' : ''}
                            onClick={() => handleMenuClick('inventory')}
                        >
                            📦 재고 목록
                        </li>
                        <li onClick={() => handleMenuClick('inventory-create')}>
                            ➕ 새 재고 등록
                        </li>
                    </ul>
                </div>

                <div className="menu-section">
                    <h3>메시지 관리</h3>
                    <ul>
                        <li 
                            className={isActiveMenu('messages') ? 'active' : ''}
                            onClick={() => handleMenuClick('messages')}
                        >
                            💬 메시지 목록
                        </li>
                        <li onClick={() => handleMenuClick('message-create')}>
                            ➕ 새 메시지 등록
                        </li>
                    </ul>
                </div>

                <div className="menu-section">
                    <h3>시스템</h3>
                    <ul>
                        <li 
                            className={isActiveMenu('settings') ? 'active' : ''}
                            onClick={() => handleMenuClick('settings')}
                        >
                            ⚙️ 시스템 설정
                        </li>
                        <li 
                            className={isActiveMenu('logs') ? 'active' : ''}
                            onClick={() => handleMenuClick('logs')}
                        >
                            📝 로그 보기
                        </li>
                    </ul>
                </div>
            </div>

            <div className="sidebar-footer">
                <div className="user-info">
                    <span className="username">{user?.username}</span>
                    <span className="role">{user?.role}</span>
                </div>
                <button className="logout-btn" onClick={handleLogout}>
                    🚪 로그아웃
                </button>
            </div>
        </div>
    );
};

export default Sidebar; 