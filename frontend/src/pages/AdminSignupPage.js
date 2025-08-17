import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { post } from '../services/api';
import './AdminSignupPage.css';

const AdminSignupPage = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        passwordConfirm: '',
        companyName: '',
        companyType: '',
        parentCode: ''
    });
    const [errors, setErrors] = useState({});
    const [successMessage, setSuccessMessage] = useState('');

    const companyTypes = [
        { value: 'headquarters', label: '본사' },
        { value: 'agency', label: '협력사' },
        { value: 'dealer', label: '대리점' },
        { value: 'retail', label: '판매점' }
    ];

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
        
        // 에러 메시지 제거
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }));
        }

        // 본사 선택 시 상위 업체 코드 초기화
        if (name === 'companyType' && value === 'headquarters') {
            setFormData(prev => ({
                ...prev,
                parentCode: ''
            }));
        }
    };

    const validateForm = () => {
        const newErrors = {};

        if (!formData.username) {
            newErrors.username = '아이디를 입력해주세요.';
        } else if (formData.username.length < 4) {
            newErrors.username = '아이디는 4자 이상이어야 합니다.';
        }

        if (!formData.password) {
            newErrors.password = '비밀번호를 입력해주세요.';
        } else if (formData.password.length < 8) {
            newErrors.password = '비밀번호는 8자 이상이어야 합니다.';
        }

        if (!formData.passwordConfirm) {
            newErrors.passwordConfirm = '비밀번호 확인을 입력해주세요.';
        } else if (formData.password !== formData.passwordConfirm) {
            newErrors.passwordConfirm = '비밀번호가 일치하지 않습니다.';
        }

        if (!formData.companyName) {
            newErrors.companyName = '업체명을 입력해주세요.';
        }

        if (!formData.companyType) {
            newErrors.companyType = '업체 유형을 선택해주세요.';
        }

        // 본사가 아닌 경우 상위 업체 코드 필수
        if (formData.companyType && formData.companyType !== 'headquarters' && !formData.parentCode) {
            newErrors.parentCode = '상위 업체 코드를 입력해주세요.';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('[AdminSignupPage] 회원가입 폼 제출');
        
        if (formData.password !== formData.passwordConfirm) {
            setError('비밀번호가 일치하지 않습니다.');
            return;
        }
        
        if (!formData.companyType) {
            setError('업체 유형을 선택해주세요.');
            return;
        }
        
        if (formData.companyType !== 'headquarters' && !formData.parentCode) {
            setError('상위 업체 코드를 입력해주세요.');
            return;
        }
        
        setLoading(true);
        setError('');
        
        try {
            const response = await post('api/companies/signup/admin/', {
                username: formData.username,
                password: formData.password,
                company_name: formData.companyName,
                company_type: formData.companyType,
                parent_code: formData.parentCode
            });
            console.log('[AdminSignupPage] 회원가입 응답:', response);
            
            if (response.success) {
                alert('회원가입이 완료되었습니다. 관리자 승인이 필요합니다.');
                navigate('/login');
            } else {
                setError(typeof response.error === 'string' ? response.error : JSON.stringify(response.error));
            }
        } catch (err) {
            console.error('[AdminSignupPage] 회원가입 중 오류:', err);
            setError('회원가입 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        navigate('/signup');
    };

    return (
        <div className="admin-signup-container">
            <div className="admin-signup-box">
                <h1>관리자 회원가입</h1>
                <p className="subtitle">새로운 업체를 등록하고 관리자로 가입합니다</p>

                {successMessage && (
                    <div className="success-message">
                        {successMessage}
                        <p className="redirect-info">잠시 후 로그인 페이지로 이동합니다...</p>
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <div className="form-section">
                        <h3>계정 정보</h3>
                        
                        <div className="form-group">
                            <label htmlFor="username">아이디 *</label>
                            <input
                                type="text"
                                id="username"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                disabled={loading}
                                placeholder="4자 이상의 아이디"
                            />
                            {errors.username && <span className="error">{errors.username}</span>}
                        </div>

                        <div className="form-group">
                            <label htmlFor="password">비밀번호 *</label>
                            <input
                                type="password"
                                id="password"
                                name="password"
                                value={formData.password}
                                onChange={handleChange}
                                disabled={loading}
                                placeholder="8자 이상의 비밀번호"
                            />
                            {errors.password && <span className="error">{errors.password}</span>}
                        </div>

                        <div className="form-group">
                            <label htmlFor="passwordConfirm">비밀번호 확인 *</label>
                            <input
                                type="password"
                                id="passwordConfirm"
                                name="passwordConfirm"
                                value={formData.passwordConfirm}
                                onChange={handleChange}
                                disabled={loading}
                                placeholder="비밀번호를 다시 입력하세요"
                            />
                            {errors.passwordConfirm && <span className="error">{errors.passwordConfirm}</span>}
                        </div>
                    </div>

                    <div className="form-section">
                        <h3>업체 정보</h3>
                        
                        <div className="form-group">
                            <label htmlFor="companyName">업체명 *</label>
                            <input
                                type="text"
                                id="companyName"
                                name="companyName"
                                value={formData.companyName}
                                onChange={handleChange}
                                disabled={loading}
                                placeholder="업체명을 입력하세요"
                            />
                            {errors.companyName && <span className="error">{errors.companyName}</span>}
                        </div>

                        <div className="form-group">
                            <label htmlFor="companyType">업체 유형 *</label>
                            <select
                                id="companyType"
                                name="companyType"
                                value={formData.companyType}
                                onChange={handleChange}
                                disabled={loading}
                            >
                                <option value="">선택하세요</option>
                                {companyTypes.map(type => (
                                    <option key={type.value} value={type.value}>
                                        {type.label}
                                    </option>
                                ))}
                            </select>
                            {errors.companyType && <span className="error">{errors.companyType}</span>}
                        </div>

                        {formData.companyType && formData.companyType !== 'headquarters' && (
                            <div className="form-group">
                                <label htmlFor="parentCode">상위 업체 코드 *</label>
                                <input
                                    type="text"
                                    id="parentCode"
                                    name="parentCode"
                                    value={formData.parentCode}
                                    onChange={handleChange}
                                    disabled={loading}
                                    placeholder="상위 업체 코드를 입력하세요"
                                />
                                {errors.parentCode && <span className="error">{errors.parentCode}</span>}
                                <p className="field-hint">
                                    {formData.companyType === 'agency' && '본사의 업체 코드를 입력하세요'}
                                    {formData.companyType === 'dealer' && '본사의 업체 코드를 입력하세요'}
                                    {formData.companyType === 'retail' && '협력사 또는 대리점의 업체 코드를 입력하세요'}
                                </p>
                            </div>
                        )}
                    </div>

                    {errors.general && (
                        <div className="error-message">
                            {errors.general}
                        </div>
                    )}

                    <div className="form-actions">
                        <button type="button" onClick={handleBack} className="back-button" disabled={loading}>
                            이전으로
                        </button>
                        <button type="submit" className="submit-button" disabled={loading}>
                            {loading ? '가입 중...' : '회원가입'}
                        </button>
                    </div>
                </form>

                <div className="signup-info">
                    <p className="info-text">
                        * 회원가입 후 상위 업체 관리자의 승인이 필요합니다.<br/>
                        * 본사는 자동으로 승인됩니다.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default AdminSignupPage;
