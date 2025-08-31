import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, post } from '../services/api';
import PermissionGuard from '../components/PermissionGuard';
import './OrderListPage.css';

const OrderListPage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [orders, setOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all');
    const [dateRange, setDateRange] = useState(() => {
        const d = new Date();
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const today = `${yyyy}-${mm}-${dd}`;
        return { start: today, end: today };
    });
    const [editedStatuses, setEditedStatuses] = useState({});

    console.log('[OrderListPage] 컴포넌트 렌더링', {
        user: user?.username,
        companyType: user?.company?.type
    });

    const fetchOrders = async () => {
        console.log('[OrderListPage] 주문 목록 가져오기 시작');
        
        try {
            setLoading(true);
            setError(null);
            
            const response = await get('api/orders/');
            console.log('[OrderListPage] 주문 목록 응답:', response);

            if (response.success) {
                const data = response.data;
                // 배열인지 확인하고 배열이 아니면 빈 배열로 설정
                let ordersArray = [];
                if (Array.isArray(data)) {
                    ordersArray = data;
                } else if (data && Array.isArray(data.results)) {
                    ordersArray = data.results;
                } else if (data && data.data && Array.isArray(data.data)) {
                    ordersArray = data.data;
                } else {
                    console.warn('[OrderListPage] 예상하지 못한 데이터 형태:', data);
                    ordersArray = [];
                }
                setOrders(ordersArray);
                console.log('[OrderListPage] 설정된 주문 목록:', ordersArray);
            } else {
                console.error('[OrderListPage] 주문 목록 실패:', response.message);
                setError('주문 목록을 불러오는데 실패했습니다.');
                setOrders([]); // 실패 시에도 빈 배열 설정
            }
        } catch (error) {
            console.error('[OrderListPage] 주문 목록 로딩 실패:', error);
            setError('주문 목록을 불러오는 중 오류가 발생했습니다.');
            setOrders([]); // 에러 시에도 빈 배열 설정
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOrders();
    }, []);

    const handleCreateOrder = () => {
        navigate('/orders/create');
    };

    const handleViewOrder = (orderId) => {
        navigate(`/orders/${orderId}`);
    };

    const handleApproveOrder = async (orderId) => {
        if (!window.confirm('이 주문을 승인하시겠습니까?')) {
            return;
        }

        try {
            const response = await post(`api/orders/${orderId}/approve/`);
            if (response.success) {
                // 승인 성공 후 목록 새로고침 (알림 미표시)
                fetchOrders();
            } else {
                alert(response.message || '주문 승인에 실패했습니다.');
            }
        } catch (error) {
            console.error('[OrderListPage] 주문 승인 실패:', error);
            alert('주문 승인 중 오류가 발생했습니다.');
        }
    };

    const handleFinalApprove = async (orderId) => {
        if (!window.confirm('이 주문을 최종 승인하여 정산을 생성하시겠습니까?')) {
            return;
        }

        try {
            const response = await post(`api/orders/${orderId}/final_approve/`);
            if (response.success) {
                alert('주문이 최종 승인되어 정산이 생성되었습니다.');
                fetchOrders();
            } else {
                alert(response.message || '최종 승인에 실패했습니다.');
            }
        } catch (error) {
            console.error('[OrderListPage] 최종 승인 실패:', error);
            alert('최종 승인 중 오류가 발생했습니다.');
        }
    };

    // 백엔드 전이 규칙에 맞춰 중간 단계를 자동 진행
    const validTransitions = {
        'pending': ['approved', 'cancelled'],
        'approved': ['processing', 'cancelled'],
        'processing': ['shipped', 'cancelled'],
        'shipped': ['completed', 'cancelled'],
        'completed': ['final_approved', 'cancelled'],
        'final_approved': [],
        'cancelled': []
    };

    const buildTransitionPath = (current, target) => {
        if (current === target) return [];
        // 간단한 단계적 경로 구성
        const order = ['pending','approved','processing','shipped','completed','final_approved'];
        const ci = order.indexOf(current);
        const ti = order.indexOf(target);
        if (ci === -1 || ti === -1) return [target];
        if (ti < ci) return [target]; // 역방향(취소 등)은 단일 시도
        const path = [];
        for (let i = ci; i < ti; i++) {
            const next = order[i+1];
            if (!validTransitions[order[i]]?.includes(next)) break;
            path.push(next);
        }
        // 마지막 단계가 목표가 아니면 직접 목표도 시도
        if (path[path.length - 1] !== target) path.push(target);
        return path;
    };

    const handleUpdateStatus = async (order, targetStatus) => {
        try {
            const current = order.status;
            const path = buildTransitionPath(current, targetStatus);
            for (const step of path) {
                await post(`api/orders/${order.id}/update_status/`, { status: step, reason: '' });
            }
            setEditedStatuses(prev => ({ ...prev, [order.id]: undefined }));
            fetchOrders();
        } catch (error) {
            console.error('[OrderListPage] 상태 변경 실패:', error);
            alert('상태 변경 중 오류가 발생했습니다.');
        }
    };

    const statusOptions = [
        { value: 'pending', label: '접수대기' },
        { value: 'approved', label: '접수준비' },
        { value: 'processing', label: '접수중' },
        { value: 'shipped', label: '접수 완료' },
        { value: 'completed', label: '개통완료' },
        { value: 'final_approved', label: '개통 승인' },
        { value: 'cancelled', label: '개통취소' }
    ];


    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('ko-KR');
    };

    const formatAmount = (amount) => {
        return new Intl.NumberFormat('ko-KR').format(amount);
    };

    const toYMD = (dateLike) => {
        try {
            const iso = typeof dateLike === 'string' && dateLike.includes(' ') ? dateLike.replace(' ', 'T') : dateLike;
            const d = new Date(iso);
            if (isNaN(d.getTime())) return '';
            const yyyy = d.getFullYear();
            const mm = String(d.getMonth() + 1).padStart(2, '0');
            const dd = String(d.getDate()).padStart(2, '0');
            return `${yyyy}-${mm}-${dd}`;
        } catch (_) {
            return '';
        }
    };

    const filteredOrders = orders.filter(order => {
        const statusOk = filter === 'all' ? true : order.status === filter;
        const ymd = toYMD(order.created_at);
        const afterStart = !dateRange.start || ymd >= dateRange.start;
        const beforeEnd = !dateRange.end || ymd <= dateRange.end;
        return statusOk && afterStart && beforeEnd;
    });

    if (loading) {
        return (
            <div className="order-list-page">
                <div className="loading">주문 목록을 불러오는 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="order-list-page">
                <div className="error-message">{error}</div>
            </div>
        );
    }

    return (
        <div className="order-list-page">
            <div className="page-header">
                <div className="header-content">
                    <h1>주문 관리</h1>
                    <p>주문을 조회하고 관리할 수 있습니다.</p>
                </div>
                <PermissionGuard permission="canCreateOrders">
                    <div className="header-actions">
                        <button 
                            className="btn btn-primary"
                            onClick={handleCreateOrder}
                        >
                            새 주문 생성
                        </button>
                    </div>
                </PermissionGuard>
            </div>

            <div className="filter-bar">
                <div className="filter-buttons">
                    <button 
                        className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                        onClick={() => setFilter('all')}
                    >
                        전체 ({orders.length})
                    </button>
                    <button 
                        className={`filter-btn ${filter === 'pending' ? 'active' : ''}`}
                        onClick={() => setFilter('pending')}
                    >
                        대기 ({orders.filter(o => o.status === 'pending').length})
                    </button>
                    <button 
                        className={`filter-btn ${filter === 'approved' ? 'active' : ''}`}
                        onClick={() => setFilter('approved')}
                    >
                        승인 ({orders.filter(o => o.status === 'approved').length})
                    </button>
                    <button 
                        className={`filter-btn ${filter === 'completed' ? 'active' : ''}`}
                        onClick={() => setFilter('completed')}
                    >
                        개통완료 ({orders.filter(o => o.status === 'completed').length})
                    </button>
                    <button 
                        className={`filter-btn ${filter === 'final_approved' ? 'active' : ''}`}
                        onClick={() => setFilter('final_approved')}
                    >
                        승인완료 ({orders.filter(o => o.status === 'final_approved').length})
                    </button>
                </div>
                <div className="filter-date" style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                    <label>주문일</label>
                    <input 
                        type="date" 
                        value={dateRange.start} 
                        onChange={(e) => setDateRange(r => ({ ...r, start: e.target.value }))}
                    />
                    <span>~</span>
                    <input 
                        type="date" 
                        value={dateRange.end} 
                        onChange={(e) => setDateRange(r => ({ ...r, end: e.target.value }))}
                    />
                    <button className="btn btn-small" onClick={() => setDateRange(() => {
                        const d = new Date();
                        const yyyy = d.getFullYear();
                        const mm = String(d.getMonth() + 1).padStart(2, '0');
                        const dd = String(d.getDate()).padStart(2, '0');
                        const today = `${yyyy}-${mm}-${dd}`;
                        return { start: today, end: today };
                    })}>오늘</button>
                    <button className="btn btn-small" onClick={() => setDateRange(() => {
                        const d = new Date();
                        const yyyy = d.getFullYear();
                        const mm = String(d.getMonth() + 1).padStart(2, '0');
                        const dd = String(d.getDate()).padStart(2, '0');
                        const today = `${yyyy}-${mm}-${dd}`;
                        const first = `${yyyy}-${mm}-01`;
                        return { start: first, end: today };
                    })}>이번달</button>
                </div>
            </div>

            <div className="orders-container">
                {filteredOrders.length === 0 ? (
                    <div className="no-data">
                        <p>주문이 없습니다.</p>
                        <PermissionGuard permission="canCreateOrders">
                            <button 
                                className="btn btn-primary"
                                onClick={handleCreateOrder}
                            >
                                첫 주문 만들기
                            </button>
                        </PermissionGuard>
                    </div>
                ) : (
                    <div className="orders-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>고객명</th>
                                    <th>전화번호</th>
                                    <th>정책명</th>
                                    <th>요금제</th>
                                    <th>약정기간</th>
                                    <th>상태</th>
                                    <th>주문일</th>
                                    <th>작업</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredOrders.map(order => (
                                    <tr key={order.id}>
                                        <td>{order.customer_name || '-'}</td>
                                        <td>{order.activation_phone || order.phone_number || '-'}</td>
                                        <td>{order.policy_title || '-'}</td>
                                        <td>{order.plan_name || '-'}</td>
                                        <td>{order.contract_period_selected || '-'}</td>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                                <select
                                                    value={editedStatuses[order.id] ?? order.status}
                                                    onChange={(e) => setEditedStatuses(prev => ({ ...prev, [order.id]: e.target.value }))}
                                                >
                                                    {statusOptions.map(opt => (
                                                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                                                    ))}
                                                </select>
                                                <button
                                                    className="btn btn-small btn-primary"
                                                    onClick={() => handleUpdateStatus(order, editedStatuses[order.id] ?? order.status)}
                                                >
                                                    저장
                                                </button>
                                            </div>
                                        </td>
                                        <td>{formatDate(order.created_at)}</td>
                                        <td>
                                            <button 
                                                className="btn btn-small btn-secondary"
                                                onClick={() => handleViewOrder(order.id)}
                                            >
                                                자세히 보기
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default OrderListPage;
