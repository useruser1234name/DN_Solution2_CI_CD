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



    // CSRF 토큰 관련 useEffect 제거

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!username || !password) {
            setError('아이디와 비밀번호를 모두 입력해주세요.');
            return;
        }

        setLoading(true);
        setError('');

        try {
            const result = await login(username, password);
            
            if (result.success) {
                navigate('/dashboard');
            } else {
                setError(result.message);
            }
        } catch (error) {
            console.error('[LoginPage] 로그인 중 예외 발생:', error);
            setError('로그인 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleUsernameChange = (e) => {
        setUsername(e.target.value);
    };

    const handlePasswordChange = (e) => {
        setPassword(e.target.value);
    };

    return (
        <div className="login-container">
            <div className="login-card">
                <div className="login-header">
                    <h1>🏢 DN_Solution</h1>
                    <p>통신업계 종합 관리 솔루션</p>
                </div>
                <form className="login-form" onSubmit={handleSubmit}>
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
                            ❌ {error}
                        </div>
                    )}
                    <button 
                        type="submit" 
                        className="login-button"
                        disabled={loading}
                    >
                        {loading ? '🔄 로그인 중...' : '🚀 로그인'}
                    </button>
                </form>
                <div className="login-footer">
                    <div className="signup-link">
                        <p>계정이 없으신가요? <a href="/signup">회원가입하기</a></p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LoginPage; 