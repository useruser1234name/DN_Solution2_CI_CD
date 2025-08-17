import React, { useState, useEffect } from 'react';
import { get, post } from '../services/api';
import { getCompanyTypeFromCode } from '../utils/companyUtils';
import './PolicyExposureModal.css';

const PolicyExposureModal = ({ isOpen, onClose, policy, onSuccess }) => {
    const [agencies, setAgencies] = useState([]);
    const [exposedAgencies, setExposedAgencies] = useState([]);
    const [selectedAgencies, setSelectedAgencies] = useState([]);
    const [selectedUnexposed, setSelectedUnexposed] = useState([]); // 비노출 업체 중 선택된 것들
    const [selectedExposed, setSelectedExposed] = useState([]); // 노출 업체 중 선택된 것들
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState(null);



    const fetchData = async () => {
        if (!policy || !isOpen) return;

        setLoading(true);
        setError(null);

        try {
            // 협력사 목록 가져오기
            console.log('[PolicyExposureModal] 협력사 목록 요청 시작...');
            const agenciesResponse = await get('api/companies/companies/?type=agency');
            console.log('[PolicyExposureModal] API 응답 전체:', agenciesResponse);
            console.log('[PolicyExposureModal] API 응답 타입:', typeof agenciesResponse);
            console.log('[PolicyExposureModal] API 응답 키들:', agenciesResponse ? Object.keys(agenciesResponse) : 'null');

            let agenciesData = [];
            
            // API 응답 구조 처리: {success: true, data: {...}, message: null}
            if (agenciesResponse && typeof agenciesResponse === 'object') {
                // success/data 구조인 경우
                if (agenciesResponse.success && agenciesResponse.data) {
                    console.log('[PolicyExposureModal] success/data 구조 응답 처리');
                    const actualData = agenciesResponse.data;
                    
                    if (actualData.results && Array.isArray(actualData.results)) {
                        console.log('[PolicyExposureModal] 페이지네이션 응답 처리:', actualData.results.length, '개 업체');
                        agenciesData = actualData.results;
                    } else if (Array.isArray(actualData)) {
                        console.log('[PolicyExposureModal] 직접 배열 응답 처리:', actualData.length, '개 업체');
                        agenciesData = actualData;
                    } else {
                        console.warn('[PolicyExposureModal] data 내부 구조 확인:', Object.keys(actualData));
                        setError('협력사 목록 데이터 구조가 예상과 다릅니다.');
                        return;
                    }
                }
                // 직접 페이지네이션 구조인 경우
                else if (agenciesResponse.results && Array.isArray(agenciesResponse.results)) {
                    console.log('[PolicyExposureModal] 직접 페이지네이션 응답 처리:', agenciesResponse.results.length, '개 업체');
                    agenciesData = agenciesResponse.results;
                } 
                // 직접 배열인 경우
                else if (Array.isArray(agenciesResponse)) {
                    console.log('[PolicyExposureModal] 직접 배열 응답 처리:', agenciesResponse.length, '개 업체');
                    agenciesData = agenciesResponse;
                } else {
                    console.warn('[PolicyExposureModal] 예상하지 못한 응답 구조:', Object.keys(agenciesResponse));
                    console.warn('[PolicyExposureModal] 응답 내용:', agenciesResponse);
                    setError('협력사 목록 데이터 구조가 예상과 다릅니다.');
                    return;
                }
            } else if (Array.isArray(agenciesResponse)) {
                // 최상위가 배열인 경우
                console.log('[PolicyExposureModal] 최상위 배열 응답 처리:', agenciesResponse.length, '개 업체');
                agenciesData = agenciesResponse;
            } else {
                console.error('[PolicyExposureModal] 잘못된 응답 타입:', typeof agenciesResponse, agenciesResponse);
                setError('협력사 목록 응답 형식이 올바르지 않습니다.');
                return;
            }

            console.log('[PolicyExposureModal] 원본 업체 데이터:', agenciesData);

            // 협력사만 필터링 (type=agency 쿼리 파라미터가 있으므로 이미 필터링되어야 하지만 안전을 위해)
            const filteredAgencies = agenciesData.filter(company => {
                console.log('[PolicyExposureModal] 업체 확인:', {
                    id: company.id,
                    name: company.name,
                    type: company.type,
                    code: company.code
                });
                
                // type 필드가 'agency'인지 먼저 확인
                if (company.type === 'agency') {
                    return true;
                }
                
                // type이 없거나 다르면 코드 패턴으로 확인
                if (company.code) {
                    try {
                        const companyTypeFromCode = getCompanyTypeFromCode(company.code);
                        console.log('[PolicyExposureModal] 코드에서 추출한 타입:', companyTypeFromCode);
                        return companyTypeFromCode === 'agency';
                    } catch (error) {
                        console.error('[PolicyExposureModal] 코드 파싱 오류:', error, 'for code:', company.code);
                        return false;
                    }
                }
                
                return false;
            });

            console.log('[PolicyExposureModal] 최종 협력사 필터링 결과:', filteredAgencies.length, '개 협력사');
            console.log('[PolicyExposureModal] 필터링된 협력사들:', filteredAgencies.map(a => ({id: a.id, name: a.name, type: a.type, code: a.code})));
            
            setAgencies(filteredAgencies);
            
            if (filteredAgencies.length === 0) {
                console.warn('[PolicyExposureModal] 협력사가 없습니다. 원본 데이터:', agenciesData);
                setError('현재 노출 가능한 협력사가 없습니다. 협력사를 먼저 등록해주세요.');
            } else {
                setError(null);
            }

            // 현재 노출된 협력사 목록 가져오기
            try {
                console.log('[PolicyExposureModal] 노출 정보 조회 시작...');
                console.log('[PolicyExposureModal] 정책 ID:', policy.id);
                console.log('[PolicyExposureModal] API URL:', `api/policies/${policy.id}/exposures/`);
                
                const exposureResponse = await get(`api/policies/${policy.id}/exposures/`);
                console.log('[PolicyExposureModal] 노출 정보 응답:', exposureResponse);
                console.log('[PolicyExposureModal] 응답 타입:', typeof exposureResponse);
                console.log('[PolicyExposureModal] 응답 키들:', exposureResponse ? Object.keys(exposureResponse) : 'null');
                
                if (exposureResponse.success) {
                    let exposureData = [];
                    
                    console.log('[PolicyExposureModal] 응답 데이터 구조 분석:');
                    console.log('- exposureResponse.data:', exposureResponse.data);
                    console.log('- exposureResponse.data 타입:', typeof exposureResponse.data);
                    console.log('- exposureResponse.data 키들:', exposureResponse.data ? Object.keys(exposureResponse.data) : 'null');
                    console.log('- exposureResponse.data.exposures:', exposureResponse.data?.exposures);
                    console.log('- exposureResponse.data.exposures 타입:', typeof exposureResponse.data?.exposures);
                    console.log('- Array.isArray(exposureResponse.data.exposures):', Array.isArray(exposureResponse.data?.exposures));
                    console.log('- exposureResponse.data.policy:', exposureResponse.data?.policy);
                    console.log('- exposureResponse.data.results:', exposureResponse.data?.results);
                    console.log('- exposureResponse.data.data:', exposureResponse.data?.data);
                    
                    // 응답 구조 처리: api.js에서 이중 래핑된 응답 우선 처리
                    if (exposureResponse.data?.data?.exposures && Array.isArray(exposureResponse.data.data.exposures)) {
                        // api.js 이중 래핑 + PolicyExposureViewSet 응답 구조
                        console.log('[PolicyExposureModal] 이중 래핑 + PolicyExposureViewSet 응답 구조 사용');
                        exposureData = exposureResponse.data.data.exposures;
                    } else if (exposureResponse.data?.exposures && Array.isArray(exposureResponse.data.exposures)) {
                        // 직접 PolicyExposureViewSet 응답 구조
                        console.log('[PolicyExposureModal] 직접 PolicyExposureViewSet 응답 구조 사용');
                        exposureData = exposureResponse.data.exposures;
                    } else if (exposureResponse.data?.data && Array.isArray(exposureResponse.data.data)) {
                        // 이중 래핑된 직접 배열 응답
                        console.log('[PolicyExposureModal] 이중 래핑된 직접 배열 응답 구조 사용');
                        exposureData = exposureResponse.data.data;
                    } else if (Array.isArray(exposureResponse.data)) {
                        // 직접 배열 응답
                        console.log('[PolicyExposureModal] 직접 배열 응답 구조 사용');
                        exposureData = exposureResponse.data;
                    } else if (exposureResponse.data?.results && Array.isArray(exposureResponse.data.results)) {
                        // 페이지네이션 응답
                        console.log('[PolicyExposureModal] 페이지네이션 응답 구조 사용');
                        exposureData = exposureResponse.data.results;
                    } else {
                        console.warn('[PolicyExposureModal] 알 수 없는 응답 구조:', exposureResponse.data);
                    }
                    
                    console.log('[PolicyExposureModal] 최종 노출 데이터:', exposureData);
                    console.log('[PolicyExposureModal] 노출 데이터 길이:', exposureData.length);
                    
                    // 노출된 협력사 ID 추출 (API 응답 구조에 맞게)
                    const exposedAgencyIds = exposureData.map(e => {
                        // API 응답 구조: {agency: {id, name, code}, ...}
                        let agencyId = null;
                        
                        if (e.agency && e.agency.id) {
                            // 중첩된 agency 객체
                            agencyId = e.agency.id;
                        } else if (e.agency_id) {
                            // 직접 agency_id 필드
                            agencyId = e.agency_id;
                        } else if (e.agency) {
                            // agency가 ID 문자열인 경우
                            agencyId = e.agency;
                        } else if (e.company_id) {
                            // company_id 필드
                            agencyId = e.company_id;
                        } else if (e.company && e.company.id) {
                            // 중첩된 company 객체
                            agencyId = e.company.id;
                        } else if (e.company) {
                            // company가 ID 문자열인 경우
                            agencyId = e.company;
                        }
                        
                        console.log('[PolicyExposureModal] 노출 항목:', e, '-> 협력사 ID:', agencyId);
                        return agencyId;
                    }).filter(id => id); // null/undefined 제거
                    
                    console.log('[PolicyExposureModal] 추출된 노출 협력사 IDs:', exposedAgencyIds);
                    
                    setExposedAgencies(exposedAgencyIds);
                    setSelectedAgencies([...exposedAgencyIds]);
                } else {
                    console.warn('[PolicyExposureModal] 노출 정보 조회 실패:', exposureResponse.message);
                    setExposedAgencies([]);
                    setSelectedAgencies([]);
                }
            } catch (exposureError) {
                console.error('[PolicyExposureModal] 노출 정보 조회 오류:', exposureError);
                console.error('[PolicyExposureModal] 오류 상세:', {
                    message: exposureError.message,
                    response: exposureError.response,
                    status: exposureError.response?.status,
                    data: exposureError.response?.data
                });
                setExposedAgencies([]);
                setSelectedAgencies([]);
            }

        } catch (error) {

            setAgencies([]);
            setError('협력사 목록을 불러오는 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, [isOpen, policy]);

    // 비노출 업체 선택/해제
    const toggleUnexposedSelection = (agencyId) => {
        setSelectedUnexposed(prev => 
            prev.includes(agencyId) 
                ? prev.filter(id => id !== agencyId)
                : [...prev, agencyId]
        );
    };

    // 노출 업체 선택/해제
    const toggleExposedSelection = (agencyId) => {
        setSelectedExposed(prev => 
            prev.includes(agencyId) 
                ? prev.filter(id => id !== agencyId)
                : [...prev, agencyId]
        );
    };

    // 비노출 업체에서 노출 업체로 이동
    const moveToExposed = (agencyIds) => {
        const idsArray = Array.isArray(agencyIds) ? agencyIds : [agencyIds];
        setSelectedAgencies(prev => {
            const newSelected = [...prev];
            idsArray.forEach(id => {
                if (!newSelected.includes(id)) {
                    newSelected.push(id);
                }
            });
            return newSelected;
        });
        // 선택 상태 초기화
        setSelectedUnexposed(prev => prev.filter(id => !idsArray.includes(id)));
    };

    // 노출 업체에서 비노출 업체로 이동
    const moveToUnexposed = (agencyIds) => {
        const idsArray = Array.isArray(agencyIds) ? agencyIds : [agencyIds];
        setSelectedAgencies(prev => prev.filter(id => !idsArray.includes(id)));
        // 선택 상태 초기화
        setSelectedExposed(prev => prev.filter(id => !idsArray.includes(id)));
    };

    // 선택된 비노출 업체들을 노출로 이동
    const moveSelectedToExposed = () => {
        if (selectedUnexposed.length > 0) {
            moveToExposed(selectedUnexposed);
        }
    };

    // 선택된 노출 업체들을 비노출로 이동
    const moveSelectedToUnexposed = () => {
        if (selectedExposed.length > 0) {
            moveToUnexposed(selectedExposed);
        }
    };

    // 전체 노출
    const moveAllToExposed = () => {
        const allAgencyIds = agencies.map(agency => agency.id);
        setSelectedAgencies(allAgencyIds);
        setSelectedUnexposed([]);
    };

    // 전체 비노출
    const moveAllToUnexposed = () => {
        setSelectedAgencies([]);
        setSelectedExposed([]);
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);

        try {
            console.log('[PolicyExposureModal] 정책 노출 설정 저장 시작:', {
                policyId: policy.id,
                selectedAgencies: selectedAgencies
            });

            // 실제 API 호출
            const response = await post(`api/policies/${policy.id}/exposures/`, {
                agency_ids: selectedAgencies
            });

            console.log('[PolicyExposureModal] 정책 노출 설정 응답:', response);

            if (response.success) {
                alert(`정책 노출 설정이 저장되었습니다.\n선택된 협력사: ${selectedAgencies.length}개`);
                onSuccess && onSuccess();
                onClose();
            } else {
                setError(response.message || '노출 설정 저장에 실패했습니다.');
            }

        } catch (error) {
            console.error('[PolicyExposureModal] 정책 노출 설정 저장 오류:', error);
            setError('노출 설정 저장 중 오류가 발생했습니다.');
        } finally {
            setSaving(false);
        }
    };

    const handleClose = () => {
        if (saving) return;
        setSelectedAgencies([...exposedAgencies]); // 원래 상태로 복원
        setSelectedUnexposed([]); // 선택 상태 초기화
        setSelectedExposed([]); // 선택 상태 초기화
        setError(null);
        onClose();
    };

    if (!isOpen || !policy) return null;

    return (
        <div className="modal-overlay" onClick={handleClose}>
            <div className="policy-exposure-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2>정책 노출 설정</h2>
                    <p>'{policy.title}' 정책을 노출할 협력사를 선택하세요.</p>
                    <button className="close-btn" onClick={handleClose} disabled={saving}>
                        ×
                    </button>
                </div>

                <div className="modal-content">
                    {loading ? (
                        <div className="loading">협력사 목록을 불러오는 중...</div>
                    ) : error ? (
                        <div className="error-message">{error}</div>
                    ) : agencies.length === 0 ? (
                        <div className="no-data">등록된 협력사가 없습니다.</div>
                    ) : (
                        <>
                            <div className="selection-summary">
                                <div className="summary-info">
                                    총 {agencies.length}개 협력사 중 {selectedAgencies.length}개 노출
                                </div>
                            </div>

                            <div className="dual-panel-container">
                                {/* 비노출 업체 (왼쪽) */}
                                <div className="panel unexposed-panel">
                                    <div className="panel-header">
                                        <h3>비노출 업체</h3>
                                        <span className="count">
                                            {agencies.filter(a => !selectedAgencies.includes(a.id)).length}개
                                        </span>
                                    </div>
                                    <div className="panel-content">
                                        {agencies
                                            .filter(agency => !selectedAgencies.includes(agency.id))
                                            .map(agency => (
                                                <div 
                                                    key={agency.id}
                                                    className={`agency-card ${selectedUnexposed.includes(agency.id) ? 'selected' : ''}`}
                                                    onClick={() => !saving && toggleUnexposedSelection(agency.id)}
                                                    onDoubleClick={() => !saving && moveToExposed(agency.id)}
                                                >
                                                    <div className="agency-info">
                                                        <div className="agency-name">{agency.name}</div>
                                                        <div className="agency-details">
                                                            <span className="agency-code">{agency.code}</span>
                                                            <span className="agency-status">
                                                                {agency.status ? '활성' : '비활성'}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <div className="selection-checkbox">
                                                        <input 
                                                            type="checkbox"
                                                            checked={selectedUnexposed.includes(agency.id)}
                                                            onChange={() => toggleUnexposedSelection(agency.id)}
                                                            onClick={e => e.stopPropagation()}
                                                            disabled={saving}
                                                        />
                                                    </div>
                                                </div>
                                            ))
                                        }
                                        {agencies.filter(a => !selectedAgencies.includes(a.id)).length === 0 && (
                                            <div className="empty-panel">모든 업체가 노출되었습니다</div>
                                        )}
                                    </div>
                                </div>

                                {/* 컨트롤 버튼 (가운데) */}
                                <div className="control-buttons">
                                    <button 
                                        className="btn btn-control"
                                        onClick={moveAllToExposed}
                                        disabled={saving || agencies.filter(a => !selectedAgencies.includes(a.id)).length === 0}
                                        title="모두 노출"
                                    >
                                        &gt;&gt;
                                    </button>
                                    <button 
                                        className="btn btn-control"
                                        onClick={moveSelectedToExposed}
                                        disabled={saving || selectedUnexposed.length === 0}
                                        title={`선택된 ${selectedUnexposed.length}개 업체 노출`}
                                    >
                                        &gt;
                                    </button>
                                    <button 
                                        className="btn btn-control"
                                        onClick={moveSelectedToUnexposed}
                                        disabled={saving || selectedExposed.length === 0}
                                        title={`선택된 ${selectedExposed.length}개 업체 비노출`}
                                    >
                                        &lt;
                                    </button>
                                    <button 
                                        className="btn btn-control"
                                        onClick={moveAllToUnexposed}
                                        disabled={saving || selectedAgencies.length === 0}
                                        title="모두 비노출"
                                    >
                                        &lt;&lt;
                                    </button>
                                </div>

                                {/* 노출 업체 (오른쪽) */}
                                <div className="panel exposed-panel">
                                    <div className="panel-header">
                                        <h3>노출 업체</h3>
                                        <span className="count">{selectedAgencies.length}개</span>
                                    </div>
                                    <div className="panel-content">
                                        {agencies
                                            .filter(agency => selectedAgencies.includes(agency.id))
                                            .map(agency => (
                                                <div 
                                                    key={agency.id}
                                                    className={`agency-card exposed ${selectedExposed.includes(agency.id) ? 'selected' : ''}`}
                                                    onClick={() => !saving && toggleExposedSelection(agency.id)}
                                                    onDoubleClick={() => !saving && moveToUnexposed(agency.id)}
                                                >
                                                    <div className="agency-info">
                                                        <div className="agency-name">{agency.name}</div>
                                                        <div className="agency-details">
                                                            <span className="agency-code">{agency.code}</span>
                                                            <span className="agency-status">
                                                                {agency.status ? '활성' : '비활성'}
                                                            </span>
                                                        </div>
                                                    </div>
                                                    <div className="selection-checkbox">
                                                        <input 
                                                            type="checkbox"
                                                            checked={selectedExposed.includes(agency.id)}
                                                            onChange={() => toggleExposedSelection(agency.id)}
                                                            onClick={e => e.stopPropagation()}
                                                            disabled={saving}
                                                        />
                                                    </div>
                                                </div>
                                            ))
                                        }
                                        {selectedAgencies.length === 0 && (
                                            <div className="empty-panel">노출된 업체가 없습니다</div>
                                        )}
                                    </div>
                                </div>
                            </div>

                            <div className="usage-hint">
                                💡 업체를 클릭하여 선택하고, 더블클릭하거나 가운데 화살표 버튼을 사용하여 노출 상태를 변경할 수 있습니다.
                            </div>
                        </>
                    )}
                </div>

                <div className="modal-actions">
                    <button 
                        className="btn btn-secondary"
                        onClick={handleClose}
                        disabled={saving}
                    >
                        취소
                    </button>
                    <button 
                        className="btn btn-primary"
                        onClick={handleSave}
                        disabled={loading || saving || agencies.length === 0}
                    >
                        {saving ? '저장 중...' : '노출 설정 저장'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PolicyExposureModal;