import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, post, put } from '../services/api';
import './AgencyRebateAllocationPage.css';

const AgencyRebateAllocationPage = () => {
    const { id } = useParams(); // policy ID
    const { user } = useAuth();
    const navigate = useNavigate();
    
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [policy, setPolicy] = useState(null);
    const [hqRebateMatrix, setHqRebateMatrix] = useState([]); // 본사 리베이트 매트릭스 (읽기전용)
    const [agencyRebateMatrix, setAgencyRebateMatrix] = useState([]); // 협력사 리베이트 매트릭스 (편집가능)
    const [errors, setErrors] = useState({});

    useEffect(() => {
        fetchData();
    }, [id]);

    const fetchData = async () => {
        try {
            setLoading(true);
            
            // 정책 정보 가져오기
            const policyResponse = await get(`api/policies/${id}/`);
            if (policyResponse.success) {
                setPolicy(policyResponse.data);
            }

            // 협력사 리베이트 API에서 본사 + 협력사 매트릭스 모두 가져오기
            try {
                const rebateResponse = await get(`api/policies/${id}/agency-rebate/`);
                console.log('[AgencyRebateAllocation] 리베이트 매트릭스 응답:', rebateResponse);
                
                if (rebateResponse.success && rebateResponse.data) {
                    // api.js 이중 래핑 처리
                    let data = rebateResponse.data;
                    
                    // 이중 래핑된 경우 처리 (api.js에서 한 번 더 래핑)
                    if (data.data && typeof data.data === 'object') {
                        console.log('[AgencyRebateAllocation] 이중 래핑 응답 감지, data.data 사용');
                        data = data.data;
                    }
                    
                    console.log('[AgencyRebateAllocation] 최종 데이터 구조:', data);
                    console.log('[AgencyRebateAllocation] hq_matrix 존재:', !!data.hq_matrix);
                    console.log('[AgencyRebateAllocation] agency_matrix 존재:', !!data.agency_matrix);
                    
                    // 본사 매트릭스 설정
                    if (data.hq_matrix && data.hq_matrix.length > 0) {
                        console.log('[AgencyRebateAllocation] 본사 매트릭스:', data.hq_matrix);
                        console.log('[AgencyRebateAllocation] 본사 매트릭스 계약기간:', 
                            [...new Set(data.hq_matrix.map(item => item.contract_period))].sort((a, b) => a - b));
                        setHqRebateMatrix(data.hq_matrix);
                        
                        // 협력사 매트릭스 설정 (있으면 기존 데이터, 없으면 초기화)
                        if (data.agency_matrix && data.agency_matrix.length > 0) {
                            console.log('[AgencyRebateAllocation] 기존 협력사 매트릭스:', data.agency_matrix);
                            console.log('[AgencyRebateAllocation] 기존 협력사 매트릭스 계약기간:', 
                                [...new Set(data.agency_matrix.map(item => item.contract_period))].sort((a, b) => a - b));
                            
                            // 본사 매트릭스에 있는 계약기간이 협력사 매트릭스에 없는 경우 추가
                            const hqPeriods = [...new Set(data.hq_matrix.map(item => item.contract_period))];
                            const agencyPeriods = [...new Set(data.agency_matrix.map(item => item.contract_period))];
                            
                            // 본사에는 있지만 협력사에는 없는 계약기간 찾기
                            const missingPeriods = hqPeriods.filter(period => !agencyPeriods.includes(period));
                            console.log('[AgencyRebateAllocation] 협력사 매트릭스에 없는 계약기간:', missingPeriods);
                            
                            if (missingPeriods.length > 0) {
                                // 누락된 계약기간에 대한 매트릭스 항목 추가
                                const additionalMatrix = [];
                                const planRanges = [...new Set(data.agency_matrix.map(item => item.plan_range))];
                                
                                planRanges.forEach(planRange => {
                                    missingPeriods.forEach(period => {
                                        // 본사 매트릭스에서 해당 요금제/계약기간 항목 찾기
                                        const hqItem = data.hq_matrix.find(item => 
                                            item.plan_range === planRange && item.contract_period === period);
                                        
                                        if (hqItem) {
                                            additionalMatrix.push({
                                                ...hqItem,
                                                id: `agency-init-${planRange}-${period}`,
                                                rebate_amount: 0
                                            });
                                        }
                                    });
                                });
                                
                                console.log('[AgencyRebateAllocation] 추가할 협력사 매트릭스 항목:', additionalMatrix);
                                // 기존 매트릭스와 새 항목 합치기
                                const updatedAgencyMatrix = [...data.agency_matrix, ...additionalMatrix];
                                console.log('[AgencyRebateAllocation] 업데이트된 협력사 매트릭스:', updatedAgencyMatrix);
                                setAgencyRebateMatrix(updatedAgencyMatrix);
                            } else {
                                setAgencyRebateMatrix(data.agency_matrix);
                            }
                        } else {
                            console.log('[AgencyRebateAllocation] 협력사 매트릭스 초기화');
                            initializeAgencyMatrix(data.hq_matrix);
                        }
                    } else {
                        console.error('[AgencyRebateAllocation] 본사 리베이트 매트릭스가 없습니다:', rebateResponse);
                        console.error('[AgencyRebateAllocation] 데이터 구조:', data);
                        setErrors({ general: '본사에서 설정한 리베이트 매트릭스가 없습니다. 본사에 문의하세요.' });
                    }
                } else {
                    console.error('[AgencyRebateAllocation] 리베이트 데이터 로딩 실패:', rebateResponse);
                    setErrors({ general: '리베이트 매트릭스를 불러올 수 없습니다.' });
                }
            } catch (rebateError) {
                console.error('[AgencyRebateAllocation] 리베이트 매트릭스 로딩 실패:', rebateError);
                setErrors({ general: '리베이트 매트릭스를 불러올 수 없습니다. 네트워크를 확인하세요.' });
            }
        } catch (error) {
            console.error('데이터 로딩 실패:', error);
            setErrors({ general: '데이터를 불러오는 중 오류가 발생했습니다.' });
        } finally {
            setLoading(false);
        }
    };

    // 더미 데이터 생성 함수 제거 - 실제 본사 데이터만 사용

    const initializeAgencyMatrix = (hqMatrix) => {
        console.log('[AgencyRebateAllocation] 본사 매트릭스 계약기간 종류:', 
            [...new Set(hqMatrix.map(item => item.contract_period))].sort((a, b) => a - b));
        
        // 본사 매트릭스를 기반으로 협력사 매트릭스 초기화 (금액은 0으로)
        const agencyMatrix = hqMatrix.map(item => ({
            ...item,
            id: `agency-init-${item.plan_range}-${item.contract_period}`, // 새로운 ID 생성
            rebate_amount: 0 // 협력사는 0부터 시작
        }));
        
        console.log('[AgencyRebateAllocation] 초기화된 협력사 매트릭스:', agencyMatrix);
        console.log('[AgencyRebateAllocation] 협력사 매트릭스 계약기간 종류:', 
            [...new Set(agencyMatrix.map(item => item.contract_period))].sort((a, b) => a - b));
        
        setAgencyRebateMatrix(agencyMatrix);
    };

    const handleAgencyRebateChange = (itemId, newAmount) => {
        const numericAmount = parseInt(newAmount) || 0;
        
        // 해당 본사 리베이트 찾기
        const hqItem = hqRebateMatrix.find(item => 
            agencyRebateMatrix.find(agencyItem => 
                agencyItem.id === itemId && 
                agencyItem.plan_range === item.plan_range && 
                agencyItem.contract_period === item.contract_period
            )
        );
        
        // 본사 리베이트보다 큰 경우 경고
        if (hqItem && numericAmount > hqItem.rebate_amount) {
            setErrors({
                [itemId]: `본사 리베이트(${hqItem.rebate_amount.toLocaleString()}원)보다 클 수 없습니다.`
            });
            return;
        }

        // 에러 제거
        if (errors[itemId]) {
            setErrors(prev => {
                const newErrors = { ...prev };
                delete newErrors[itemId];
                return newErrors;
            });
        }

        // 협력사 매트릭스 업데이트
        setAgencyRebateMatrix(prev => 
            prev.map(item => 
                item.id === itemId 
                    ? { ...item, rebate_amount: numericAmount }
                    : item
            )
        );
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            
            const saveData = {
                policy_id: id,
                matrix: agencyRebateMatrix
            };

            const response = await post(`api/policies/${id}/agency-rebate/`, saveData);
            
            if (response.success) {
                alert('리베이트 할당이 저장되었습니다.');
                navigate('/policies');
            } else {
                alert('저장에 실패했습니다: ' + (response.message || '알 수 없는 오류'));
            }
        } catch (error) {
            console.error('저장 실패:', error);
            alert('저장 중 오류가 발생했습니다.');
        } finally {
            setSaving(false);
        }
    };

    const renderMatrix = (matrix, isEditable = false, title = '') => {
        const planRanges = [...new Set(matrix.map(item => item.plan_range))];
        const contractPeriods = [...new Set(matrix.map(item => item.contract_period))].sort((a, b) => a - b);

        return (
            <div className="rebate-matrix-card">
                <h3>{title}</h3>
                <div className="matrix-table">
                    <table>
                        <thead>
                            <tr>
                                <th>요금제</th>
                                {contractPeriods.map(period => (
                                    <th key={period}>{period}개월</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {planRanges.map(planRange => (
                                <tr key={planRange}>
                                    <td className="plan-range">{planRange}</td>
                                    {contractPeriods.map(period => {
                                        const item = matrix.find(m => 
                                            m.plan_range === planRange && m.contract_period === period
                                        );
                                        return (
                                            <td key={`${planRange}-${period}`}>
                                                {isEditable ? (
                                                    <div className="input-container">
                                                        <input
                                                            type="number"
                                                            value={item?.rebate_amount || 0}
                                                            onChange={(e) => handleAgencyRebateChange(item?.id, e.target.value)}
                                                            className={errors[item?.id] ? 'error' : ''}
                                                            min="0"
                                                            step="1000"
                                                        />
                                                        {errors[item?.id] && (
                                                            <div className="error-message">{errors[item?.id]}</div>
                                                        )}
                                                    </div>
                                                ) : (
                                                    <span className="readonly-amount">
                                                        {(item?.rebate_amount || 0).toLocaleString()}원
                                                    </span>
                                                )}
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    };

    if (loading) {
        return (
            <div className="agency-rebate-allocation">
                <div className="loading">데이터를 불러오는 중...</div>
            </div>
        );
    }

    return (
        <div className="agency-rebate-allocation">
            <div className="page-header">
                <div className="header-content">
                    <button 
                        className="back-btn" 
                        onClick={() => navigate('/policies')}
                    >
                        ← 목록으로
                    </button>
                    <h1>리베이트 할당</h1>
                    <p>{policy?.title} 정책의 판매점 리베이트를 설정합니다.</p>
                </div>
                <div className="header-actions">
                    <button 
                        className="btn btn-primary"
                        onClick={handleSave}
                        disabled={saving}
                    >
                        {saving ? '저장 중...' : '저장'}
                    </button>
                </div>
            </div>

            {errors.general && (
                <div className="error-message general-error">
                    {errors.general}
                </div>
            )}

            <div className="matrix-container">
                {/* 좌측: 본사 리베이트 매트릭스 (읽기전용) */}
                <div className="left-panel">
                    {renderMatrix(hqRebateMatrix, false, '📊 본사 리베이트 매트릭스 (참고용)')}
                    <div className="info-box">
                        <p><strong>💡 참고사항</strong></p>
                        <p>• 본사에서 설정한 리베이트 금액입니다.</p>
                        <p>• 우측에서 판매점에게 줄 리베이트를 설정하세요.</p>
                        <p>• 판매점 리베이트는 본사 리베이트보다 작거나 같아야 합니다.</p>
                    </div>
                </div>

                {/* 우측: 협력사 리베이트 설정 (편집가능) */}
                <div className="right-panel">
                    {renderMatrix(agencyRebateMatrix, true, '🎯 판매점 리베이트 설정')}
                    <div className="profit-info">
                        <p><strong>💰 협력사 수익</strong></p>
                        <p>협력사 수익 = 본사 리베이트 - 판매점 리베이트</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default AgencyRebateAllocationPage;
