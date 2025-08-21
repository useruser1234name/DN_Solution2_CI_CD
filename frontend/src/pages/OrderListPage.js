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
            const response = await post(`orders/${orderId}/approve/`);
            if (response.success) {
                alert('주문이 승인되었습니다.');
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

    const handleUpdateStatus = async (orderId, status) => {
        const statusName = {
            'processing': '개통 준비중',
            'shipped': '개통중',
            'completed': '개통완료',
            'cancelled': '개통취소'
        }[status] || status;

        // 상태 변경 사유 입력 (취소의 경우 필수)
        let reason = '';
        if (status === 'cancelled') {
            reason = prompt('취소 사유를 입력해주세요:');
            if (reason === null) {
                return; // 취소
            }
            if (!reason.trim()) {
                alert('취소 사유는 필수입니다.');
                return;
            }
        } else {
            // 다른 상태는 선택적
            reason = prompt(`주문 상태를 '${statusName}'로 변경하는 사유를 입력해주세요 (선택사항):`) || '';
        }

        if (!window.confirm(`주문 상태를 '${statusName}'(으)로 변경하시겠습니까?`)) {
            return;
        }

        try {
            const response = await post(`api/orders/${orderId}/update_status/`, { 
                status,
                reason: reason?.trim() || ''
            });
            if (response.success) {
                alert(`주문 상태가 '${statusName}'(으)로 변경되었습니다.`);
                fetchOrders();
            } else {
                alert(response.message || '상태 변경에 실패했습니다.');
            }
        } catch (error) {
            console.error('[OrderListPage] 상태 변경 실패:', error);
            alert('상태 변경 중 오류가 발생했습니다.');
        }
    };

    const getStatusBadge = (status) => {
        const statusMap = {
            'pending': { label: '접수대기', className: 'pending' },
            'approved': { label: '승인됨', className: 'approved' },
            'processing': { label: '개통준비중', className: 'processing' },
            'shipped': { label: '개통중', className: 'shipped' },
            'completed': { label: '개통완료', className: 'completed' },
            'final_approved': { label: '승인(완료)', className: 'final-approved' },
            'cancelled': { label: '개통취소', className: 'cancelled' }
        };
        
        const statusInfo = statusMap[status] || { label: status, className: 'default' };
        return <span className={`badge ${statusInfo.className}`}>{statusInfo.label}</span>;
    };

    const formatDate = (dateString) => {
        return new Date(dateString).toLocaleDateString('ko-KR');
    };

    const formatAmount = (amount) => {
        return new Intl.NumberFormat('ko-KR').format(amount);
    };

    const filteredOrders = orders.filter(order => {
        if (filter === 'all') return true;
        return order.status === filter;
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
                                    <th>주문번호</th>
                                    <th>고객명</th>
                                    <th>정책</th>
                                    <th>금액</th>
                                    <th>상태</th>
                                    <th>주문일</th>
                                    <th>작업</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredOrders.map(order => (
                                    <tr key={order.id}>
                                        <td>
                                            <span className="order-number">#{order.order_number || order.id.slice(0, 8)}</span>
                                        </td>
                                        <td>{order.customer_name || '-'}</td>
                                        <td>{order.policy_name || '-'}</td>
                                        <td className="amount">{formatAmount(order.amount || 0)}원</td>
                                        <td>{getStatusBadge(order.status)}</td>
                                        <td>{formatDate(order.created_at)}</td>
                                        <td>
                                            <div className="action-buttons">
                                                <button 
                                                    className="btn btn-small btn-secondary"
                                                    onClick={() => handleViewOrder(order.id)}
                                                >
                                                    보기
                                                </button>
                                                {order.status === 'pending' && (
                                                    <PermissionGuard permission="canApproveOrders">
                                                        <button 
                                                            className="btn btn-small btn-success"
                                                            onClick={() => handleApproveOrder(order.id)}
                                                        >
                                                            승인
                                                        </button>
                                                    </PermissionGuard>
                                                )}
                                                {order.status === 'approved' && (
                                                    <PermissionGuard permission="canApproveOrders">
                                                        <button 
                                                            className="btn btn-small btn-info"
                                                            onClick={() => handleUpdateStatus(order.id, 'processing')}
                                                        >
                                                            개통준비
                                                        </button>
                                                    </PermissionGuard>
                                                )}
                                                {order.status === 'processing' && (
                                                    <PermissionGuard permission="canApproveOrders">
                                                        <button 
                                                            className="btn btn-small btn-info"
                                                            onClick={() => handleUpdateStatus(order.id, 'shipped')}
                                                        >
                                                            개통시작
                                                        </button>
                                                    </PermissionGuard>
                                                )}
                                                {order.status === 'shipped' && (
                                                    <PermissionGuard permission="canApproveOrders">
                                                        <button 
                                                            className="btn btn-small btn-success"
                                                            onClick={() => handleUpdateStatus(order.id, 'completed')}
                                                        >
                                                            개통완료
                                                        </button>
                                                    </PermissionGuard>
                                                )}
                                                {order.status === 'completed' && (
                                                    <PermissionGuard permission="canApproveOrders">
                                                        <button 
                                                            className="btn btn-small btn-primary"
                                                            onClick={() => handleFinalApprove(order.id)}
                                                        >
                                                            최종승인
                                                        </button>
                                                    </PermissionGuard>
                                                )}
                                                {(order.status === 'pending' || order.status === 'approved' || order.status === 'processing' || order.status === 'shipped') && (
                                                    <PermissionGuard permission="canApproveOrders">
                                                        <button 
                                                            className="btn btn-small btn-danger"
                                                            onClick={() => handleUpdateStatus(order.id, 'cancelled')}
                                                        >
                                                            취소
                                                        </button>
                                                    </PermissionGuard>
                                                )}
                                            </div>
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
