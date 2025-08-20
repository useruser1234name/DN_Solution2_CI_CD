import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, put, post } from '../services/api';
import MatrixRebateEditor from '../components/MatrixRebateEditor';
import CommissionGradeInput from '../components/CommissionGradeInput';
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
    
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        carrier: 'skt',
        expose: true,
        premium_market_expose: false,
        is_active: true,
        grade_period_type: 'monthly'
    });
    
    const [commissionGrades, setCommissionGrades] = useState([]);
    const [rebateMatrix, setRebateMatrix] = useState([]);

    const carriers = [
        { value: 'skt', label: 'SKT' },
        { value: 'kt', label: 'KT' },
        { value: 'lg', label: 'LG U+' }
    ];

    const gradePeriodTypes = [
        { value: 'monthly', label: '월별 (매월 1일 기준 리셋)' },
        { value: 'quarterly', label: '분기별 (분기 시작일 기준 리셋)' },
        { value: 'yearly', label: '연간 (매년 1월 1일 기준 리셋)' },
        { value: 'policy_lifetime', label: '정책 전체 기간 (정책 활성화 이후 누적)' }
    ];

    useEffect(() => {
        if (id) {
            fetchPolicy();
        }
    }, [id]);

    const fetchPolicy = async () => {
        try {
            setLoading(true);
            
            const response = await get(`api/policies/${id}/`);
            console.log('[PolicyEditPage] 정책 상세 응답:', response);

            if (response.success) {
                let policy = response.data;
                if (policy.success && policy.data) {
                    policy = policy.data;
                }
                
                setOriginalPolicy(policy);
                setFormData({
                    title: policy.title || '',
                    description: policy.description || '',
                    carrier: policy.carrier || 'skt',
                    is_active: policy.is_active !== false,
                    grade_period_type: policy.grade_period_type || 'monthly'
                });

                // 수수료 그레이드 로드
                if (policy.commission_grades && Array.isArray(policy.commission_grades)) {
                    setCommissionGrades(policy.commission_grades);
                }

                // 기존 수수료 매트릭스 로드
                try {
                    const matrixResponse = await get(`api/policies/${id}/commission-matrix/`);
                    if (matrixResponse && matrixResponse.success && matrixResponse.data) {
                        let matrixData = matrixResponse.data;
                        if (matrixData.success && matrixData.data) {
                            matrixData = matrixData.data;
                        }
                        
                        if (matrixData.matrix && Array.isArray(matrixData.matrix) && matrixData.matrix.length > 0) {
                            setRebateMatrix(matrixData.matrix);
                        } else {
                            setRebateMatrix(getDefaultMatrix());
                        }
                    } else {
                        setRebateMatrix(getDefaultMatrix());
                    }
                } catch (matrixError) {
                    console.warn('[PolicyEditPage] 수수료 매트릭스 로딩 실패, 기본값 사용:', matrixError);
                    setRebateMatrix(getDefaultMatrix());
                }
            } else {
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
            [name]: type === 'checkbox' ? checked : (type === 'number' ? Number(value) : value)
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



        // 그레이드 검증
        if (commissionGrades.length > 0) {
            const minOrdersList = commissionGrades.map(g => g.min_orders).filter(Boolean);
            const duplicates = minOrdersList.filter((item, index) => minOrdersList.indexOf(item) !== index);
            if (duplicates.length > 0) {
                newErrors.commission_grades = '동일한 최소 주문건수가 중복됩니다.';
            }
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
            return;
        }

        setSaving(true);
        setErrors({});

        try {
            // 정책 데이터 준비
            const policyData = {
                ...formData,
                commission_grades: commissionGrades
            };

            // 정책 수정
            const policyResponse = await put(`api/policies/${id}/`, policyData);

            if (policyResponse.success) {
                // 수수료 매트릭스 저장
                if (rebateMatrix.length > 0) {
                    try {
                        const matrixResponse = await post(`api/policies/${id}/commission-matrix/`, {
                            matrix: rebateMatrix
                        });
                        console.log('[PolicyEditPage] 수수료 매트릭스 수정 응답:', matrixResponse);
                    } catch (matrixError) {
                        console.warn('[PolicyEditPage] 수수료 매트릭스 저장 실패:', matrixError);
                    }
                }
                
                alert('정책이 성공적으로 수정되었습니다.');
                setViewMode('view');
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
                {/* 기본 정보 섹션 */}
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
                </div>



                {/* 수수료 그레이드 설정 섹션 */}
                <div className="form-section">
                    <CommissionGradeInput
                        value={commissionGrades}
                        onChange={setCommissionGrades}
                        disabled={saving || viewMode === 'view'}
                        title="수수료 그레이드 설정"
                    />
                    {errors.commission_grades && (
                        <div className="error-message">{errors.commission_grades}</div>
                    )}
                </div>

                {/* 그레이드 적용 기간 설정 */}
                <div className="form-section">
                    <h3>그레이드 적용 설정</h3>
                    
                    <div className="form-group">
                        <label htmlFor="grade_period_type">그레이드 적용 기간</label>
                        <select
                            id="grade_period_type"
                            name="grade_period_type"
                            value={formData.grade_period_type}
                            onChange={handleChange}
                            disabled={saving || viewMode === 'view'}
                        >
                            {gradePeriodTypes.map(period => (
                                <option key={period.value} value={period.value}>
                                    {period.label}
                                </option>
                            ))}
                        </select>
                        <span className="field-hint">그레이드 달성을 위한 주문량 집계 기간을 설정합니다.</span>
                    </div>
                </div>

                {/* 정책 활성화 설정 */}
                <div className="form-section">
                    <h3>정책 활성화 설정</h3>
                    
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

                {/* 수수료 매트릭스 섹션 */}
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

                {errors.general && (
                    <div className="error-message">
                        {errors.general}
                    </div>
                )}
            </form>
        </div>
    );
};

export default PolicyEditPage;