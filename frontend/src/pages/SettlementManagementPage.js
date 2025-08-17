import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { get, post } from '../services/api';
import './SettlementManagementPage.css';

const SettlementManagementPage = () => {
    const { user } = useAuth();
  const [settlements, setSettlements] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [dateRange, setDateRange] = useState({
        start_date: '',
        end_date: ''
    });
      const [stats, setStats] = useState({
        totalReceivable: 0,
        totalPayable: 0,
        pendingCount: 0,
        paidCount: 0
    });
    
    // 본사용 추가 리베이트 통계
    const [rebateStats, setRebateStats] = useState({
        total_policies: 0,
        participating_stores: 0,
        total_rebate_amount: 0
    });

    useEffect(() => {
        fetchSettlements();
        // 본사인 경우 리베이트 통계도 로드
        if (user?.companyType === 'headquarters') {
            fetchRebateStats();
        }
    }, [user?.companyType]);

    const fetchSettlements = async () => {
        try {
    setLoading(true);
            setError(null);
            const response = await get('api/settlements/');
            if (response.success) {
                // DRF 페이지네이션 구조 처리
                let settlementsData = [];
                if (response.data && response.data.results) {
                    settlementsData = response.data.results;
                } else if (Array.isArray(response.data)) {
                    settlementsData = response.data;
                } else {
                    console.warn('예상하지 못한 정산 데이터 구조:', response.data);
                    settlementsData = [];
                }
                
                setSettlements(settlementsData);
                calculateStats(settlementsData);
            } else {
                setError(response.message || '정산 목록을 불러오는데 실패했습니다.');
            }
        } catch (err) {
            setError('정산 목록을 불러오는 중 오류가 발생했습니다.');
            console.error('Failed to fetch settlements:', err);
    } finally {
      setLoading(false);
    }
    };

    // 본사용 리베이트 통계 로드
    const fetchRebateStats = async () => {
        try {
            const response = await get('api/policies/rebate/summary/');
            if (response.success && response.data) {
                setRebateStats({
                    total_policies: response.data.summary?.total_policies || 0,
                    participating_stores: response.data.summary?.participating_stores || 0,
                    total_rebate_amount: response.data.summary?.total_payable || 0
                });
            }
        } catch (error) {
            console.error('리베이트 통계 로드 실패:', error);
        }
    };

  const calculateStats = (data) => {
        const userCompanyType = user?.companyType;
        let totalReceivable = 0;
        let totalPayable = 0;
        let pendingCount = 0;
        let paidCount = 0;

        data.forEach(settlement => {
            if (settlement.status === 'approved') {
                if (userCompanyType === 'headquarters') {
                    // 본사는 지급할 금액만
                    totalPayable += parseFloat(settlement.rebate_amount || 0);
                } else if (userCompanyType === 'agency') {
                    // 협력사는 받을 금액과 지급할 금액 모두
                    if (settlement.company_id === user?.companyId) {
                        totalReceivable += parseFloat(settlement.rebate_amount || 0);
                    } else {
                        totalPayable += parseFloat(settlement.rebate_amount || 0);
                    }
                } else if (userCompanyType === 'retail') {
                    // 판매점은 받을 금액만
                    totalReceivable += parseFloat(settlement.rebate_amount || 0);
                }
            }
            
            // 상태별 카운트
            if (settlement.status === 'pending') {
                pendingCount++;
            } else if (settlement.status === 'paid') {
                paidCount++;
            }
        });

    setStats({
            totalReceivable,
            totalPayable,
            pendingCount,
            paidCount
    });
  };

    const handleExportExcel = async () => {
        if (!dateRange.start_date || !dateRange.end_date) {
            alert('시작일과 종료일을 선택해주세요.');
            return;
        }

        try {
            const response = await get(`api/settlements/export_excel/?start_date=${dateRange.start_date}&end_date=${dateRange.end_date}`, {
                responseType: 'blob'
            });
            
            // 파일 다운로드
            const url = window.URL.createObjectURL(new Blob([response]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `정산내역_${dateRange.start_date}_${dateRange.end_date}.xlsx`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Excel export failed:', err);
            alert('엑셀 출력 중 오류가 발생했습니다.');
        }
    };

    const getStatusBadgeClass = (status) => {
        switch (status) {
            case 'pending': return 'badge-warning';
            case 'approved': return 'badge-success';
            case 'paid': return 'badge-primary';
            case 'cancelled': return 'badge-danger';
            default: return 'badge-secondary';
        }
    };

    const getStatusText = (status) => {
        switch (status) {
            case 'pending': return '정산 대기';
            case 'approved': return '승인됨';
            case 'paid': return '지급 완료';
            case 'cancelled': return '취소됨';
            default: return status;
        }
    };

    const renderSettlementsByUserType = () => {
        const userCompanyType = user?.companyType;

        if (userCompanyType === 'headquarters') {
            // 본사: 지급할 리베이트만 표시
            return (
                <div className="settlements-section">
                    {/* 본사용 추가 리베이트 통계 */}
                    <div className="rebate-stats-section">
                        <h3>📊 리베이트 현황</h3>
                        <div className="stats-grid">
                            <div className="stat-card">
                                <div className="stat-icon">📋</div>
                                <div className="stat-content">
                                    <div className="stat-label">활성 정책</div>
                                    <div className="stat-value">{rebateStats.total_policies}개</div>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-icon">🏪</div>
                                <div className="stat-content">
                                    <div className="stat-label">참여 판매점</div>
                                    <div className="stat-value">{rebateStats.participating_stores}개</div>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-icon">💰</div>
                                <div className="stat-content">
                                    <div className="stat-label">총 리베이트</div>
                                    <div className="stat-value">{rebateStats.total_rebate_amount.toLocaleString()}원</div>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    <h3>💰 협력사 지급 예정</h3>
                    <div className="settlement-table-container">
                        <table className="settlement-table">
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
                                {settlements.filter(s => s.status === 'approved').map(settlement => (
                                    <tr key={settlement.id}>
                                        <td>#{settlement.id.slice(0, 8)}</td>
                                        <td>{settlement.order_number || '-'}</td>
                                        <td>{settlement.company_name}</td>
                                        <td className="amount">
                                            {parseFloat(settlement.rebate_amount || 0).toLocaleString()}원
                                        </td>
                                        <td>
                                            <span className={`badge ${getStatusBadgeClass(settlement.status)}`}>
                                                {getStatusText(settlement.status)}
                                            </span>
                                        </td>
                                        <td>{new Date(settlement.created_at).toLocaleDateString()}</td>
                                        <td>
                                            <button className="btn btn-sm btn-primary">
                                                상세보기
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                        
                        {settlements.filter(s => s.status === 'approved').length === 0 && (
                            <div className="empty-table">
                                <p>지급 예정인 정산이 없습니다.</p>
                            </div>
                        )}
                    </div>
                </div>
            );
        } else if (userCompanyType === 'agency') {
            // 협력사: 받을 리베이트와 지급할 리베이트 모두 표시
            const receivableSettlements = settlements.filter(s => 
                s.company_id === user?.companyId && s.status === 'approved'
            );
            const payableSettlements = settlements.filter(s => 
                s.company_id !== user?.companyId && s.status === 'approved'
            );

            return (
                <div className="settlements-section">
                    <div className="agency-settlements">
                        <div className="receivable-section">
                            <h3>📈 본사로부터 받을 리베이트</h3>
                            <div className="settlements-grid">
                                {receivableSettlements.map(settlement => (
                                    <div key={settlement.id} className="settlement-card receivable">
                                        <div className="settlement-header">
                                            <h4>본사 리베이트</h4>
                                            <span className={`badge ${getStatusBadgeClass(settlement.status)}`}>
                                                {getStatusText(settlement.status)}
                                            </span>
                                        </div>
                                        <div className="settlement-amount">
                                            <span className="amount-label">받을 금액:</span>
                                            <span className="amount-value receivable">
                                                +{parseFloat(settlement.rebate_amount || 0).toLocaleString()}원
                                            </span>
        </div>
                                        <div className="settlement-details">
                                            <p><strong>주문 정보:</strong> {settlement.order_info?.customer_name}</p>
                                            <p><strong>생성일:</strong> {new Date(settlement.created_at).toLocaleDateString()}</p>
        </div>
        </div>
                                ))}
          </div>
        </div>

                        <div className="payable-section">
                            <h3>📉 판매점에 지급할 리베이트</h3>
                            <div className="settlements-grid">
                                {payableSettlements.map(settlement => (
                                    <div key={settlement.id} className="settlement-card payable">
                                        <div className="settlement-header">
                                            <h4>{settlement.company_name}</h4>
                                            <span className={`badge ${getStatusBadgeClass(settlement.status)}`}>
                                                {getStatusText(settlement.status)}
                                            </span>
                                        </div>
                                        <div className="settlement-amount">
                                            <span className="amount-label">지급 금액:</span>
                                            <span className="amount-value payable">
                                                -{parseFloat(settlement.rebate_amount || 0).toLocaleString()}원
                                            </span>
                                        </div>
                                        <div className="settlement-details">
                                            <p><strong>주문 정보:</strong> {settlement.order_info?.customer_name}</p>
                                            <p><strong>생성일:</strong> {new Date(settlement.created_at).toLocaleDateString()}</p>
                                            {settlement.rebate_due_date && (
                                                <p><strong>지급 예정일:</strong> {settlement.rebate_due_date}</p>
                                            )}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            );
        } else if (userCompanyType === 'retail') {
            // 판매점: 받을 리베이트만 표시
            return (
                <div className="settlements-section">
                    <h3>💎 협력사로부터 받을 리베이트</h3>
                    <div className="settlements-grid">
                        {settlements.filter(s => s.status === 'approved').map(settlement => (
                            <div key={settlement.id} className="settlement-card receivable">
                                <div className="settlement-header">
                                    <h4>리베이트 수령</h4>
                                    <span className={`badge ${getStatusBadgeClass(settlement.status)}`}>
                                        {getStatusText(settlement.status)}
                                    </span>
                                </div>
                                <div className="settlement-amount">
                                    <span className="amount-label">받을 금액:</span>
                                    <span className="amount-value receivable">
                                        +{parseFloat(settlement.rebate_amount || 0).toLocaleString()}원
                                    </span>
                                </div>
                                <div className="settlement-details">
                                    <p><strong>주문 정보:</strong> {settlement.order_info?.customer_name}</p>
                                    <p><strong>생성일:</strong> {new Date(settlement.created_at).toLocaleDateString()}</p>
                                    {settlement.rebate_due_date && (
                                        <p><strong>지급 예정일:</strong> {settlement.rebate_due_date}</p>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            );
        }
    };

    if (loading) return <div className="settlement-page loading">로딩 중...</div>;
    if (error) return <div className="settlement-page error">{error}</div>;

    const getPageTitle = () => {
        const companyType = user?.companyType;
        switch (companyType) {
            case 'headquarters':
                return '💰 정산 관리 (본사)';
            case 'agency':
                return '💰 정산 관리 (협력사)';
            case 'retail':
                return '💰 정산 관리 (판매점)';
            default:
                return '📊 정산 관리';
        }
    };

  return (
    <div className="settlement-management-page">
            <div className="page-header">
                <div className="header-content">
                    <h1>{getPageTitle()}</h1>
                    <p>정산 내역을 조회하고 관리할 수 있습니다.</p>
                </div>
                <div className="header-actions">
                    <div className="date-range-selector">
                        <label>📅 조회 기간:</label>
                        <input
                            type="date"
                            value={dateRange.start_date}
                            onChange={(e) => setDateRange(prev => ({ ...prev, start_date: e.target.value }))}
                            max={new Date().toISOString().split('T')[0]}
                            placeholder="시작일"
                        />
                        <span>~</span>
                        <input
                            type="date"
                            value={dateRange.end_date}
                            onChange={(e) => setDateRange(prev => ({ ...prev, end_date: e.target.value }))}
                            max={new Date().toISOString().split('T')[0]}
                            placeholder="종료일"
                        />
                        <button 
                            className="btn btn-primary" 
                            onClick={handleExportExcel}
                            disabled={!dateRange.start_date || !dateRange.end_date}
                        >
                            📊 엑셀 출력
                        </button>
            </div>
            </div>
            </div>

            {/* 정산 보고서 */}
            <div className="settlement-report">
                <h2>📋 정산 보고서</h2>
                <div className="stats-grid">
                    <div className="stat-card total">
                        <div className="stat-icon">💼</div>
                        <div className="stat-content">
                            <div className="stat-label">전체 정산액</div>
                            <div className="stat-value">
                                {(stats.totalReceivable + stats.totalPayable).toLocaleString()}원
                            </div>
                        </div>
                    </div>
                    
                    {user?.companyType !== 'headquarters' && (
                        <div className="stat-card receivable">
                            <div className="stat-icon">💰</div>
                            <div className="stat-content">
                                <div className="stat-label">받을 금액</div>
                                <div className="stat-value positive">
                                    +{stats.totalReceivable.toLocaleString()}원
                                </div>
                            </div>
                        </div>
                    )}
                    
                    {user?.companyType !== 'retail' && (
                        <div className="stat-card payable">
                            <div className="stat-icon">💸</div>
                            <div className="stat-content">
                                <div className="stat-label">지급할 금액</div>
                                <div className="stat-value negative">
                                    -{stats.totalPayable.toLocaleString()}원
                                </div>
                </div>
              </div>
            )}

                    <div className="stat-card pending">
                        <div className="stat-icon">⏳</div>
                        <div className="stat-content">
                            <div className="stat-label">대기 중</div>
                            <div className="stat-value">
                                {stats.pendingCount}건
                            </div>
                        </div>
                    </div>
                    
                    <div className="stat-card completed">
                        <div className="stat-icon">✅</div>
                        <div className="stat-content">
                            <div className="stat-label">지급완료</div>
                            <div className="stat-value">
                                {stats.paidCount}건
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* 정산 목록 */}
            {renderSettlementsByUserType()}

            {settlements.length === 0 && (
                <div className="no-data">
                    <div className="no-data-icon">📋</div>
                    <h3>정산 내역이 없습니다</h3>
                    <p>주문이 승인되면 자동으로 정산이 생성됩니다.</p>
              </div>
            )}
    </div>
  );
};

export default SettlementManagementPage;