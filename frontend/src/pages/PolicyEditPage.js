import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, put, post } from '../services/api';
import MatrixRebateEditor from '../components/MatrixRebateEditor';
import './PolicyCreatePage.css'; // 동일한 스타일 사용

const PolicyEditPage = () => {
    const { id } = useParams();
    const { user } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [errors, setErrors] = useState({});
    const [originalPolicy, setOriginalPolicy] = useState(null);
    const [viewMode, setViewMode] = useState('view'); // 'view' 또는 'edit'
    
    // 그레이드 추가 핸들러
    const handleAddGrade = () => {
        setFormData(prev => ({
            ...prev,
            grades: [...prev.grades, { count: '', amount: '' }]
        }));
    };
    
    // 그레이드 변경 핸들러
    const handleGradeChange = (index, field, value) => {
        const updatedGrades = [...formData.grades];
        updatedGrades[index][field] = value;
        
        setFormData(prev => ({
            ...prev,
            grades: updatedGrades
        }));
    };
    
    // 그레이드 삭제 핸들러
    const handleRemoveGrade = (index) => {
        const updatedGrades = formData.grades.filter((_, i) => i !== index);
        
        setFormData(prev => ({
            ...prev,
            grades: updatedGrades
        }));
    };
    
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        carrier: 'skt',
        expose: true,
        is_active: true,
        activation_notes: '',
        common_notes: '',
        grades: []
    });
    
    const [rebateMatrix, setRebateMatrix] = useState([]);

    const carriers = [
        { value: 'skt', label: 'SKT' },
        { value: 'kt', label: 'KT' },
        { value: 'lg', label: 'LG U+' }
    ];

    console.log('[PolicyEditPage] 컴포넌트 렌더링', { id, user: user?.username });

    useEffect(() => {
        if (id) {
            fetchPolicy();
        }
    }, [id]);

    const fetchPolicy = async () => {
        console.log('[PolicyEditPage] 정책 정보 가져오기 시작:', id);
        
        try {
            setLoading(true);
            
            const response = await get(`api/policies/${id}/`);
            console.log('[PolicyEditPage] 정책 상세 응답:', response);

            if (response.success) {
                // 이중 래핑 확인 및 처리
                let policy = response.data;
                if (policy.success && policy.data) {
                    console.log('[PolicyEditPage] 이중 래핑된 정책 응답 감지');
                    policy = policy.data;
                }
                
                console.log('[PolicyEditPage] 정책 데이터:', policy);
                setOriginalPolicy(policy);
                setFormData({
                    title: policy.title || '',
                    description: policy.description || '',
                    carrier: policy.carrier || 'skt',
                    expose: policy.expose !== false,
                    is_active: policy.is_active !== false,
                    activation_notes: policy.activation_notes || '',
                    common_notes: policy.common_notes || '',
                    grades: policy.grades || []
                });

                // 기존 리베이트 매트릭스 로드
                try {
                    const matrixResponse = await get(`api/policies/${id}/rebate-matrix/`);
                    console.log('[PolicyEditPage] 리베이트 매트릭스 원본 응답:', matrixResponse);
                    console.log('[PolicyEditPage] 응답 타입:', typeof matrixResponse);
                    console.log('[PolicyEditPage] 응답 키들:', Object.keys(matrixResponse || {}));
                    
                    if (matrixResponse && matrixResponse.success && matrixResponse.data) {
                        // 이중 래핑 확인 및 처리
                        let matrixData = matrixResponse.data;
                        console.log('[PolicyEditPage] 매트릭스 데이터 (1차):', matrixData);
                        console.log('[PolicyEditPage] 매트릭스 데이터 타입:', typeof matrixData);
                        console.log('[PolicyEditPage] 매트릭스 데이터 키들:', Object.keys(matrixData || {}));
                        
                        if (matrixData.success && matrixData.data) {
                            console.log('[PolicyEditPage] 이중 래핑된 매트릭스 응답 감지');
                            matrixData = matrixData.data;
                        }
                        
                        console.log('[PolicyEditPage] 최종 매트릭스 데이터:', matrixData);
                        console.log('[PolicyEditPage] 매트릭스 배열:', matrixData.matrix);
                        console.log('[PolicyEditPage] 매트릭스 배열 길이:', matrixData.matrix ? matrixData.matrix.length : 'undefined');
                        
                        if (matrixData.matrix && Array.isArray(matrixData.matrix) && matrixData.matrix.length > 0) {
                            console.log('[PolicyEditPage] 매트릭스 첫 번째 항목:', matrixData.matrix[0]);
                            setRebateMatrix(matrixData.matrix);
                        } else {
                            console.log('[PolicyEditPage] 매트릭스 배열이 비어있음, 기본값 사용');
                            setRebateMatrix(getDefaultMatrix());
                        }
                    } else {
                        console.log('[PolicyEditPage] 매트릭스 응답 구조 문제, 기본값 사용');
                        console.log('[PolicyEditPage] success:', matrixResponse?.success);
                        console.log('[PolicyEditPage] data:', matrixResponse?.data);
                        // 기본 매트릭스 설정
                        setRebateMatrix(getDefaultMatrix());
                    }
                } catch (matrixError) {
                    console.warn('[PolicyEditPage] 리베이트 매트릭스 로딩 실패, 기본값 사용:', matrixError);
                    setRebateMatrix(getDefaultMatrix());
                }
            } else {
                console.error('[PolicyEditPage] 정책 상세 실패:', response.message);
                setErrors({ general: '정책 정보를 불러오는데 실패했습니다.' });
            }
        } catch (error) {
            console.error('[PolicyEditPage] 정책 상세 로딩 실패:', error);
            setErrors({ general: '정책 정보를 불러오는 중 오류가 발생했습니다.' });
        } finally {
            setLoading(false);
        }
    };

    const getDefaultMatrix = () => {
        // 기본 9x3 매트릭스 생성
        const planRanges = ['11K', '22K', '33K', '44K', '55K', '66K', '77K', '88K', '99K'];
        const contractPeriods = [12, 24, 36];
        const matrix = [];

        planRanges.forEach((planRange, rowIndex) => {
            contractPeriods.forEach((period, colIndex) => {
                matrix.push({
                    id: `${rowIndex}-${colIndex}`,
                    plan_range: planRange,
                    contract_period: period,
                    rebate_amount: 0,
                    row: rowIndex,
                    col: colIndex
                });
            });
        });

        return matrix;
    };

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
        
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }));
        }
    };

    const validateForm = () => {
        const newErrors = {};

        if (!formData.title) {
            newErrors.title = '정책명을 입력해주세요.';
        }

        if (!formData.carrier) {
            newErrors.carrier = '통신사를 선택해주세요.';
        }

        if (rebateMatrix.length === 0) {
            newErrors.rebateMatrix = '최소 하나 이상의 수수료를 설정해주세요.';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('[PolicyEditPage] 정책 수정 시작');

        if (!validateForm()) {
            console.log('[PolicyEditPage] 유효성 검사 실패');
            return;
        }

        setSaving(true);
        setErrors({});

        try {
            // 정책 수정
            const policyResponse = await put(`api/policies/${id}/`, formData);
            console.log('[PolicyEditPage] 정책 수정 응답:', policyResponse);

            if (policyResponse.success) {
                // 리베이트 매트릭스 저장 (TODO: 백엔드 API 구현 후 활성화)
                if (rebateMatrix.length > 0) {
                    try {
                        const matrixResponse = await post(`api/policies/${id}/rebate-matrix/`, {
                            matrix: rebateMatrix
                        });
                        console.log('[PolicyEditPage] 리베이트 매트릭스 수정 응답:', matrixResponse);
                    } catch (matrixError) {
                        console.warn('[PolicyEditPage] 리베이트 매트릭스 저장 실패 (API 미구현):', matrixError);
                        // 리베이트 매트릭스 저장 실패는 정책 수정을 막지 않음
                    }
                }
                
                alert('정책이 성공적으로 수정되었습니다.');
                setViewMode('view'); // 저장 후 보기 모드로 전환
            } else {
                setErrors({ general: policyResponse.error || '정책 수정에 실패했습니다.' });
            }
        } catch (error) {
            console.error('[PolicyEditPage] 정책 수정 실패:', error);
            setErrors({ general: '정책 수정 중 오류가 발생했습니다.' });
        } finally {
            setSaving(false);
        }
    };

    const handleCancel = () => {
        if (window.confirm('수정을 취소하시겠습니까? 변경사항은 저장되지 않습니다.')) {
            navigate('/policies');
        }
    };

    if (loading) {
        return (
            <div className="policy-create-page">
                <div className="loading">정책 정보를 불러오는 중...</div>
            </div>
        );
    }

    if (!originalPolicy) {
        return (
            <div className="policy-create-page">
                <div className="error-message">정책을 찾을 수 없습니다.</div>
                <button className="btn btn-secondary" onClick={() => navigate('/policies')}>
                    목록으로 돌아가기
                </button>
            </div>
        );
    }

    return (
        <div className="policy-create-page">
            <div className="page-header">
                <div className="header-content">
                    <div className="header-left">
                        <button className="back-btn" onClick={() => navigate('/policies')}>
                            ← 목록으로
                        </button>
                        <div className="header-info">
                            <h1>
                                {viewMode === 'view' ? '정책 보기' : '정책 편집'}
                            </h1>
                            <p>
                                {originalPolicy?.title} 정책의 {viewMode === 'view' ? '상세 정보입니다' : '정보를 편집합니다'}.
                            </p>
                        </div>
                    </div>
                    <div className="header-actions">
                        {viewMode === 'view' ? (
                            <>
                                <button 
                                    className="btn btn-primary"
                                    onClick={() => setViewMode('edit')}
                                >
                                    편집
                                </button>
                                <button 
                                    className="btn btn-secondary"
                                    onClick={() => navigate('/policies')}
                                >
                                    확인
                                </button>
                            </>
                        ) : (
                            <>
                                <button 
                                    className="btn btn-secondary"
                                    onClick={() => setViewMode('view')}
                                >
                                    미리보기
                                </button>
                                <button 
                                    className="btn btn-primary"
                                    onClick={handleSubmit}
                                    disabled={saving}
                                >
                                    {saving ? '저장 중...' : '저장'}
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="policy-form">
                <div className="form-section">
                    <h3>기본 정보</h3>
                    
                    <div className="form-group">
                        <label htmlFor="title">정책명 *</label>
                        <input
                            type="text"
                            id="title"
                            name="title"
                            value={formData.title}
                            onChange={handleChange}
                            disabled={saving || viewMode === 'view'}
                            readOnly={viewMode === 'view'}
                            placeholder="정책명을 입력하세요"
                        />
                        {errors.title && <span className="error">{errors.title}</span>}
                    </div>

                    <div className="form-group">
                        <label htmlFor="description">설명</label>
                        <textarea
                            id="description"
                            name="description"
                            value={formData.description}
                            onChange={handleChange}
                            disabled={saving || viewMode === 'view'}
                            readOnly={viewMode === 'view'}
                            placeholder="정책 설명을 입력하세요"
                            rows="3"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="carrier">통신사 *</label>
                        <select
                            id="carrier"
                            name="carrier"
                            value={formData.carrier}
                            onChange={handleChange}
                            disabled={saving || viewMode === 'view'}
                        >
                            {carriers.map(carrier => (
                                <option key={carrier.value} value={carrier.value}>
                                    {carrier.label}
                                </option>
                            ))}
                        </select>
                        {errors.carrier && <span className="error">{errors.carrier}</span>}
                    </div>

                    <div className="form-row">
                        <div className="form-group checkbox-group">
                            <label>
                                <input
                                    type="checkbox"
                                    name="is_active"
                                    checked={formData.is_active}
                                    onChange={handleChange}
                                    disabled={saving || viewMode === 'view'}
                                />
                                정책 활성화
                            </label>
                            <span className="field-hint">체크하면 정책이 활성화됩니다.</span>
                        </div>
                    </div>
                </div>

                <div className="form-section">
                    <h3>수수료 매트릭스</h3>
                    {errors.rebateMatrix && (
                        <div className="error-message">{errors.rebateMatrix}</div>
                    )}
                    <MatrixRebateEditor
                        matrix={rebateMatrix}
                        onChange={setRebateMatrix}
                        disabled={saving || viewMode === 'view'}
                        carrier={formData.carrier || 'KT'}
                    />
                </div>
                
                <div className="form-section">
                    <h3>그레이드 설정</h3>
                    {viewMode === 'edit' ? (
                        <div className="grade-settings-container">
                            <div className="form-header">
                                <button 
                                    type="button" 
                                    className="btn btn-sm btn-primary" 
                                    onClick={() => handleAddGrade()}
                                    disabled={saving}
                                >
                                    그레이드 추가 +
                                </button>
                            </div>
                            
                            {formData.grades && formData.grades.length > 0 ? (
                                formData.grades.map((grade, index) => (
                                    <div key={index} className="grade-row">
                                        <div className="grade-input-group">
                                            <input
                                                type="number"
                                                value={grade.count}
                                                onChange={(e) => handleGradeChange(index, 'count', e.target.value)}
                                                disabled={saving}
                                                min="1"
                                                placeholder="건수"
                                            />
                                            <span className="grade-text">이상</span>
                                            <input
                                                type="number"
                                                value={grade.amount}
                                                onChange={(e) => handleGradeChange(index, 'amount', e.target.value)}
                                                disabled={saving}
                                                min="1000"
                                                step="1000"
                                                placeholder="수수료"
                                            />
                                                                                            <button
                                                    type="button"
                                                    className="btn btn-sm btn-danger"
                                                    onClick={() => handleRemoveGrade(index)}
                                                    disabled={saving}
                                                    title="그레이드 삭제"
                                                >
                                                    삭제
                                                </button>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="no-grades-message">
                                    그레이드가 없습니다. 그레이드를 추가하세요.
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="grades-container">
                            {formData.grades && formData.grades.length > 0 ? (
                                formData.grades.map((grade, index) => (
                                    <div key={index} className="grade-item">
                                        <span className="grade-count">{grade.count}건 이상</span>
                                        <span className="grade-amount">{Number(grade.amount).toLocaleString()}원</span>
                                    </div>
                                ))
                            ) : (
                                <div className="no-grades-message">
                                    그레이드가 없습니다.
                                </div>
                            )}
                        </div>
                    )}
                </div>
                
                <div className="form-section">
                    <h3>유의사항</h3>
                    <div className="form-group">
                        <label htmlFor="activation_notes">개통시 유의사항</label>
                        <textarea
                            id="activation_notes"
                            name="activation_notes"
                            value={formData.activation_notes}
                            onChange={handleChange}
                            disabled={saving || viewMode === 'view'}
                            readOnly={viewMode === 'view'}
                            placeholder="개통시 유의사항을 입력하세요"
                            rows="4"
                        />
                    </div>
                    
                    <div className="form-group">
                        <label htmlFor="common_notes">공통 유의사항</label>
                        <textarea
                            id="common_notes"
                            name="common_notes"
                            value={formData.common_notes}
                            onChange={handleChange}
                            disabled={saving || viewMode === 'view'}
                            readOnly={viewMode === 'view'}
                            placeholder="공통 유의사항을 입력하세요"
                            rows="4"
                        />
                    </div>
                </div>

                {errors.general && (
                    <div className="error-message">
                        {errors.general}
                    </div>
                )}

                {/* 폼 액션 버튼들은 헤더로 이동됨 */}
            </form>
        </div>
    );
};

export default PolicyEditPage;