import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { get, del } from '../services/api';
import { getCompanyTypeFromCode } from '../utils/companyUtils';
import './CompanyListPage.css';

const CompanyListPage = () => {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();



    useEffect(() => {
        fetchCompanies();
    }, []);

    const fetchCompanies = async () => {
        setLoading(true);
        setError(null);

        try {
            console.log('[CompanyListPage] 업체 목록 요청 시작...');
            const response = await get('api/companies/companies/');
            console.log('[CompanyListPage] API 응답:', response);
            console.log('[CompanyListPage] 응답 타입:', typeof response);

            let companiesData = [];
            
            // API 응답 구조 처리: {success: true, data: {...}, message: null}
            if (response && typeof response === 'object') {
                // success/data 구조인 경우
                if (response.success && response.data) {
                    console.log('[CompanyListPage] success/data 구조 응답 처리');
                    const actualData = response.data;
                    
                    if (actualData.results && Array.isArray(actualData.results)) {
                        console.log('[CompanyListPage] 페이지네이션 응답 처리:', actualData.results.length, '개 업체');
                        companiesData = actualData.results;
                    } else if (Array.isArray(actualData)) {
                        console.log('[CompanyListPage] 직접 배열 응답 처리:', actualData.length, '개 업체');
                        companiesData = actualData;
                    } else {
                        console.warn('[CompanyListPage] data 내부 구조 확인:', Object.keys(actualData));
                        setError('업체 목록 데이터 구조가 예상과 다릅니다.');
                        return;
                    }
                }
                // 직접 페이지네이션 구조인 경우
                else if (response.results && Array.isArray(response.results)) {
                    console.log('[CompanyListPage] 직접 페이지네이션 응답 처리:', response.results.length, '개 업체');
                    companiesData = response.results;
                } 
                // 직접 배열인 경우
                else if (Array.isArray(response)) {
                    console.log('[CompanyListPage] 직접 배열 응답 처리:', response.length, '개 업체');
                    companiesData = response;
                } else {
                    console.warn('[CompanyListPage] 예상하지 못한 응답 구조:', Object.keys(response));
                    console.warn('[CompanyListPage] 응답 내용:', response);
                    setError('업체 목록 데이터 구조가 예상과 다릅니다.');
                    return;
                }
            } else if (Array.isArray(response)) {
                console.log('[CompanyListPage] 최상위 배열 응답 처리:', response.length, '개 업체');
                companiesData = response;
            } else {
                console.error('[CompanyListPage] 잘못된 응답 타입:', typeof response, response);
                setError('업체 목록 응답 형식이 올바르지 않습니다.');
                return;
            }

            console.log('[CompanyListPage] 원본 업체 데이터:', companiesData);

            // 업체 코드를 기반으로 타입 보완
            const companiesWithType = companiesData.map(company => {
                const enhancedCompany = {
                    ...company,
                    type: company.type || getCompanyTypeFromCode(company.code)
                };
                console.log('[CompanyListPage] 업체 타입 보완:', {
                    id: company.id,
                    name: company.name,
                    originalType: company.type,
                    code: company.code,
                    finalType: enhancedCompany.type
                });
                return enhancedCompany;
            });
            
            console.log('[CompanyListPage] 최종 업체 목록:', companiesWithType.length, '개 업체');
            setCompanies(companiesWithType);
            if (companiesWithType.length === 0) {
                setError('현재 표시할 업체가 없습니다.');
            }
        } catch (error) {
            console.error('[CompanyListPage] 업체 목록 조회 오류:', error);
            setError('네트워크 오류가 발생했습니다.');
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
        navigate('/companies/create');
    };

    const handleCompanyAction = async (action, companyId) => {
        switch (action) {
            case 'view':
                // TODO: 업체 상세 페이지로 이동
                break;
            case 'edit':
                // TODO: 업체 수정 페이지로 이동
                break;
            case 'delete':
                if (!window.confirm('정말로 이 업체를 삭제하시겠습니까?')) {
                    return;
                }
                
                try {
                    const response = await del(`api/companies/${companyId}/`);
                    if (response.success) {
                        alert('업체가 삭제되었습니다.');
                        fetchCompanies(); // 목록 새로고침
                    } else {
                        alert(response.error || '업체 삭제에 실패했습니다.');
                    }
                } catch (error) {
                    alert('업체 삭제 중 오류가 발생했습니다.');
                }
                break;
        }
    };

    // 계층 구조 빌드 함수
    const buildHierarchy = (companies) => {
        const companyMap = new Map();
        const rootCompanies = [];

        // 1단계: 모든 업체를 맵에 저장
        companies.forEach(company => {
            companyMap.set(company.id, {
                ...company,
                children: []
            });
        });

        // 2단계: 계층 구조 구성
        companies.forEach(company => {
            const companyNode = companyMap.get(company.id);
            
            if (company.parent_company) {
                const parent = companyMap.get(company.parent_company);
                if (parent) {
                    parent.children.push(companyNode);
                } else {
                    // 부모를 찾을 수 없으면 루트에 추가
                    rootCompanies.push(companyNode);
                }
            } else {
                rootCompanies.push(companyNode);
            }
        });

        return rootCompanies;
    };

    // 계층 구조 렌더링 함수
    const renderCompanyHierarchy = () => {
        const hierarchy = buildHierarchy(companies);
        
        return (
            <div className="company-hierarchy">
                {hierarchy.map(company => renderCompanyNode(company, 0))}
            </div>
        );
    };

    // 개별 업체 노드 렌더링 함수
    const renderCompanyNode = (company, level) => {
        const indent = level * 20; // 들여쓰기
        const hasChildren = company.children && company.children.length > 0;
        
        return (
            <div key={company.id} className="company-node">
                <div 
                    className={`company-item level-${level}`}
                    style={{ paddingLeft: `${indent}px` }}
                >
                    <div className="company-info">
                        <div className="company-main">
                            {level > 0 && <span className="tree-connector">└─ </span>}
                            <span className="company-name">{company.name}</span>
                            <span className={`company-type ${company.type}`}>
                                {getCompanyTypeDisplay(company.type)}
                            </span>
                            <span className="company-code">{company.code}</span>
                            <span className={`company-status ${company.status ? 'active' : 'inactive'}`}>
                                {getStatusDisplay(company.status)}
                            </span>
                        </div>
                        <div className="company-meta">
                            <span className="company-date">
                                {new Date(company.created_at).toLocaleDateString('ko-KR')}
                            </span>
                            {hasChildren && (
                                <span className="children-count">
                                    {company.type === 'headquarters' && `협력사: ${company.children.length}개`}
                                    {company.type === 'agency' && `판매점: ${company.children.length}개`}
                                </span>
                            )}
                        </div>
                    </div>
                    <div className="company-actions">
                        <button 
                            className="action-btn view"
                            onClick={() => handleCompanyAction('view', company.id)}
                        >
                            보기
                        </button>
                        <button 
                            className="action-btn edit"
                            onClick={() => handleCompanyAction('edit', company.id)}
                        >
                            수정
                        </button>
                        <button 
                            className="action-btn delete"
                            onClick={() => handleCompanyAction('delete', company.id)}
                        >
                            삭제
                        </button>
                    </div>
                </div>
                
                {/* 하위 업체들 렌더링 */}
                {hasChildren && (
                    <div className="company-children">
                        {company.children.map(child => renderCompanyNode(child, level + 1))}
                    </div>
                )}
            </div>
        );
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

            <div className="company-hierarchy-section">
                <h3>업체 계층 구조</h3>
                <p>본사 → 협력사 → 판매점 순서로 조직 구조를 확인할 수 있습니다.</p>
                {renderCompanyHierarchy()}
            </div>
        </div>
    );
};

export default CompanyListPage; 