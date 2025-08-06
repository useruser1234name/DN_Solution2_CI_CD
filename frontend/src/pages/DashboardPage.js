import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { get } from '../services/api';
import './DashboardPage.css';

const DashboardPage = () => {
    const { user } = useAuth();
    const [stats, setStats] = useState([]);
    const [recentActivities, setRecentActivities] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    console.log('[DashboardPage] 컴포넌트 렌더링', { user: user?.username });

    // fetchDashboardStats를 useCallback으로 감쌈
    const fetchDashboardStats = useCallback(async () => {
        console.log('[DashboardPage] 대시보드 데이터 가져오기 시작');
        
        try {
            setLoading(true);
            setError(null);
            
            console.log('[DashboardPage] API 호출 시작');
            const [statsResponse, activitiesResponse] = await Promise.all([
                get('dashboard/stats/'),
                get('dashboard/activities/')
            ]);

            console.log('[DashboardPage] API 응답 결과:', {
                stats: statsResponse,
                activities: activitiesResponse
            });

            console.log('[DashboardPage] 성공 여부 확인:', {
                statsSuccess: statsResponse.success,
                activitiesSuccess: activitiesResponse.success,
                statsData: statsResponse.data,
                activitiesData: activitiesResponse.data
            });

            if (statsResponse.success && activitiesResponse.success) {
                console.log('[DashboardPage] API 호출 성공, 데이터 변환 시작');
                
                // API 응답을 대시보드 형식으로 변환
                const apiStats = statsResponse.data;
                const statsData = [
                    {
                        title: '총 업체 수',
                        value: apiStats.total_companies?.toString() || '0',
                        icon: '🏢',
                        color: '#3498db'
                    },
                    {
                        title: '대기 중인 승인',
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
                        title: '재고 부족',
                        value: apiStats.low_stock_items?.toString() || '0',
                        icon: '⚠️',
                        color: '#e74c3c'
                    }
                ];

                console.log('[DashboardPage] 변환된 통계 데이터:', statsData);
                console.log('[DashboardPage] 활동 데이터:', activitiesResponse.data);

                setStats(statsData);
                setRecentActivities(activitiesResponse.data || []);
            } else {
                console.error('[DashboardPage] API 호출 실패:', {
                    statsError: statsResponse.message,
                    activitiesError: activitiesResponse.message
                });
                
                setError('데이터를 불러오는데 실패했습니다.');
                
                // API 실패 시 기본 데이터 사용
                const defaultStats = [
                    {
                        title: '총 업체 수',
                        value: '1',
                        icon: '🏢',
                        color: '#3498db'
                    },
                    {
                        title: '대기 중인 승인',
                        value: '0',
                        icon: '⏳',
                        color: '#f39c12'
                    },
                    {
                        title: '오늘의 주문',
                        value: '0',
                        icon: '📦',
                        color: '#27ae60'
                    },
                    {
                        title: '재고 부족',
                        value: '0',
                        icon: '⚠️',
                        color: '#e74c3c'
                    }
                ];
                
                setStats(defaultStats);
                setRecentActivities([
                    {
                        type: 'system',
                        message: 'API 연결 중...',
                        time: '방금 전'
                    }
                ]);
            }
        } catch (error) {
            console.error('[DashboardPage] 대시보드 데이터 로딩 실패:', error);
            setError('데이터를 불러오는 중 오류가 발생했습니다.');
            
            // 에러 시 기본 데이터 사용
            setStats([
                {
                    title: '총 업체 수',
                    value: '1',
                    icon: '🏢',
                    color: '#3498db'
                },
                {
                    title: '대기 중인 승인',
                    value: '0',
                    icon: '⏳',
                    color: '#f39c12'
                },
                {
                    title: '오늘의 주문',
                    value: '0',
                    icon: '📦',
                    color: '#27ae60'
                },
                {
                    title: '재고 부족',
                    value: '0',
                    icon: '⚠️',
                    color: '#e74c3c'
                }
            ]);
            setRecentActivities([
                {
                    type: 'system',
                    message: '시스템이 정상적으로 실행 중입니다.',
                    time: '방금 전'
                },
                {
                    type: 'user',
                    message: `관리자 ${user?.username || 'admin'}님이 로그인했습니다.`,
                    time: '방금 전'
                }
            ]);
        } finally {
            setLoading(false);
            console.log('[DashboardPage] 대시보드 데이터 로딩 완료');
        }
    }, [user]);

    useEffect(() => {
        if (!user || !user.token) return; // 로그인 안 했으면 API 호출 X
        fetchDashboardStats();
    }, [user, fetchDashboardStats]);

    if (loading) {
        console.log('[DashboardPage] 로딩 상태 렌더링');
        return (
            <div className="dashboard">
                <div className="dashboard-header">
                    <h1>대시보드</h1>
                    <p>데이터를 불러오는 중...</p>
                </div>
            </div>
        );
    }

    console.log('[DashboardPage] 메인 렌더링', { statsCount: stats.length, activitiesCount: recentActivities.length });

    return (
        <div className="dashboard">
            <div className="dashboard-header">
                <h1>대시보드</h1>
                <p>안녕하세요, {user?.username || '사용자'}님!</p>
                {error && (
                    <div className="error-message">
                        {error}
                    </div>
                )}
            </div>

            <div className="stats-grid">
                {stats.map((stat, index) => (
                    <div key={index} className="stat-card" style={{ borderLeftColor: stat.color }}>
                        <div className="stat-icon" style={{ backgroundColor: stat.color }}>
                            {stat.icon}
                        </div>
                        <div className="stat-content">
                            <h3 className="stat-value">{stat.value}</h3>
                            <p className="stat-title">{stat.title}</p>
                        </div>
                    </div>
                ))}
            </div>

            <div className="dashboard-content">
                <div className="content-section">
                    <h2>최근 활동</h2>
                    <div className="activity-list">
                        {recentActivities.length > 0 ? (
                            recentActivities.map((activity, index) => (
                                <div key={index} className="activity-item">
                                    <div className="activity-icon">
                                        {activity.type === 'company' && '🏢'}
                                        {activity.type === 'order' && '📦'}
                                        {activity.type === 'approval' && '✅'}
                                        {activity.type === 'inventory' && '📊'}
                                        {activity.type === 'system' && '⚙️'}
                                        {activity.type === 'user' && '👤'}
                                    </div>
                                    <div className="activity-content">
                                        <p className="activity-message">{activity.message}</p>
                                        <span className="activity-time">{activity.time}</span>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="no-activity">
                                <p>최근 활동이 없습니다.</p>
                            </div>
                        )}
                    </div>
                </div>

                <div className="content-section">
                    <h2>빠른 액션</h2>
                    <div className="quick-actions">
                        <button className="action-button" onClick={() => {
                            console.log('[DashboardPage] 새 업체 등록 버튼 클릭');
                            window.location.href = '/companies/create';
                        }}>
                            <span className="action-icon">➕</span>
                            <span>새 업체 등록</span>
                        </button>
                        <button className="action-button" onClick={() => {
                            console.log('[DashboardPage] 정책 관리 버튼 클릭');
                            window.location.href = '/policies';
                        }}>
                            <span className="action-icon">📋</span>
                            <span>정책 관리</span>
                        </button>
                        <button className="action-button" onClick={() => {
                            console.log('[DashboardPage] 주문 처리 버튼 클릭');
                            window.location.href = '/orders';
                        }}>
                            <span className="action-icon">📦</span>
                            <span>주문 처리</span>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DashboardPage; 