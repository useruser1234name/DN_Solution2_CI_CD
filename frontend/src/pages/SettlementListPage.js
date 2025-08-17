import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, post } from '../services/api';
import PermissionGuard from '../components/PermissionGuard';
import RebateSummary from '../components/RebateSummary';
import './SettlementListPage.css';

const SettlementListPage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [settlements, setSettlements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [filter, setFilter] = useState('all');
    const [summary, setSummary] = useState({
        total: 0,
        pending: 0,
        approved: 0,
        paid: 0
    });

    console.log('[SettlementListPage] 컴포넌트 렌더링', {
        user: user?.username,
        companyType: user?.company?.type
    });

    const fetchSettlements = async () => {
        console.log('[SettlementListPage] 정산 목록 가져오기 시작');
        
        try {
            setLoading(true);
            setError(null);
            
            const response = await get('api/settlements/');
            console.log('[SettlementListPage] 정산 목록 응답:', response);

            if (response.success) {
                const data = response.data;
                // DRF 페이지네이션 구조 처리
                let settlementsArray = [];
                if (Array.isArray(data)) {
                    settlementsArray = data;
                } else if (data && Array.isArray(data.results)) {
                    settlementsArray = data.results;
                } else if (data && data.data && Array.isArray(data.data)) {
                    settlementsArray = data.data;
                } else if (data && typeof data === 'object' && data.settlements) {
                    // 백엔드에서 settlements 키로 반환하는 경우
                    console.log('[SettlementListPage] settlements 키 발견:', data.settlements);
                    settlementsArray = [];
                } else {
                    console.warn('[SettlementListPage] 예상하지 못한 데이터 형태:', data);
                    settlementsArray = [];
                }
                setSettlements(settlementsArray);
                console.log('[SettlementListPage] 설정된 정산 목록:', settlementsArray);
                
                // 요약 정보 계산 (rebate_amount 필드 사용)
                const summaryData = {
                    total: settlementsArray.reduce((sum, s) => sum + parseFloat(s.rebate_amount || 0), 0),
                    pending: settlementsArray.filter(s => s.status === 'pending').reduce((sum, s) => sum + parseFloat(s.rebate_amount || 0), 0),
                    approved: settlementsArray.filter(s => s.status === 'approved').reduce((sum, s) => sum + parseFloat(s.rebate_amount || 0), 0),
                    paid: settlementsArray.filter(s => s.status === 'paid').reduce((sum, s) => sum + parseFloat(s.rebate_amount || 0), 0)
                };
                setSummary(summaryData);
            } else {
                console.error('[SettlementListPage] 정산 목록 실패:', response.message);
                setError('정산 목록을 불러오는데 실패했습니다.');
                setSettlements([]); // 실패 시에도 빈 배열 설정
            }
        } catch (error) {
            console.error('[SettlementListPage] 정산 목록 로딩 실패:', error);
            setError('정산 목록을 불러오는 중 오류가 발생했습니다.');
            setSettlements([]); // 에러 시에도 빈 배열 설정
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSettlements();
    }, []);

    const handleViewReport = () => {
        navigate('/settlements/report');
    };

    const handleApproveSettlement = async (settlementId) => {
        if (!window.confirm('이 정산을 승인하시겠습니까?')) {
            return;
        }

        try {
            const response = await post(`settlements/${settlementId}/approve/`);
            if (response.success) {
                alert('정산이 승인되었습니다.');
                fetchSettlements();
            } else {
                alert(response.message || '정산 승인에 실패했습니다.');
            }
        } catch (error) {
            console.error('[SettlementListPage] 정산 승인 실패:', error);
            alert('정산 승인 중 오류가 발생했습니다.');
        }
    };

    const handlePaySettlement = async (settlementId) => {
        if (!window.confirm('이 정산을 지급 완료 처리하시겠습니까?')) {
            return;
        }

        try {
            const response = await post(`settlements/${settlementId}/pay/`);
            if (response.success) {
                alert('정산이 지급 완료 처리되었습니다.');
                fetchSettlements();
            } else {
                alert(response.message || '정산 지급 처리에 실패했습니다.');
            }
        } catch (error) {
            console.error('[SettlementListPage] 정산 지급 처리 실패:', error);
            alert('정산 지급 처리 중 오류가 발생했습니다.');
        }
    };

    const getStatusBadge = (status) => {
        const statusMap = {
            'pending': { label: '대기', className: 'pending' },
            'approved': { label: '승인', className: 'approved' },
            'paid': { label: '지급완료', className: 'paid' },
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

    const filteredSettlements = settlements.filter(settlement => {
        if (filter === 'all') return true;
        return settlement.status === filter;
    });

    if (loading) {
        return (
            <div className="settlement-list-page">
                <div className="loading">정산 목록을 불러오는 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="settlement-list-page">
                <div className="error-message">{error}</div>
            </div>
        );
    }

    return (
        <div className="settlement-list-page">
            <div className="page-header">
                <div className="header-content">
                    <h1>정산 관리</h1>
                    <p>정산 내역을 조회하고 관리할 수 있습니다.</p>
                </div>
                <div className="header-actions">
                    <button 
                        className="btn btn-secondary"
                        onClick={handleViewReport}
                    >
                        정산 보고서
                    </button>
                </div>
            </div>

            {/* 협력사용 리베이트 요약 */}
            <RebateSummary />

            <div className="settlement-summary">
                <div className="summary-card">
                    <h3>전체 정산액</h3>
                    <p className="amount">{formatAmount(summary.total)}원</p>
                </div>
                <div className="summary-card">
                    <h3>대기 중</h3>
                    <p className="amount pending">{formatAmount(summary.pending)}원</p>
                </div>
                <div className="summary-card">
                    <h3>승인됨</h3>
                    <p className="amount approved">{formatAmount(summary.approved)}원</p>
                </div>
                <div className="summary-card">
                    <h3>지급완료</h3>
                    <p className="amount paid">{formatAmount(summary.paid)}원</p>
                </div>
            </div>

            <div className="filter-bar">
                <div className="filter-buttons">
                    <button 
                        className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
                        onClick={() => setFilter('all')}
                    >
                        전체 ({settlements.length})
                    </button>
                    <button 
                        className={`filter-btn ${filter === 'pending' ? 'active' : ''}`}
                        onClick={() => setFilter('pending')}
                    >
                        대기 ({settlements.filter(s => s.status === 'pending').length})
                    </button>
                    <button 
                        className={`filter-btn ${filter === 'approved' ? 'active' : ''}`}
                        onClick={() => setFilter('approved')}
                    >
                        승인 ({settlements.filter(s => s.status === 'approved').length})
                    </button>
                    <button 
                        className={`filter-btn ${filter === 'paid' ? 'active' : ''}`}
                        onClick={() => setFilter('paid')}
                    >
                        지급완료 ({settlements.filter(s => s.status === 'paid').length})
                    </button>
                </div>
            </div>

            <div className="settlements-container">
                {filteredSettlements.length === 0 ? (
                    <div className="no-data">
                        <p>정산 내역이 없습니다.</p>
                    </div>
                ) : (
                    <div className="settlements-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>정산번호</th>
                                    <th>주문번호</th>
                                    <th>업체명</th>
                                    <th>정산액</th>
                                    <th>상태</th>
                                    <th>생성일</th>
                                    <th>작업</th>
                                </tr>
                            </thead>
                            <tbody>
                                {filteredSettlements.map(settlement => (
                                    <tr key={settlement.id}>
                                        <td>
                                            <span className="settlement-number">
                                                #{settlement.settlement_number || settlement.id.slice(0, 8)}
                                            </span>
                                        </td>
                                        <td>{settlement.order_number || '-'}</td>
                                        <td>{settlement.company_name || '-'}</td>
                                        <td className="amount">{formatAmount(settlement.rebate_amount || 0)}원</td>
                                        <td>{getStatusBadge(settlement.status)}</td>
                                        <td>{formatDate(settlement.created_at)}</td>
                                        <td>
                                            <div className="action-buttons">
                                                {settlement.status === 'pending' && (
                                                    <PermissionGuard permission="canManageSettlements">
                                                        <button 
                                                            className="btn btn-small btn-success"
                                                            onClick={() => handleApproveSettlement(settlement.id)}
                                                        >
                                                            승인
                                                        </button>
                                                    </PermissionGuard>
                                                )}
                                                {settlement.status === 'approved' && (
                                                    <PermissionGuard permission="canManageSettlements">
                                                        <button 
                                                            className="btn btn-small btn-primary"
                                                            onClick={() => handlePaySettlement(settlement.id)}
                                                        >
                                                            지급완료
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

export default SettlementListPage;
