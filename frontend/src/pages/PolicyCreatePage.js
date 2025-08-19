import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { post } from '../services/api';
import MatrixRebateEditor from '../components/MatrixRebateEditor';
import './PolicyCreatePage.css';

const PolicyCreatePage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [errors, setErrors] = useState({});
    
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
        is_active: true,
        activation_notes: '', // 개통시 유의사항
        common_notes: '',    // 공통 유의사항
        grades: []           // 그레이드 설정 배열 [{count: 50, amount: 20000}, {count: 100, amount: 30000}]
    });
    
    const [rebateMatrix, setRebateMatrix] = useState([]);

    const carriers = [
        { value: 'skt', label: 'SKT' },
        { value: 'kt', label: 'KT' },
        { value: 'lg', label: 'LG U+' }
    ];



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
        console.log('[PolicyCreatePage] 정책 생성 시작');

        if (!validateForm()) {
            console.log('[PolicyCreatePage] 유효성 검사 실패');
            return;
        }

        setLoading(true);
        setErrors({});

        try {
            // 정책 생성
            const policyResponse = await post('api/policies/', formData);
            console.log('[PolicyCreatePage] 정책 생성 응답:', policyResponse);

            if (policyResponse.success) {
                const policyId = policyResponse.data.id;
                
                // 수수료 매트릭스 저장 (TODO: 백엔드 API 구현 후 활성화)
                if (rebateMatrix.length > 0) {
                    try {
                        const matrixResponse = await post(`api/policies/${policyId}/rebate-matrix/`, {
                            matrix: rebateMatrix
                        });
                        console.log('[PolicyCreatePage] 수수료 매트릭스 저장 응답:', matrixResponse);
                    } catch (matrixError) {
                        console.warn('[PolicyCreatePage] 수수료 매트릭스 저장 실패 (API 미구현):', matrixError);
                        // 수수료 매트릭스 저장 실패는 정책 생성을 막지 않음
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
                <p>새로운 정책을 생성하고 수수료를 설정합니다.</p>
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

                                        <div className="form-row">
                        <div className="form-group checkbox-group">
                            <label>
                                <input
                                    type="checkbox"
                                    name="is_active"
                                    checked={formData.is_active}
                                    onChange={handleChange}
                                    disabled={loading}
                                />
                                정책 활성화
                            </label>
                            <span className="field-hint">체크하면 정책이 활성화됩니다.</span>
                        </div>
                    </div>
                </div>
                
                <div className="form-section">
                    <div className="form-header">
                        <h3>그레이드 설정</h3>
                        <button 
                            type="button" 
                            className="btn btn-sm btn-primary" 
                            onClick={() => handleAddGrade()}
                            disabled={loading}
                        >
                            그레이드 추가 +
                        </button>
                    </div>
                    
                    <div className="grade-settings-container">
                        {formData.grades && formData.grades.length > 0 ? (
                            formData.grades.map((grade, index) => (
                                <div key={index} className="grade-row">
                                    <div className="grade-input-group">
                                        <input
                                            type="number"
                                            value={grade.count}
                                            onChange={(e) => handleGradeChange(index, 'count', e.target.value)}
                                            disabled={loading}
                                            min="1"
                                            placeholder="건수"
                                        />
                                        <span className="grade-text">이상</span>
                                        <input
                                            type="number"
                                            value={grade.amount}
                                            onChange={(e) => handleGradeChange(index, 'amount', e.target.value)}
                                            disabled={loading}
                                            min="1000"
                                            step="1000"
                                            placeholder="수수료"
                                        />
                                        <button
                                            type="button"
                                            className="btn btn-sm btn-danger"
                                            onClick={() => handleRemoveGrade(index)}
                                            disabled={loading}
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
                </div>

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
                
                <div className="form-section">
                    <h3>유의사항</h3>
                    
                    <div className="form-group">
                        <label htmlFor="activation_notes">개통시 유의사항</label>
                        <textarea
                            id="activation_notes"
                            name="activation_notes"
                            value={formData.activation_notes}
                            onChange={handleChange}
                            disabled={loading}
                            placeholder="개통시 유의해야 할 사항을 입력하세요"
                            rows="5"
                        />
                    </div>
                    
                    <div className="form-group">
                        <label htmlFor="common_notes">공통 유의사항</label>
                        <textarea
                            id="common_notes"
                            name="common_notes"
                            value={formData.common_notes}
                            onChange={handleChange}
                            disabled={loading}
                            placeholder="공통적으로 유의해야 할 사항을 입력하세요"
                            rows="5"
                        />
                    </div>
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