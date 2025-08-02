import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { post } from '../services/api';
import './CompanyCreatePage.css';

const CompanyCreatePage = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [formData, setFormData] = useState({
        code: '',
        name: '',
        type: 'agency',
        status: true,
        visible: true,
        default_courier: ''
    });

    console.log('[CompanyCreatePage] 컴포넌트 렌더링');

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('[CompanyCreatePage] 업체 등록 시작:', formData);
        
        setLoading(true);
        setError(null);

        try {
            const response = await post('companies/', formData);
            console.log('[CompanyCreatePage] 업체 등록 응답:', response);

            if (response.success) {
                console.log('[CompanyCreatePage] 업체 등록 성공');
                alert('업체가 성공적으로 등록되었습니다.');
                navigate('/companies');
            } else {
                setError(response.error || '업체 등록에 실패했습니다.');
                console.error('[CompanyCreatePage] 업체 등록 실패:', response.error);
            }
        } catch (error) {
            setError('네트워크 오류가 발생했습니다.');
            console.error('[CompanyCreatePage] 업체 등록 중 오류:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        console.log('[CompanyCreatePage] 취소 버튼 클릭');
        navigate('/companies');
    };

    return (
        <div className="company-create-page">
            <div className="page-header">
                <h1>➕ 새 업체 등록</h1>
            </div>

            <div className="form-container">
                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="code">업체 코드 *</label>
                        <input
                            type="text"
                            id="code"
                            name="code"
                            value={formData.code}
                            onChange={handleInputChange}
                            required
                            placeholder="예: COMP001"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="name">업체명 *</label>
                        <input
                            type="text"
                            id="name"
                            name="name"
                            value={formData.name}
                            onChange={handleInputChange}
                            required
                            placeholder="업체명을 입력하세요"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="type">업체 유형 *</label>
                        <select
                            id="type"
                            name="type"
                            value={formData.type}
                            onChange={handleInputChange}
                            required
                        >
                            <option value="headquarters">본사</option>
                            <option value="agency">협력사</option>
                            <option value="dealer">대리점</option>
                            <option value="retail">판매점</option>
                        </select>
                    </div>

                    <div className="form-group">
                        <label htmlFor="default_courier">기본 배송업체</label>
                        <input
                            type="text"
                            id="default_courier"
                            name="default_courier"
                            value={formData.default_courier}
                            onChange={handleInputChange}
                            placeholder="기본 배송업체명"
                        />
                    </div>

                    <div className="form-group checkbox-group">
                        <label>
                            <input
                                type="checkbox"
                                name="status"
                                checked={formData.status}
                                onChange={handleInputChange}
                            />
                            활성 상태
                        </label>
                    </div>

                    <div className="form-group checkbox-group">
                        <label>
                            <input
                                type="checkbox"
                                name="visible"
                                checked={formData.visible}
                                onChange={handleInputChange}
                            />
                            공개 상태
                        </label>
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
                            {loading ? '등록 중...' : '업체 등록'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default CompanyCreatePage; 