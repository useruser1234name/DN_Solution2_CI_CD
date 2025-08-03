import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import './LoginPage.css';

const LoginPage = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const { login } = useAuth();
    const navigate = useNavigate();

    console.log('[LoginPage] 컴포넌트 렌더링');

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('[LoginPage] 로그인 폼 제출:', { username, password: '***' });
        
        if (!username || !password) {
            console.log('[LoginPage] 입력값 검증 실패: 빈 필드');
            setError('아이디와 비밀번호를 모두 입력해주세요.');
            return;
        }

        setLoading(true);
        setError('');

        try {
            console.log('[LoginPage] 로그인 함수 호출');
            const result = await login(username, password);
            
            if (result.success) {
                console.log('[LoginPage] 로그인 성공, 대시보드로 이동');
                navigate('/dashboard');
            } else {
                console.log('[LoginPage] 로그인 실패:', result.message);
                setError(result.message);
            }
        } catch (error) {
            console.error('[LoginPage] 로그인 중 예외 발생:', error);
            setError('로그인 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
            console.log('[LoginPage] 로그인 처리 완료');
        }
    };

    const handleUsernameChange = (e) => {
        const value = e.target.value;
        console.log('[LoginPage] 사용자명 입력:', value);
        setUsername(value);
    };

    const handlePasswordChange = (e) => {
        const value = e.target.value;
        console.log('[LoginPage] 비밀번호 입력:', value.length + '자');
        setPassword(value);
    };

    return (
        <div className="login-container">
            <div className="login-box">
                <h1>HB Admin</h1>
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="username">아이디</label>
                        <input
                            type="text"
                            id="username"
                            value={username}
                            onChange={handleUsernameChange}
                            disabled={loading}
                            placeholder="아이디를 입력하세요"
                        />
                    </div>
                    <div className="form-group">
                        <label htmlFor="password">비밀번호</label>
                        <input
                            type="password"
                            id="password"
                            value={password}
                            onChange={handlePasswordChange}
                            disabled={loading}
                            placeholder="비밀번호를 입력하세요"
                        />
                    </div>
                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}
                    <button type="submit" disabled={loading}>
                        {loading ? '로그인 중...' : '로그인'}
                    </button>
                </form>
                <div className="login-info">
                    <p>테스트 계정: admin / admin1234</p>
                </div>
            </div>
        </div>
    );
};

export default LoginPage; 