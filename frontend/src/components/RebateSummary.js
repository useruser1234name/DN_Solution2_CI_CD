import React, { useState, useEffect } from 'react';
import { get } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './RebateSummary.css';

const RebateSummary = () => {
    const { user } = useAuth();
    const [rebateData, setRebateData] = useState([]);
    const [summary, setSummary] = useState({
        total_receivable: 0,
        total_payable: 0,
        net_amount: 0,
        participating_stores: 0
    });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    console.log('[RebateSummary] 컴포넌트 렌더링', {
        user: user?.username,
        companyType: user?.companyType
    });

    const fetchRebateSummary = async () => {
        console.log('[RebateSummary] 리베이트 요약 정보 가져오기 시작');
        
        try {
            setLoading(true);
            setError(null);
            
            const response = await get('api/policies/rebate-summary/');
            console.log('[RebateSummary] 리베이트 요약 응답:', response);

            if (response.success) {
                const data = response.data;
                setRebateData(data.rebate_data || []);
                setSummary({
                    total_receivable: data.total_receivable || 0,
                    total_payable: data.total_payable || 0,
                    net_amount: (data.total_receivable || 0) - (data.total_payable || 0),
                    participating_stores: data.participating_stores || 0
                });
            } else {
                setError(response.error || '리베이트 정보를 가져오는데 실패했습니다.');
            }
        } catch (err) {
            console.error('[RebateSummary] 리베이트 요약 가져오기 오류:', err);
            setError('리베이트 정보를 가져오는데 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        // 협력사만 리베이트 요약 표시
        if (user?.companyType === 'agency') {
            fetchRebateSummary();
        }
    }, [user]);

    const formatAmount = (amount) => {
        return new Intl.NumberFormat('ko-KR').format(amount);
    };

    const getRebateTypeClass = (rebateType) => {
        return rebateType === '받을 리베이트' ? 'receivable' : 'payable';
    };

    const getRebateTypeIcon = (rebateType) => {
        return rebateType === '받을 리베이트' ? '⬇️' : '⬆️';
    };

    // 협력사가 아닌 경우 렌더링하지 않음
    if (user?.companyType !== 'agency') {
        return null;
    }

    if (loading) {
        return (
            <div className="rebate-summary loading">
                <div className="loading-spinner">리베이트 정보를 불러오는 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="rebate-summary error">
                <div className="error-message">{error}</div>
                <button onClick={fetchRebateSummary} className="retry-btn">다시 시도</button>
            </div>
        );
    }

    return (
        <div className="rebate-summary">
            <div className="rebate-summary-header">
                <h3>🏢 협력사 리베이트 현황</h3>
                <p className="summary-description">
                    본사에서 받을 리베이트와 판매점에 지급할 리베이트를 확인하세요.
                </p>
            </div>

            {/* 요약 카드들 */}
            <div className="summary-cards">
                <div className="summary-card receivable">
                    <div className="card-icon">⬇️</div>
                    <div className="card-content">
                        <h4>받을 리베이트</h4>
                        <div className="amount">{formatAmount(summary.total_receivable)}원</div>
                        <div className="description">본사에서 받을 총 금액</div>
                    </div>
                </div>

                <div className="summary-card payable">
                    <div className="card-icon">⬆️</div>
                    <div className="card-content">
                        <h4>지급할 리베이트</h4>
                        <div className="amount">{formatAmount(summary.total_payable)}원</div>
                        <div className="description">판매점에 지급할 총 금액</div>
                    </div>
                </div>

                <div className="summary-card net">
                    <div className="card-icon">💰</div>
                    <div className="card-content">
                        <h4>순 리베이트</h4>
                        <div className={`amount ${summary.net_amount >= 0 ? 'positive' : 'negative'}`}>
                            {formatAmount(summary.net_amount)}원
                        </div>
                        <div className="description">실제 수익 금액</div>
                    </div>
                </div>

                <div className="summary-card stores">
                    <div className="card-icon">🏪</div>
                    <div className="card-content">
                        <h4>참여 판매점</h4>
                        <div className="amount">{summary.participating_stores}개</div>
                        <div className="description">리베이트 설정된 판매점</div>
                    </div>
                </div>
            </div>

            {/* 상세 리베이트 목록 */}
            {rebateData.length > 0 && (
                <div className="rebate-details">
                    <h4>📋 리베이트 상세 내역</h4>
                    <div className="rebate-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>구분</th>
                                    <th>정책명</th>
                                    <th>업체명</th>
                                    <th>리베이트 금액</th>
                                    <th>상태</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rebateData.map((item, index) => (
                                    <tr key={index} className={getRebateTypeClass(item.rebate_type)}>
                                        <td>
                                            <span className={`rebate-type-badge ${getRebateTypeClass(item.rebate_type)}`}>
                                                {getRebateTypeIcon(item.rebate_type)} {item.rebate_type}
                                            </span>
                                        </td>
                                        <td className="policy-title">{item.policy_title}</td>
                                        <td className="company-name">{item.company_name}</td>
                                        <td className={`amount ${getRebateTypeClass(item.rebate_type)}`}>
                                            {formatAmount(item.rebate_amount)}원
                                        </td>
                                        <td>
                                            <span className={`status-badge ${item.status}`}>
                                                {item.status === 'active' ? '활성' : '비활성'}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {rebateData.length === 0 && (
                <div className="no-rebate-data">
                    <div className="no-data-icon">📊</div>
                    <h4>리베이트 설정이 없습니다</h4>
                    <p>정책이 노출되고 판매점 리베이트가 설정되면 여기에 표시됩니다.</p>
                </div>
            )}
        </div>
    );
};

export default RebateSummary;
