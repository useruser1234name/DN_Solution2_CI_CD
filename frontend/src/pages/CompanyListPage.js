import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { get } from '../services/api';
import './CompanyListPage.css';

const CompanyListPage = () => {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();

    console.log('[CompanyListPage] 컴포넌트 렌더링');

    useEffect(() => {
        fetchCompanies();
    }, []);

    const fetchCompanies = async () => {
        console.log('[CompanyListPage] 업체 목록 조회 시작');
        setLoading(true);
        setError(null);

        try {
            const response = await get('companies/');
            console.log('[CompanyListPage] 업체 목록 응답:', response);

            if (response.success) {
                setCompanies(response.data.results || []);
                console.log('[CompanyListPage] 업체 목록 설정 완료:', response.data.results?.length);
            } else {
                setError(response.error || '업체 목록을 불러오는데 실패했습니다.');
                console.error('[CompanyListPage] 업체 목록 조회 실패:', response.error);
            }
        } catch (error) {
            setError('네트워크 오류가 발생했습니다.');
            console.error('[CompanyListPage] 업체 목록 조회 중 오류:', error);
        } finally {
            setLoading(false);
        }
    };

    const getCompanyTypeDisplay = (type) => {
        const typeMap = {
            'headquarters': '본사',
            'agency': '협력사',
            'dealer': '대리점',
            'retail': '판매점'
        };
        return typeMap[type] || type;
    };

    const getStatusDisplay = (status) => {
        return status ? '활성' : '비활성';
    };

    const handleAddCompany = () => {
        console.log('[CompanyListPage] 새 업체 등록 버튼 클릭');
        navigate('/companies/create');
    };

    if (loading) {
        return (
            <div className="company-list-page">
                <div className="page-header">
                    <h1>🏢 업체 목록</h1>
                </div>
                <div className="loading">로딩 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="company-list-page">
                <div className="page-header">
                    <h1>🏢 업체 목록</h1>
                </div>
                <div className="error">{error}</div>
            </div>
        );
    }

    return (
        <div className="company-list-page">
            <div className="page-header">
                <h1>🏢 업체 목록</h1>
                <button className="add-btn" onClick={handleAddCompany}>
                    ➕ 새 업체 등록
                </button>
            </div>

            <div className="company-stats">
                <div className="stat-card">
                    <span className="stat-number">{companies.length}</span>
                    <span className="stat-label">총 업체 수</span>
                </div>
                <div className="stat-card">
                    <span className="stat-number">{companies.filter(c => c.status).length}</span>
                    <span className="stat-label">활성 업체</span>
                </div>
                <div className="stat-card">
                    <span className="stat-number">{companies.filter(c => !c.status).length}</span>
                    <span className="stat-label">비활성 업체</span>
                </div>
            </div>

            <div className="company-table">
                <table>
                    <thead>
                        <tr>
                            <th>코드</th>
                            <th>업체명</th>
                            <th>유형</th>
                            <th>상태</th>
                            <th>상위 업체</th>
                            <th>자식 업체</th>
                            <th>생성일</th>
                            <th>작업</th>
                        </tr>
                    </thead>
                    <tbody>
                        {companies.map((company) => (
                            <tr key={company.id}>
                                <td>{company.code}</td>
                                <td>{company.name}</td>
                                <td>{getCompanyTypeDisplay(company.type)}</td>
                                <td>
                                    <span className={`status-badge ${company.status ? 'active' : 'inactive'}`}>
                                        {getStatusDisplay(company.status)}
                                    </span>
                                </td>
                                <td>{company.parent_company_name || '-'}</td>
                                <td>{company.child_companies && company.child_companies.length > 0 ? company.child_companies.join(', ') : '-'}</td>
                                <td>{new Date(company.created_at).toLocaleDateString()}</td>
                                <td>
                                    <button className="action-btn edit">수정</button>
                                    <button className="action-btn delete">삭제</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default CompanyListPage; 