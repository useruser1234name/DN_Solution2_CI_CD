import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { post } from '../services/api';
import './StaffSignupPage.css';

const StaffSignupPage = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        passwordConfirm: '',
        companyCode: ''
    });
    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');

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

        if (!formData.companyCode) {
            newErrors.companyCode = '업체 코드를 입력해주세요.';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('[StaffSignupPage] 회원가입 폼 제출');

        if (!validateForm()) {
            console.log('[StaffSignupPage] 유효성 검사 실패');
            return;
        }

        setLoading(true);
        setErrors({});

        try {
            const response = await post('api/companies/signup/staff/', {
                username: formData.username,
                password: formData.password,
                company_code: formData.companyCode
            });

            console.log('[StaffSignupPage] 회원가입 응답:', response);

            if (response.success) {
                setSuccessMessage(response.message || '회원가입이 완료되었습니다.');
                
                // 3초 후 로그인 페이지로 이동
                setTimeout(() => {
                    navigate('/login');
                }, 3000);
            } else {
                setErrors({ general: response.error || '회원가입에 실패했습니다.' });
            }
        } catch (error) {
            console.error('[StaffSignupPage] 회원가입 실패:', error);
            setErrors({ general: '회원가입 중 오류가 발생했습니다.' });
        } finally {
            setLoading(false);
        }
    };

    const handleBack = () => {
        navigate('/signup');
    };

    return (
        <div className="staff-signup-container">
            <div className="staff-signup-box">
                <h1>직원 회원가입</h1>
                <p className="subtitle">본사 직원으로 가입합니다</p>

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
                        <h3>소속 정보</h3>
                        
                        <div className="form-group">
                            <label htmlFor="companyCode">본사 업체 코드 *</label>
                            <input
                                type="text"
                                id="companyCode"
                                name="companyCode"
                                value={formData.companyCode}
                                onChange={handleChange}
                                disabled={loading}
                                placeholder="본사 업체 코드를 입력하세요"
                            />
                            {errors.companyCode && <span className="error">{errors.companyCode}</span>}
                            <p className="field-hint">
                                관리자로부터 받은 본사 업체 코드를 입력하세요.
                            </p>
                        </div>
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
                    <div className="info-box warning">
                        <h4>⚠️ 주의사항</h4>
                        <ul>
                            <li>직원 가입은 <strong>본사만</strong> 가능합니다.</li>
                            <li>협력사, 대리점, 판매점은 직원 가입이 불가능합니다.</li>
                            <li>회원가입 후 본사 관리자의 승인이 필요합니다.</li>
                            <li>승인 전까지는 로그인이 제한됩니다.</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default StaffSignupPage;
