import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { get } from '../services/api';
import rolePermissions from '../utils/rolePermissions';
import {
    StatisticsWidget,
    RecentActivitiesWidget,
    CompanyHierarchyWidget,
    PendingOrdersWidget,
    SettlementSummaryWidget,
    PolicyStatusWidget,
    PendingUsersWidget,
    SystemAlertsWidget,
    UserInfoWidget
} from '../components/dashboard/DashboardWidgets';
import './DashboardPage.css';

const DashboardPage = () => {
    const { user } = useAuth();
    const [dashboardData, setDashboardData] = useState({
        stats: [],
        activities: [],
        companies: {},
        pendingOrders: [],
        settlements: {},
        policies: {},
        pendingUsers: [],
        systemAlerts: []
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    console.log('[DashboardPage] 컴포넌트 렌더링', { 
        user: user?.username,
        companyType: user?.company?.type,
        role: user?.role
    });

    // fetchDashboardData를 useCallback으로 감쌈
    const fetchDashboardData = useCallback(async () => {
        console.log('[DashboardPage] 대시보드 데이터 가져오기 시작');
        
        try {
            setLoading(true);
            setError(null);
            
            // 기본 데이터 가져오기
            const [statsResponse, activitiesResponse] = await Promise.all([
                get('api/dashboard/stats/'),
                get('api/dashboard/activities/')
            ]);

            console.log('[DashboardPage] API 응답 결과:', {
                stats: statsResponse,
                activities: activitiesResponse
            });

            if (statsResponse.success && activitiesResponse.success) {
                const apiStats = statsResponse.data;
                
                // 역할별 통계 데이터 구성
                let statsData = [];
                
                // 회사 타입별 통계 구성
                if (user?.company?.type === 'headquarters') {
                    // 본사 통계
                    statsData = [
                        {
                            title: '총 업체 수',
                            value: apiStats.total_companies?.toString() || '0',
                            icon: '🏢',
                            color: '#3498db'
                        },
                        {
                            title: '승인 대기',
                            value: apiStats.pending_approvals?.toString() || '0',
                            icon: '⏳',
                            color: '#f39c12'
                        },
                        {
                            title: '오늘의 주문',
                            value: apiStats.today_orders?.toString() || '0',
                            icon: '📦',
                            color: '#27ae60'
                        },
                        {
                            title: '활성 정책',
                            value: apiStats.active_policies?.toString() || '0',
                            icon: '📋',
                            color: '#9b59b6'
                        }
                    ];
                } else if (user?.company?.type === 'agency' || user?.company?.type === 'dealer') {
                    // 협력사/대리점 통계
                    statsData = [
                        {
                            title: '하위 업체 수',
                            value: apiStats.child_companies?.toString() || '0',
                            icon: '🏢',
                            color: '#3498db'
                        },
                        {
                            title: '할당된 정책',
                            value: apiStats.assigned_policies?.toString() || '0',
                            icon: '📋',
                            color: '#9b59b6'
                        },
                        {
                            title: '이번 달 정산',
                            value: apiStats.monthly_settlement?.toString() || '0',
                            icon: '💰',
                            color: '#27ae60'
                        },
                        {
                            title: '승인 대기',
                            value: apiStats.pending_approvals?.toString() || '0',
                            icon: '⏳',
                            color: '#f39c12'
                        }
                    ];
                } else if (user?.company?.type === 'retail') {
                    // 판매점 통계
                    statsData = [
                        {
                            title: '이번 달 주문',
                            value: apiStats.monthly_orders?.toString() || '0',
                            icon: '📦',
                            color: '#3498db'
                        },
                        {
                            title: '승인 대기',
                            value: apiStats.pending_orders?.toString() || '0',
                            icon: '⏳',
                            color: '#f39c12'
                        },
                        {
                            title: '이번 달 정산',
                            value: apiStats.monthly_settlement?.toString() || '0',
                            icon: '💰',
                            color: '#27ae60'
                        },
                        {
                            title: '할당된 정책',
                            value: apiStats.assigned_policies?.toString() || '0',
                            icon: '📋',
                            color: '#9b59b6'
                        }
                    ];
                }

                // 추가 데이터 구성 (실제로는 API에서 가져와야 함)
                const mockData = {
                    companies: {
                        agencies: apiStats.agency_count || 0,
                        dealers: apiStats.dealer_count || 0,
                        retailers: apiStats.retail_count || 0
                    },
                    pendingOrders: apiStats.pending_orders_list || [],
                    settlements: {
                        monthlyTotal: apiStats.monthly_settlement || 0,
                        pending: apiStats.pending_settlements || 0,
                        completed: apiStats.completed_settlements || 0
                    },
                    policies: {
                        active: apiStats.active_policies || 0,
                        expiring: apiStats.expiring_policies || 0,
                        new: apiStats.new_policies || 0
                    },
                    pendingUsers: apiStats.pending_users_list || [],
                    systemAlerts: apiStats.system_alerts || []
                };

                setDashboardData({
                    stats: statsData,
                    activities: activitiesResponse.data || [],
                    ...mockData
                });
            } else {
                console.error('[DashboardPage] API 호출 실패:', {
                    statsError: statsResponse.message,
                    activitiesError: activitiesResponse.message
                });
                
                setError('데이터를 불러오는데 실패했습니다.');
                
                // 기본 데이터 설정
                setDashboardData({
                    stats: [
                        {
                            title: '데이터 로딩 실패',
                            value: '-',
                            icon: '❌',
                            color: '#e74c3c'
                        }
                    ],
                    activities: [],
                    companies: {},
                    pendingOrders: [],
                    settlements: {},
                    policies: {},
                    pendingUsers: [],
                    systemAlerts: []
                });
            }
        } catch (err) {
            console.error('[DashboardPage] 대시보드 데이터 로드 실패:', err);
            setError('대시보드 데이터를 불러오는 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    }, [user]);

    useEffect(() => {
        console.log('[DashboardPage] useEffect 실행');
        fetchDashboardData();
    }, [fetchDashboardData]);

      // 역할별 표시할 위젯 결정
  const visibleWidgets = rolePermissions.getDashboardWidgets(user);
    console.log('[DashboardPage] 표시할 위젯:', visibleWidgets);

    if (loading) {
        return (
            <div className="dashboard-page">
                <div className="loading">대시보드 데이터를 불러오는 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="dashboard-page">
                <div className="error-message">{error}</div>
            </div>
        );
    }

    return (
        <div className="dashboard-page">
            <div className="dashboard-header">
                <h1>대시보드</h1>
                <p>안녕하세요, {user?.username}님!</p>
            </div>

            {/* 통계 위젯 (모든 사용자) */}
            {visibleWidgets.includes('statistics') && (
                <StatisticsWidget stats={dashboardData.stats} />
            )}

            <div className="dashboard-grid">
                {/* 사용자 정보 위젯 */}
                <UserInfoWidget user={user} />

                {/* 역할별 위젯 표시 */}
                {visibleWidgets.includes('companyHierarchy') && (
                    <CompanyHierarchyWidget companies={dashboardData.companies} />
                )}

                {visibleWidgets.includes('pendingOrders') && (
                    <PendingOrdersWidget orders={dashboardData.pendingOrders} />
                )}

                {visibleWidgets.includes('settlementSummary') && (
                    <SettlementSummaryWidget settlements={dashboardData.settlements} />
                )}

                {visibleWidgets.includes('policyStatus') && (
                    <PolicyStatusWidget policies={dashboardData.policies} />
                )}

                {visibleWidgets.includes('pendingUsers') && (
                    <PendingUsersWidget users={dashboardData.pendingUsers} />
                )}

                {visibleWidgets.includes('systemAlerts') && (
                    <SystemAlertsWidget alerts={dashboardData.systemAlerts} />
                )}

                {/* 최근 활동 위젯 (모든 사용자) */}
                {visibleWidgets.includes('recentActivities') && (
                    <RecentActivitiesWidget activities={dashboardData.activities} />
                )}
            </div>
        </div>
    );
};

export default DashboardPage;