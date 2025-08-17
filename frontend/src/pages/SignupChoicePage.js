import React from 'react';
import { useNavigate } from 'react-router-dom';
import './SignupChoicePage.css';

const SignupChoicePage = () => {
    const navigate = useNavigate();

    const handleAdminSignup = () => {
        console.log('[SignupChoicePage] 관리자 회원가입 선택');
        navigate('/signup/admin');
    };

    const handleStaffSignup = () => {
        console.log('[SignupChoicePage] 직원 회원가입 선택');
        navigate('/signup/staff');
    };

    const handleBack = () => {
        console.log('[SignupChoicePage] 로그인 페이지로 돌아가기');
        navigate('/login');
    };

    return (
        <div className="signup-choice-container">
            <div className="signup-choice-box">
                <h1>회원가입 유형 선택</h1>
                <p className="subtitle">가입하실 유형을 선택해주세요</p>
                
                <div className="signup-options">
                    <div className="signup-option" onClick={handleAdminSignup}>
                        <div className="option-icon">👔</div>
                        <h2>관리자 가입</h2>
                        <p className="option-description">
                            새로운 업체를 등록하고 관리자로 가입합니다.
                        </p>
                        <ul className="option-features">
                            <li>새 업체 생성</li>
                            <li>업체 관리자 권한</li>
                            <li>직원 관리 가능</li>
                        </ul>
                        <button className="option-button">관리자로 가입하기</button>
                    </div>

                    <div className="signup-option" onClick={handleStaffSignup}>
                        <div className="option-icon">👥</div>
                        <h2>직원 가입</h2>
                        <p className="option-description">
                            기존 본사에 직원으로 가입합니다.
                        </p>
                        <ul className="option-features">
                            <li>본사 직원 전용</li>
                            <li>업체 코드 필요</li>
                            <li>관리자 승인 필요</li>
                        </ul>
                        <button className="option-button">직원으로 가입하기</button>
                    </div>
                </div>

                <div className="back-link">
                    <button onClick={handleBack} className="back-button">
                        ← 로그인 페이지로 돌아가기
                    </button>
                </div>
            </div>
        </div>
    );
};

export default SignupChoicePage;
