import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { get, post } from '../services/api';
import './UserCreatePage.css';

const UserCreatePage = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [companies, setCompanies] = useState([]);
    const [formData, setFormData] = useState({
        username: '',
        password: '',
        company: '',
        role: 'user',
        status: 'pending'
    });

    console.log('[UserCreatePage] 컴포넌트 렌더링');

    useEffect(() => {
        fetchCompanies();
    }, []);

    const fetchCompanies = async () => {
        console.log('[UserCreatePage] 업체 목록 조회 시작');
        try {
            const response = await get('api/companies/');
            if (response.success) {
                setCompanies(response.data.results || []);
                console.log('[UserCreatePage] 업체 목록 설정 완료:', response.data.results?.length);
            } else {
                console.error('[UserCreatePage] 업체 목록 조회 실패:', response.error);
            }
        } catch (error) {
            console.error('[UserCreatePage] 업체 목록 조회 중 오류:', error);
        }
    };

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('[UserCreatePage] 사용자 등록 시작:', formData);
        
        setLoading(true);
        setError(null);

        try {
            const response = await post('api/companies/users/', formData);
            console.log('[UserCreatePage] 사용자 등록 응답:', response);

            if (response.success) {
                console.log('[UserCreatePage] 사용자 등록 성공');
                alert('사용자가 성공적으로 등록되었습니다.');
                navigate('/users');
            } else {
                setError(response.error || '사용자 등록에 실패했습니다.');
                console.error('[UserCreatePage] 사용자 등록 실패:', response.error);
            }
        } catch (error) {
            setError(error.message || '네트워크 오류가 발생했습니다.');
            console.error('[UserCreatePage] 사용자 등록 중 오류:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        console.log('[UserCreatePage] 취소 버튼 클릭');
        navigate('/users');
    };

    return (
        <div className="user-create-page">
            <div className="page-header">
                <h1>➕ 새 사용자 등록</h1>
            </div>

            <div className="form-container">
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="username">사용자명 *</label>
                        <input
                            type="text"
                            id="username"
                            name="username"
                            value={formData.username}
                            onChange={handleInputChange}
                            required
                            placeholder="사용자명을 입력하세요"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">비밀번호 *</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            value={formData.password}
                            onChange={handleInputChange}
                            required
                            placeholder="비밀번호를 입력하세요"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="company">소속 업체 *</label>
                        <select
                            id="company"
                            name="company"
                            value={formData.company}
                            onChange={handleInputChange}
                            required
                        >
                            <option value="">업체를 선택하세요</option>
                            {companies.map((company) => (
                                <option key={company.id} value={company.id}>
                                    {company.name}
                                </option>
                            ))}
                        </select>
                    </div>

                    <div className="form-group">
                        <label htmlFor="role">역할 *</label>
                        <select
                            id="role"
                            name="role"
                            value={formData.role}
                            onChange={handleInputChange}
                            required
                        >
                            <option value="user">사용자</option>
                            <option value="staff">직원</option>
                            <option value="admin">관리자</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label htmlFor="status">상태 *</label>
                        <select
                            id="status"
                            name="status"
                            value={formData.status}
                            onChange={handleInputChange}
                            required
                        >
                            <option value="pending">대기 중</option>
                            <option value="approved">승인됨</option>
                            <option value="rejected">거부됨</option>
                        </select>
                    </div>

                    {error && (
                        <div className="error-message">
                            {error}
                        </div>
                    )}

                    <div className="form-actions">
                        <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={handleCancel}
                            disabled={loading}
                        >
                            취소
                        </button>
                        <button
                            type="submit"
                            className="btn btn-primary"
                            disabled={loading}
                        >
                            {loading ? '등록 중...' : '사용자 등록'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default UserCreatePage; 