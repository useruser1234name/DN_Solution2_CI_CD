import React, { useState } from 'react';
import ToggleSwitch from '../components/common/ToggleSwitch';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { post } from '../services/api';
import MatrixRebateEditor from '../components/MatrixRebateEditor';
import CommissionGradeInput from '../components/CommissionGradeInput';
import './PolicyCreatePage.css';

const PolicyCreatePage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});
    
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        carrier: 'skt',
        external_url: '',
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
        console.log('[PolicyCreatePage] 정책 생성 시작');

        if (!validateForm()) {
            console.log('[PolicyCreatePage] 유효성 검사 실패');
            return;
        }

        setLoading(true);
        setErrors({});

        try {
            // 정책 데이터 준비
            const policyData = {
                ...formData,
                commission_grades: commissionGrades
            };

            // 정책 생성
            const policyResponse = await post('api/policies/', policyData);
            console.log('[PolicyCreatePage] 정책 생성 응답:', policyResponse);

            if (policyResponse.success) {
                const policyId = policyResponse.data.id;
                
                // 수수료 매트릭스 저장
                if (rebateMatrix.length > 0) {
                    try {
                        const matrixResponse = await post(`api/policies/${policyId}/commission-matrix/`, {
                            matrix: rebateMatrix
                        });
                        console.log('[PolicyCreatePage] 수수료 매트릭스 저장 응답:', matrixResponse);
                    } catch (matrixError) {
                        console.warn('[PolicyCreatePage] 수수료 매트릭스 저장 실패:', matrixError);
                    }
                }
                
                alert('정책이 성공적으로 생성되었습니다.');
                navigate('/policies');
            } else {
                setErrors({ general: policyResponse.error || '정책 생성에 실패했습니다.' });
            }
        } catch (error) {
            console.error('[PolicyCreatePage] 정책 생성 실패:', error);
            setErrors({ general: '정책 생성 중 오류가 발생했습니다.' });
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        navigate('/policies');
    };

    return (
        <div className="policy-create-page">
            <div className="page-header">
                <h1>새 정책 생성</h1>
                <p>새로운 정책을 생성하고 수수료 및 그레이드를 설정합니다.</p>
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
                            disabled={loading}
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
                            disabled={loading}
                            placeholder="정책 설명을 입력하세요"
                            rows="3"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="external_url">정책 URL</label>
                        <input
                            type="url"
                            id="external_url"
                            name="external_url"
                            value={formData.external_url}
                            onChange={handleChange}
                            disabled={loading}
                            placeholder="정책 URL을 입력하세요"
                            inputMode="url"
                            pattern="https?://.+"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="carrier">통신사 *</label>
                        <select
                            id="carrier"
                            name="carrier"
                            value={formData.carrier}
                            onChange={handleChange}
                            disabled={loading}
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
                        disabled={loading}
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
                            disabled={loading}
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
                    <div className="form-group">
                        <div>
                            <ToggleSwitch
                                checked={formData.is_active}
                                onChange={(next) => setFormData(prev => ({ ...prev, is_active: next }))}
                                disabled={loading}
                                onColor="#4caf50"
                                offColor="#d9d9d9"
                            />
                        </div>
                        <span className="field-hint">활성화 시 정책이 즉시 사용 및 노출됩니다.</span>
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
                        disabled={loading}
                        carrier={formData.carrier || 'KT'}
                    />
                </div>

                {errors.general && (
                    <div className="error-message">
                        {errors.general}
                    </div>
                )}

                <div className="form-actions">
                    <button 
                        type="button" 
                        onClick={handleCancel} 
                        className="btn btn-secondary"
                        disabled={loading}
                    >
                        취소
                    </button>
                    <button 
                        type="submit" 
                        className="btn btn-primary"
                        disabled={loading}
                    >
                        {loading ? '생성 중...' : '정책 생성'}
                    </button>
                </div>
            </form>
        </div>
    );
};

export default PolicyCreatePage;