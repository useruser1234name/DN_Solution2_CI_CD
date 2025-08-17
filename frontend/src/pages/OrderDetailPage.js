import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, post } from '../services/api';
import PermissionGuard from '../components/PermissionGuard';
import './OrderDetailPage.css';

const OrderDetailPage = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const { user } = useAuth();
    const [order, setOrder] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchOrder = async () => {
        try {
            setLoading(true);
            setError(null);
            
            const response = await get(`api/orders/${id}/`);
            if (response.success) {
                setOrder(response.data);
            } else {
                setError('주문 정보를 불러오는데 실패했습니다.');
            }
        } catch (error) {
            console.error('[OrderDetailPage] 주문 정보 로딩 실패:', error);
            setError('주문 정보를 불러오는 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (id) {
            fetchOrder();
        }
    }, [id]);

    const handleApproveOrder = async () => {
        if (!window.confirm('이 주문을 승인하시겠습니까?')) {
            return;
        }

        try {
            const response = await post(`orders/${id}/approve/`);
            if (response.success) {
                alert('주문이 승인되었습니다.');
                fetchOrder(); // 주문 정보 새로고침
            } else {
                alert(response.message || '주문 승인에 실패했습니다.');
            }
        } catch (error) {
            console.error('[OrderDetailPage] 주문 승인 실패:', error);
            alert('주문 승인 중 오류가 발생했습니다.');
        }
    };

    const handleRejectOrder = async () => {
        const reason = window.prompt('반려 사유를 입력하세요:');
        if (!reason) return;

        try {
            const response = await post(`orders/${id}/reject/`, { memo: reason });
            if (response.success) {
                alert('주문이 반려되었습니다.');
                fetchOrder(); // 주문 정보 새로고침
            } else {
                alert(response.message || '주문 반려에 실패했습니다.');
            }
        } catch (error) {
            console.error('[OrderDetailPage] 주문 반려 실패:', error);
            alert('주문 반려 중 오류가 발생했습니다.');
        }
    };

    const handleBackToList = () => {
        navigate('/orders');
    };

    const formatDate = (dateString) => {
        if (!dateString) return '-';
        return new Date(dateString).toLocaleString('ko-KR');
    };

    const getStatusBadge = (status) => {
        const statusMap = {
            'pending': { text: '접수대기', class: 'status-pending' },
            'processing': { text: '처리중', class: 'status-processing' },
            'shipped': { text: '배송중', class: 'status-shipped' },
            'completed': { text: '완료', class: 'status-completed' },
            'cancelled': { text: '취소', class: 'status-cancelled' }
        };
        
        const statusInfo = statusMap[status] || { text: status, class: 'status-unknown' };
        return <span className={`status-badge ${statusInfo.class}`}>{statusInfo.text}</span>;
    };

    if (loading) {
        return (
            <div className="order-detail-page">
                <div className="page-header">
                    <h1>📦 주문 상세</h1>
                </div>
                <div className="loading">로딩 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="order-detail-page">
                <div className="page-header">
                    <h1>📦 주문 상세</h1>
                    <button className="btn btn-secondary" onClick={handleBackToList}>
                        목록으로 돌아가기
                    </button>
                </div>
                <div className="error">{error}</div>
            </div>
        );
    }

    if (!order) {
        return (
            <div className="order-detail-page">
                <div className="page-header">
                    <h1>📦 주문 상세</h1>
                    <button className="btn btn-secondary" onClick={handleBackToList}>
                        목록으로 돌아가기
                    </button>
                </div>
                <div className="error">주문을 찾을 수 없습니다.</div>
            </div>
        );
    }

    return (
        <div className="order-detail-page">
            <div className="page-header">
                <h1>📦 주문 상세</h1>
                <div className="header-actions">
                    <button className="btn btn-secondary" onClick={handleBackToList}>
                        목록으로 돌아가기
                    </button>
                    {order.status === 'pending' && (
                        <PermissionGuard permission="canApproveOrders">
                            <button 
                                className="btn btn-success"
                                onClick={handleApproveOrder}
                            >
                                승인
                            </button>
                            <button 
                                className="btn btn-danger"
                                onClick={handleRejectOrder}
                            >
                                반려
                            </button>
                        </PermissionGuard>
                    )}
                </div>
            </div>

            <div className="order-detail-content">
                <div className="order-info-section">
                    <h2>주문 정보</h2>
                    <div className="info-grid">
                        <div className="info-item">
                            <label>주문 ID</label>
                            <span>{order.id}</span>
                        </div>
                        <div className="info-item">
                            <label>상태</label>
                            {getStatusBadge(order.status)}
                        </div>
                        <div className="info-item">
                            <label>정책명</label>
                            <span>{order.policy_title || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>업체명</label>
                            <span>{order.company_name || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>주문일시</label>
                            <span>{formatDate(order.created_at)}</span>
                        </div>
                        <div className="info-item">
                            <label>수정일시</label>
                            <span>{formatDate(order.updated_at)}</span>
                        </div>
                    </div>
                </div>

                <div className="customer-info-section">
                    <h2>고객 정보</h2>
                    <div className="info-grid">
                        <div className="info-item">
                            <label>고객명</label>
                            <span>{order.customer_name}</span>
                        </div>
                        <div className="info-item">
                            <label>연락처</label>
                            <span>{order.customer_phone}</span>
                        </div>
                        <div className="info-item">
                            <label>이메일</label>
                            <span>{order.customer_email || '-'}</span>
                        </div>
                        <div className="info-item full-width">
                            <label>주소</label>
                            <span>{order.customer_address}</span>
                        </div>
                    </div>
                </div>

                <div className="order-details-section">
                    <h2>주문 상세</h2>
                    <div className="info-grid">
                        <div className="info-item">
                            <label>총 금액</label>
                            <span>{order.total_amount ? `${Number(order.total_amount).toLocaleString()}원` : '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>리베이트 금액</label>
                            <span>{order.rebate_amount ? `${Number(order.rebate_amount).toLocaleString()}원` : '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>메모 수</label>
                            <span>{order.memo_count || 0}개</span>
                        </div>
                        <div className="info-item">
                            <label>송장 여부</label>
                            <span>{order.has_invoice ? '등록됨' : '미등록'}</span>
                        </div>
                        {order.notes && (
                            <div className="info-item full-width">
                                <label>메모</label>
                                <span>{order.notes}</span>
                            </div>
                        )}
                    </div>
                </div>

                {order.invoice_info && (
                    <div className="invoice-info-section">
                        <h2>송장 정보</h2>
                        <div className="info-grid">
                            <div className="info-item">
                                <label>택배사</label>
                                <span>{order.invoice_info.courier_display}</span>
                            </div>
                            <div className="info-item">
                                <label>송장번호</label>
                                <span>{order.invoice_info.invoice_number}</span>
                            </div>
                            <div className="info-item">
                                <label>발송일시</label>
                                <span>{formatDate(order.invoice_info.sent_at)}</span>
                            </div>
                            <div className="info-item">
                                <label>배송상태</label>
                                <span>{order.invoice_info.delivery_status}</span>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default OrderDetailPage;
