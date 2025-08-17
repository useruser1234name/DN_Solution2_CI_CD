import React from 'react';
import PermissionGuard from '../PermissionGuard';
import { getCompanyTypeLabel, getRoleLabel } from '../../utils/rolePermissions';

/**
 * 통계 위젯
 */
export const StatisticsWidget = ({ stats }) => {
    return (
        <div className="dashboard-stats">
            {stats.map((stat, index) => (
                <div key={index} className="stat-card" style={{ borderColor: stat.color }}>
                    <div className="stat-icon" style={{ color: stat.color }}>
                        {stat.icon}
                    </div>
                    <div className="stat-content">
                        <h3>{stat.title}</h3>
                        <p className="stat-value">{stat.value}</p>
                    </div>
                </div>
            ))}
        </div>
    );
};

/**
 * 최근 활동 위젯
 */
export const RecentActivitiesWidget = ({ activities }) => {
    return (
        <div className="recent-activities">
            <h2>최근 활동</h2>
            {activities.length > 0 ? (
                <ul className="activity-list">
                    {activities.map((activity, index) => (
                        <li key={index} className="activity-item">
                            <span className="activity-icon">{activity.icon}</span>
                            <div className="activity-content">
                                <p className="activity-description">{activity.description}</p>
                                <span className="activity-time">{activity.time}</span>
                            </div>
                        </li>
                    ))}
                </ul>
            ) : (
                <p className="no-data">최근 활동이 없습니다.</p>
            )}
        </div>
    );
};

/**
 * 회사 계층 구조 위젯 (본사, 협력사, 대리점용)
 */
export const CompanyHierarchyWidget = ({ companies }) => {
    return (
        <PermissionGuard anyPermissions={['canManageAgencies', 'canManageDealers', 'canManageRetailers']}>
            <div className="company-hierarchy-widget">
                <h2>하위 업체 현황</h2>
                <div className="hierarchy-stats">
                    <div className="hierarchy-item">
                        <span className="label">협력사</span>
                        <span className="value">{companies?.agencies || 0}</span>
                    </div>
                    <div className="hierarchy-item">
                        <span className="label">대리점</span>
                        <span className="value">{companies?.dealers || 0}</span>
                    </div>
                    <div className="hierarchy-item">
                        <span className="label">판매점</span>
                        <span className="value">{companies?.retailers || 0}</span>
                    </div>
                </div>
            </div>
        </PermissionGuard>
    );
};

/**
 * 승인 대기 주문 위젯 (본사용)
 */
export const PendingOrdersWidget = ({ orders }) => {
    return (
        <PermissionGuard permission="canApproveOrders">
            <div className="pending-orders-widget">
                <h2>승인 대기 주문</h2>
                {orders && orders.length > 0 ? (
                    <ul className="order-list">
                        {orders.slice(0, 5).map((order, index) => (
                            <li key={index} className="order-item">
                                <div className="order-info">
                                    <span className="order-id">#{order.id}</span>
                                    <span className="order-company">{order.company}</span>
                                </div>
                                <span className="order-amount">{order.amount}원</span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="no-data">승인 대기 중인 주문이 없습니다.</p>
                )}
            </div>
        </PermissionGuard>
    );
};

/**
 * 정산 요약 위젯
 */
export const SettlementSummaryWidget = ({ settlements }) => {
    return (
        <PermissionGuard anyPermissions={['canManageSettlements', 'canViewOwnSettlements']}>
            <div className="settlement-summary-widget">
                <h2>정산 현황</h2>
                <div className="settlement-stats">
                    <div className="settlement-item">
                        <span className="label">이번 달 정산액</span>
                        <span className="value">{settlements?.monthlyTotal || 0}원</span>
                    </div>
                    <div className="settlement-item">
                        <span className="label">대기 중</span>
                        <span className="value">{settlements?.pending || 0}건</span>
                    </div>
                    <div className="settlement-item">
                        <span className="label">완료</span>
                        <span className="value">{settlements?.completed || 0}건</span>
                    </div>
                </div>
            </div>
        </PermissionGuard>
    );
};

/**
 * 정책 현황 위젯 (본사용)
 */
export const PolicyStatusWidget = ({ policies }) => {
    return (
        <PermissionGuard permission="canManagePolicies">
            <div className="policy-status-widget">
                <h2>정책 현황</h2>
                <div className="policy-stats">
                    <div className="policy-item">
                        <span className="label">활성 정책</span>
                        <span className="value">{policies?.active || 0}</span>
                    </div>
                    <div className="policy-item">
                        <span className="label">만료 예정</span>
                        <span className="value">{policies?.expiring || 0}</span>
                    </div>
                    <div className="policy-item">
                        <span className="label">신규 등록</span>
                        <span className="value">{policies?.new || 0}</span>
                    </div>
                </div>
            </div>
        </PermissionGuard>
    );
};

/**
 * 승인 대기 사용자 위젯
 */
export const PendingUsersWidget = ({ users }) => {
    return (
        <PermissionGuard permission="canApproveUsers">
            <div className="pending-users-widget">
                <h2>승인 대기 사용자</h2>
                {users && users.length > 0 ? (
                    <ul className="user-list">
                        {users.slice(0, 5).map((user, index) => (
                            <li key={index} className="user-item">
                                <div className="user-info">
                                    <span className="user-name">{user.username}</span>
                                    <span className="user-company">{user.company}</span>
                                </div>
                                <span className="user-role">{getRoleLabel(user.role)}</span>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="no-data">승인 대기 중인 사용자가 없습니다.</p>
                )}
            </div>
        </PermissionGuard>
    );
};

/**
 * 시스템 알림 위젯 (본사용)
 */
export const SystemAlertsWidget = ({ alerts }) => {
    return (
        <PermissionGuard permission="canViewSystemLogs">
            <div className="system-alerts-widget">
                <h2>시스템 알림</h2>
                {alerts && alerts.length > 0 ? (
                    <ul className="alert-list">
                        {alerts.slice(0, 5).map((alert, index) => (
                            <li key={index} className={`alert-item ${alert.level}`}>
                                <span className="alert-icon">
                                    {alert.level === 'error' ? '❌' : 
                                     alert.level === 'warning' ? '⚠️' : 'ℹ️'}
                                </span>
                                <div className="alert-content">
                                    <p className="alert-message">{alert.message}</p>
                                    <span className="alert-time">{alert.time}</span>
                                </div>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="no-data">시스템 알림이 없습니다.</p>
                )}
            </div>
        </PermissionGuard>
    );
};

/**
 * 사용자 정보 위젯
 */
export const UserInfoWidget = ({ user }) => {
    return (
        <div className="user-info-widget">
            <h2>내 정보</h2>
            <div className="info-content">
                <div className="info-item">
                    <span className="label">사용자명</span>
                    <span className="value">{user?.username || 'N/A'}</span>
                </div>
                <div className="info-item">
                    <span className="label">회사</span>
                    <span className="value">{user?.company?.name || 'N/A'}</span>
                </div>
                <div className="info-item">
                    <span className="label">회사 유형</span>
                    <span className="value">{getCompanyTypeLabel(user?.company?.type) || 'N/A'}</span>
                </div>
                <div className="info-item">
                    <span className="label">역할</span>
                    <span className="value">{getRoleLabel(user?.role) || 'N/A'}</span>
                </div>
            </div>
        </div>
    );
};
