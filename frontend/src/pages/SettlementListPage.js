
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, post, settlementAPI } from '../services/api';
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
    const [exportLoading, setExportLoading] = useState(false);
    const [searchFilters, setSearchFilters] = useState(() => {
        const d = new Date();
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        const today = `${yyyy}-${mm}-${dd}`;
        return {
            startDate: today,
            endDate: today,
            status: 'all',
            dateColumn: 'created_at'
        };
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
        handleSearch();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    const handleViewReport = () => {
        navigate('/settlements/report');
    };

    // 검색 및 엑셀 내보내기 함수들
    const handleSearch = async () => {
        try {
            setLoading(true);
            
            // 검색 파라미터 구성
            const params = {};
            
            if (searchFilters.startDate) {
                params.start_date = searchFilters.startDate;
            }
            if (searchFilters.endDate) {
                params.end_date = searchFilters.endDate;
            }
            if (searchFilters.status !== 'all') {
                params.status = searchFilters.status;
            }
            if (searchFilters.dateColumn) {
                params.date_column = searchFilters.dateColumn;
            }
            
            const response = await get('api/settlements/', params);
            
            if (response.success) {
                const data = response.data;
                let settlementsArray = [];
                if (Array.isArray(data)) {
                    settlementsArray = data;
                } else if (data && Array.isArray(data.results)) {
                    settlementsArray = data.results;
                } else if (data && data.data && Array.isArray(data.data)) {
                    settlementsArray = data.data;
                }
                
                setSettlements(settlementsArray);
                
                // 요약 정보 계산
                const summaryData = {
                    total: settlementsArray.reduce((sum, s) => sum + parseFloat(s.rebate_amount || 0), 0),
                    pending: settlementsArray.filter(s => s.status === 'pending').reduce((sum, s) => sum + parseFloat(s.rebate_amount || 0), 0),
                    approved: settlementsArray.filter(s => s.status === 'approved').reduce((sum, s) => sum + parseFloat(s.rebate_amount || 0), 0),
                    paid: settlementsArray.filter(s => s.status === 'paid').reduce((sum, s) => sum + parseFloat(s.rebate_amount || 0), 0)
                };
                setSummary(summaryData);
            }
        } catch (error) {
            console.error('검색 실패:', error);
            alert('검색 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleExportExcel = async () => {
        try {
            setExportLoading(true);
            
            // 현재 검색 조건으로 엑셀 내보내기
            const params = {};
            
            if (searchFilters.startDate) {
                params.start_date = searchFilters.startDate;
            }
            if (searchFilters.endDate) {
                params.end_date = searchFilters.endDate;
            }
            if (searchFilters.status !== 'all') {
                params.status = searchFilters.status;
            }
            if (searchFilters.dateColumn) {
                params.date_column = searchFilters.dateColumn;
            }

            console.log('엑셀 내보내기 요청:', params);

                        // settlementAPI의 exportExcel 사용 (파라미터 수정)
            const response = await settlementAPI.exportExcel(
                searchFilters.startDate || '',
                searchFilters.endDate || '',
                searchFilters.status !== 'all' ? searchFilters.status : '',
                searchFilters.dateColumn || 'created_at'
            );
            
            console.log('엑셀 내보내기 응답:', response);
            
            // 파일 다운로드 처리 (response가 이미 blob)
            const blob = response;
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `정산데이터_${searchFilters.startDate || new Date().toISOString().split('T')[0]}_${searchFilters.endDate || new Date().toISOString().split('T')[0]}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            alert('엑셀 파일이 다운로드되었습니다.');
        } catch (error) {
            console.error('엑셀 내보내기 실패:', error);
            
            // 에러 메시지 개선
            let errorMessage = '엑셀 내보내기 중 오류가 발생했습니다.';
            if (error.response) {
                if (error.response.status === 400) {
                    errorMessage = '요청 데이터가 올바르지 않습니다. 날짜를 확인해주세요.';
                } else if (error.response.status === 404) {
                    errorMessage = 'API 엔드포인트를 찾을 수 없습니다.';
                } else if (error.response.status === 500) {
                    errorMessage = '서버 오류가 발생했습니다. 관리자에게 문의하세요.';
                }
            }
            
            alert(errorMessage);
        } finally {
            setExportLoading(false);
        }
    };

    const handleFilterInputChange = (key, value) => {
        setSearchFilters(prev => ({
            ...prev,
            [key]: value
        }));
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
   
                </div>
            </div>

            {/* 협력사용 리베이트 요약 */}
            <RebateSummary />

            {/* 검색 패널 */}
            <div className="search-panel">
                <div className="search-form">
                    <div className="search-group">
                        <label>기준 날짜</label>
                        <select
                            value={searchFilters.dateColumn}
                            onChange={(e) => handleFilterInputChange('dateColumn', e.target.value)}
                            className="date-column-select"
                        >
                            <option value="created_at">생성일</option>
                            <option value="paid_at">지급일</option>
                            <option value="order__created_at">접수일</option>
                            <option value="order__activation_date">개통일</option>
                            <option value="updated_at">수정일</option>
                        </select>
                    </div>
                    
                    <div className="search-group">
                        <label>조회기간</label>
                        <div className="date-range">
                            <input
                                type="date"
                                value={searchFilters.startDate}
                                onChange={(e) => handleFilterInputChange('startDate', e.target.value)}
                                className="date-input"
                            />
                            <span className="date-separator">~</span>
                            <input
                                type="date"
                                value={searchFilters.endDate}
                                onChange={(e) => handleFilterInputChange('endDate', e.target.value)}
                                className="date-input"
                            />
                        </div>
                    </div>
                    
                    <div className="search-group">
                        <label>상태</label>
                        <select
                            value={searchFilters.status}
                            onChange={(e) => handleFilterInputChange('status', e.target.value)}
                            className="status-select"
                        >
                            <option value="all">전체</option>
                            <option value="pending">정산 대기</option>
                            <option value="approved">정산 승인</option>
                            <option value="paid">입금 완료</option>
                            <option value="unpaid">미입금</option>
                            <option value="cancelled">취소됨</option>
                        </select>
                    </div>
                    
                    <div className="search-actions">
                        <button 
                            className="btn btn-primary search-btn"
                            onClick={handleSearch}
                            disabled={loading}
                        >
                            {loading ? '조회 중...' : '조회'}
                        </button>
                        <button 
                            className="btn btn-success export-btn"
                            onClick={handleExportExcel}
                            disabled={exportLoading}
                        >
                            {exportLoading ? '📥 내보내는 중...' : '📥 엑셀 출력'}
                        </button>
                    </div>
                </div>
            </div>

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

            {/* 데이터 프레임 */}
            <div className="data-frame-container">
                <div className="data-frame-header">
                    <div className="data-info">
                        <span className="data-count">총 {filteredSettlements.length}건</span>
                        <span className="data-total">합계: {formatAmount(summary.total)}원</span>
                    </div>
                </div>
                
                {filteredSettlements.length === 0 ? (
                    <div className="no-data-frame">
                        <div className="no-data-icon">📊</div>
                        <h3>조회된 데이터가 없습니다</h3>
                        <p>검색 조건을 변경하여 다시 시도해보세요.</p>
                    </div>
                ) : (
                    <div className="data-frame-table">
                        <div className="table-wrapper">
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th className="col-date">접수일</th>
                                        <th className="col-company">판매점</th>
                                        <th className="col-plan">요금제</th>
                                        <th className="col-total-commission">총 수수료</th>
                                        <th className="col-grade">그레이드(레벨/보너스)</th>
                                        <th className="col-agency">대리점 정산</th>
                                        <th className="col-retail">판매점 수수료</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {filteredSettlements.map((settlement) => (
                                        <tr key={settlement.id} className="data-row">
                                            <td className="col-date">
                                                <span className="date-value">{settlement.received_date ? formatDate(settlement.received_date) : (settlement.order_info?.created_at ? formatDate(settlement.order_info.created_at) : '-')}</span>
                                            </td>
                                            <td className="col-company">
                                                <span className="company-name">{settlement.company_name || '-'}</span>
                                            </td>
                                            <td className="col-plan">
                                                <span className="plan-name">
                                                    {settlement.plan_name || settlement.order_info?.plan_name || '-'}
                                                </span>
                                            </td>
                                            <td className="col-total-commission">
                                                <span className="amount-value">{formatAmount(settlement.total_commission || 0)}원</span>
                                            </td>
                                            <td className="col-grade">
                                                <span className="amount-value">L{settlement.grade_level ?? 0} / {formatAmount(settlement.grade_bonus || 0)}원</span>
                                            </td>
                                            <td className="col-agency">
                                                <span className="amount-value">{formatAmount(settlement.agency_commission || 0)}원</span>
                                            </td>
                                            <td className="col-retail">
                                                <span className="amount-value">{formatAmount(settlement.retail_commission || 0)}원</span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        
                        {/* 페이지네이션 (향후 추가 가능) */}
                        <div className="data-frame-footer">
                            <div className="pagination-info">
                                1-{filteredSettlements.length} of {filteredSettlements.length} 항목
                            </div>
                        </div>
                    </div>
                )}
            </div>


        </div>
    );
};

export default SettlementListPage;
