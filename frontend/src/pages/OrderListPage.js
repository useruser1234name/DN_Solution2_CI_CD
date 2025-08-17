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

    const handleRejectOrder = async (orderId) => {
        const reason = window.prompt('반려 사유를 입력하세요:');
        if (!reason) return;

        try {
            const response = await post(`orders/${orderId}/reject/`, { reason });
            if (response.success) {
                alert('주문이 반려되었습니다.');
                fetchOrders();
            } else {
                alert(response.message || '주문 반려에 실패했습니다.');
            }
        } catch (error) {
            console.error('[OrderListPage] 주문 반려 실패:', error);
            alert('주문 반려 중 오류가 발생했습니다.');
        }
    };

    const getStatusBadge = (status) => {
        const statusMap = {
            'pending': { label: '대기', className: 'pending' },
            'approved': { label: '승인', className: 'approved' },
            'rejected': { label: '반려', className: 'rejected' },
            'completed': { label: '완료', className: 'completed' },
            'cancelled': { label: '취소', className: 'cancelled' }
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
                        className={`filter-btn ${filter === 'rejected' ? 'active' : ''}`}
                        onClick={() => setFilter('rejected')}
                    >
                        반려 ({orders.filter(o => o.status === 'rejected').length})
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
                                                        <button 
                                                            className="btn btn-small btn-danger"
                                                            onClick={() => handleRejectOrder(order.id)}
                                                        >
                                                            반려
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
