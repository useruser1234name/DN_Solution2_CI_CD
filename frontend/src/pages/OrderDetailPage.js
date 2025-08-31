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
                let data = response.data;
                if (data && data.data) {
                    data = data.data;
                }
                setOrder(data);
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
            const response = await post(`api/orders/${id}/approve/`);
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
            const response = await post(`api/orders/${id}/reject/`, { memo: reason });
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
            'approved': { text: '승인됨', class: 'status-approved' },
            'processing': { text: '개통준비중', class: 'status-processing' },
            'shipped': { text: '개통중', class: 'status-shipped' },
            'completed': { text: '개통완료', class: 'status-completed' },
            'final_approved': { text: '승인(완료)', class: 'status-final-approved' },
            'cancelled': { text: '개통취소', class: 'status-cancelled' }
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
                            <label>접수번호</label>
                            <span>{order.acceptance_number || order.order_number || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>접수일시</label>
                            <span>{order.acceptance_date || (order.received_date && new Date(order.received_date).toLocaleString('ko-KR')) || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>1차 ID</label>
                            <span>{order.first_id || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>판매점명</label>
                            <span>{order.retailer_name || order.company_name || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>통신사</label>
                            <span>{order.carrier || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>가입유형</label>
                            <span>{order.subscription_type || '-'}</span>
                        </div>
                        <div className="info-item full-width">
                            <label>참조 URL</label>
                            {order.reference_url ? (
                                <a href={order.reference_url} target="_blank" rel="noreferrer">{order.reference_url}</a>
                            ) : (
                                <span>-</span>
                            )}
                        </div>
                        <div className="info-item">
                            <label>요금제</label>
                            <span>{order.plan_name || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>약정기간</label>
                            <span>{order.contract_period_selected || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>단말 모델</label>
                            <span>{order.device_model || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>일련번호</label>
                            <span>{order.device_serial || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>IMEI</label>
                            <span>{order.imei || '-'}</span>
                        </div>
                        {order.imei2 && (
                            <div className="info-item">
                                <label>IMEI2</label>
                                <span>{order.imei2}</span>
                            </div>
                        )}
                        {order.eid && (
                            <div className="info-item">
                                <label>EID</label>
                                <span>{order.eid}</span>
                            </div>
                        )}
                        {order.usim_serial && (
                            <div className="info-item">
                                <label>유심 일련번호</label>
                                <span>{order.usim_serial}</span>
                            </div>
                        )}
                        <div className="info-item">
                            <label>이전 통신사</label>
                            <span>{order.previous_carrier || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>결제방법</label>
                            <span>{order.payment_method || '-'}</span>
                        </div>
                        {order.account_number_masked && (
                            <div className="info-item">
                                <label>계좌(마스킹)</label>
                                <span>{order.account_number_masked}</span>
                            </div>
                        )}
                        {order.card_number_masked && (
                            <div className="info-item">
                                <label>카드(마스킹)</label>
                                <span>{order.card_number_masked}{order.card_exp_mmyy ? ` (${order.card_exp_mmyy})` : ''}</span>
                            </div>
                        )}
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
