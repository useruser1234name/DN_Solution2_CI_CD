import React, { useState, useEffect } from 'react';
import { get } from '../services/api';
import './RetailRebateModal.css';

const RetailRebateModal = ({ isOpen, onClose, policy }) => {
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [rebateData, setRebateData] = useState(null);

    useEffect(() => {
        if (isOpen && policy) {
            fetchRebateData();
        }
    }, [isOpen, policy]);

    const fetchRebateData = async () => {
        try {
            setLoading(true);
            setError(null);
            
            console.log('[RetailRebateModal] 리베이트 데이터 조회 시작:', policy.id);
            
            const response = await get(`api/policies/${policy.id}/retail-rebate/`);
            console.log('[RetailRebateModal] API 응답:', response);
            
            if (response.success) {
                // api.js 이중 래핑 처리
                let data = response.data;
                if (data.data && typeof data.data === 'object') {
                    console.log('[RetailRebateModal] 이중 래핑 응답 감지, data.data 사용');
                    data = data.data;
                }
                
                console.log('[RetailRebateModal] 최종 데이터:', data);
                setRebateData(data);
            } else {
                console.error('[RetailRebateModal] 리베이트 조회 실패:', response.message);
                setError(response.message || '리베이트 정보를 불러올 수 없습니다.');
            }
        } catch (error) {
            console.error('[RetailRebateModal] 리베이트 조회 오류:', error);
            setError('리베이트 정보를 불러오는 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const formatAmount = (amount) => {
        return new Intl.NumberFormat('ko-KR').format(amount) + '원';
    };

    const renderRebateMatrix = () => {
        if (!rebateData || !rebateData.rebate_matrix || rebateData.rebate_matrix.length === 0) {
            return (
                <div className="no-rebate-data">
                    <p>협력사에서 설정한 리베이트가 없습니다.</p>
                    <small>협력사에 문의하여 리베이트를 설정해달라고 요청하세요.</small>
                </div>
            );
        }

        // 매트릭스를 9x2 형태로 구성
        const matrix = Array(9).fill(null).map(() => Array(2).fill(0));
        
        rebateData.rebate_matrix.forEach(item => {
            if (item.row !== undefined && item.col !== undefined) {
                matrix[item.row][item.col] = item.rebate_amount;
            }
        });

        const planRanges = [
            { value: 11000, display: '11K' },
            { value: 22000, display: '22K' },
            { value: 33000, display: '33K' },
            { value: 44000, display: '44K' },
            { value: 55000, display: '55K' },
            { value: 66000, display: '66K' },
            { value: 77000, display: '77K' },
            { value: 88000, display: '88K' },
            { value: 99000, display: '99K' }
        ];

        return (
            <div className="rebate-matrix">
                <table>
                    <thead>
                        <tr>
                            <th>요금제</th>
                            <th>12개월</th>
                            <th>24개월</th>
                        </tr>
                    </thead>
                    <tbody>
                        {planRanges.map((plan, rowIndex) => (
                            <tr key={plan.value}>
                                <td className="plan-range">{plan.display}</td>
                                <td className="rebate-amount">{formatAmount(matrix[rowIndex][0])}</td>
                                <td className="rebate-amount">{formatAmount(matrix[rowIndex][1])}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal-content retail-rebate-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>💰 리베이트 금액</h2>
                    <button className="modal-close" onClick={onClose}>×</button>
                </div>

                <div className="modal-body">
                    {loading ? (
                        <div className="loading-state">
                            <div className="spinner"></div>
                            <p>리베이트 정보를 불러오는 중...</p>
                        </div>
                    ) : error ? (
                        <div className="error-state">
                            <p className="error-message">{error}</p>
                        </div>
                    ) : (
                        <div className="rebate-content">
                            <div className="policy-info">
                                <h3>{rebateData?.policy_title}</h3>
                                {rebateData?.agency_name && (
                                    <p className="agency-info">
                                        협력사: <strong>{rebateData.agency_name}</strong>
                                    </p>
                                )}
                            </div>

                            <div className="rebate-matrix-container">
                                <h4>🎯 판매점 리베이트</h4>
                                <p className="matrix-description">
                                    협력사에서 설정한 리베이트 금액입니다. 계약 체결 시 받을 수 있는 금액입니다.
                                </p>
                                {renderRebateMatrix()}
                            </div>

                            {rebateData?.rebate_matrix && rebateData.rebate_matrix.length > 0 && (
                                <div className="rebate-info">
                                    <h4>💡 참고사항</h4>
                                    <ul>
                                        <li>위 금액은 협력사에서 설정한 리베이트입니다.</li>
                                        <li>실제 지급 조건은 협력사와의 계약에 따라 달라질 수 있습니다.</li>
                                        <li>문의사항이 있으시면 협력사에 직접 연락하세요.</li>
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                <div className="modal-footer">
                    <button className="btn btn-secondary" onClick={onClose}>
                        확인
                    </button>
                </div>
            </div>
        </div>
    );
};

export default RetailRebateModal;
