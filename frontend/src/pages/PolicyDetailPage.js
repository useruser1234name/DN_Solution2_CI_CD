import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, del } from '../services/api';
import PermissionGuard from '../components/PermissionGuard';
import OrderFormBuilderModal from '../components/OrderFormBuilderModal';
import './PolicyDetailPage.css';

const PolicyDetailPage = () => {
    const { id } = useParams();
    const { user } = useAuth();
    const navigate = useNavigate();
    const [policy, setPolicy] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [orderFormModal, setOrderFormModal] = useState({ isOpen: false });
    const [exposedCompanies, setExposedCompanies] = useState([]);

    console.log('[PolicyDetailPage] 컴포넌트 렌더링', { id, user: user?.username });

    const fetchPolicy = async () => {
        console.log('[PolicyDetailPage] 정책 상세 정보 가져오기 시작:', id);
        
        try {
            setLoading(true);
            setError(null);
            
            const response = await get(`api/policies/${id}/`);
            console.log('[PolicyDetailPage] 정책 상세 응답:', response);

            if (response.success) {
                setPolicy(response.data);
                
                // 본사 사용자인 경우 노출된 업체 목록도 가져오기
                if (user?.companyType === 'headquarters') {
                    await fetchExposedCompanies();
                }
            } else {
                console.error('[PolicyDetailPage] 정책 상세 실패:', response.message);
                setError('정책 정보를 불러오는데 실패했습니다.');
            }
        } catch (error) {
            console.error('[PolicyDetailPage] 정책 상세 로딩 실패:', error);
            setError('정책 정보를 불러오는 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const fetchExposedCompanies = async () => {
        try {
            console.log('[PolicyDetailPage] 노출된 업체 목록 가져오기 시작:', id);
            const response = await get(`api/policies/${id}/exposures/`);
            console.log('[PolicyDetailPage] 노출된 업체 응답:', response);

            if (response.success && response.data) {
                // api.js에서 이중 래핑된 응답 처리
                const actualData = response.data.success ? response.data.data : response.data;
                const exposures = actualData.exposures || [];
                
                console.log('[PolicyDetailPage] 노출 데이터 파싱:', {
                    rawResponse: response,
                    actualData: actualData,
                    exposures: exposures,
                    exposuresLength: exposures.length
                });
                
                // agency 정보만 추출하여 설정
                const agencies = exposures.map(exposure => ({
                    ...exposure.agency,
                    exposed_at: exposure.exposed_at
                }));
                
                console.log('[PolicyDetailPage] 파싱된 협력업체 목록:', agencies);
                setExposedCompanies(agencies);
            } else {
                console.log('[PolicyDetailPage] 노출 데이터 파싱 실패:', response);
            }
        } catch (error) {
            console.error('[PolicyDetailPage] 노출된 업체 목록 로딩 실패:', error);
        }
    };

    useEffect(() => {
        if (id) {
            fetchPolicy();
        }
    }, [id]);

    const handleEdit = () => {
        navigate(`/policies/${id}/edit`);
    };

    const handleDelete = async () => {
        if (!window.confirm('정말로 이 정책을 삭제하시겠습니까?')) {
            return;
        }

        try {
            const response = await del(`api/policies/${id}/`);
            if (response.success) {
                alert('정책이 삭제되었습니다.');
                navigate('/policies');
            } else {
                alert(response.message || '정책 삭제에 실패했습니다.');
            }
        } catch (error) {
            console.error('[PolicyDetailPage] 정책 삭제 실패:', error);
            alert('정책 삭제 중 오류가 발생했습니다.');
        }
    };

    const handleBack = () => {
        navigate('/policies');
    };

    const handleOrderFormBuilder = () => {
        console.log('[PolicyDetailPage] 주문서 양식 편집 열기');
        setOrderFormModal({ isOpen: true });
    };

    const handleOrderFormModalClose = () => {
        setOrderFormModal({ isOpen: false });
    };

    const handleOrderFormSuccess = () => {
        console.log('[PolicyDetailPage] 주문서 양식 저장 완료');
        // 필요시 정책 정보 새로고침
        fetchPolicy();
    };

    const getStatusBadge = (policy) => {
        if (!policy.is_active) {
            return <span className="badge inactive">비활성</span>;
        }
        if (policy.expose) {
            return <span className="badge active">활성</span>;
        }
        return <span className="badge hidden">숨김</span>;
    };

    const getCarrierLabel = (carrier) => {
        const carriers = {
            'SKT': 'SKT',
            'KT': 'KT', 
            'LG': 'LG U+',
            'skt': 'SKT',
            'kt': 'KT',
            'lg': 'LG U+'
        };
        return carriers[carrier] || carrier;
    };

    const formatDate = (dateString) => {
        if (!dateString) return 'N/A';
        
        try {
            const date = new Date(dateString);
            if (isNaN(date.getTime())) return 'N/A';
            
            return date.toLocaleDateString('ko-KR', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            console.error('[PolicyDetailPage] 날짜 포맷팅 오류:', error);
            return 'N/A';
        }
    };

    if (loading) {
        return (
            <div className="policy-detail-page">
                <div className="loading">정책 정보를 불러오는 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="policy-detail-page">
                <div className="error-message">{error}</div>
                <button className="btn btn-secondary" onClick={handleBack}>
                    목록으로 돌아가기
                </button>
            </div>
        );
    }

    if (!policy) {
        return (
            <div className="policy-detail-page">
                <div className="error-message">정책을 찾을 수 없습니다.</div>
                <button className="btn btn-secondary" onClick={handleBack}>
                    목록으로 돌아가기
                </button>
            </div>
        );
    }

    return (
        <div className="policy-detail-page">
            <div className="page-header">
                <div className="header-content">
                    <button className="back-btn" onClick={handleBack}>
                        ← 목록으로
                    </button>
                    <div className="header-info">
                        <h1>{policy.title}</h1>
                        <div className="header-meta">
                            {getStatusBadge(policy)}
                            <span className="carrier-badge">{getCarrierLabel(policy.carrier)}</span>
                        </div>
                    </div>
                </div>
                <PermissionGuard permission="canManagePolicies">
                    <div className="header-actions">
                        <button 
                            className="btn btn-info"
                            onClick={handleOrderFormBuilder}
                            title="주문서 양식 편집"
                        >
                            주문서양식
                        </button>
                        <button 
                            className="btn btn-primary"
                            onClick={handleEdit}
                        >
                            수정
                        </button>
                        <button 
                            className="btn btn-danger"
                            onClick={handleDelete}
                        >
                            삭제
                        </button>
                    </div>
                </PermissionGuard>
            </div>

            <div className="policy-content">
                <div className="policy-section">
                    <h3>기본 정보</h3>
                    <div className="info-grid">
                        <div className="info-item">
                            <label>정책명</label>
                            <span>{policy.title}</span>
                        </div>
                        <div className="info-item">
                            <label>설명</label>
                            <span>{policy.description || '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>통신사</label>
                            <span>{getCarrierLabel(policy.carrier)}</span>
                        </div>
                        <div className="info-item">
                            <label>계약기간</label>
                            <span>{policy.contract_period}개월</span>
                        </div>
                        <div className="info-item">
                            <label>노출 상태</label>
                            <span>{policy.expose ? '노출' : '비노출'}</span>
                        </div>
                        <div className="info-item">
                            <label>활성 상태</label>
                            <span>{policy.is_active ? '활성' : '비활성'}</span>
                        </div>
                    </div>
                </div>

                <div className="policy-section">
                    <h3>리베이트 정보</h3>
                    <div className="info-grid">
                        <div className="info-item">
                            <label>협력사 리베이트</label>
                            <span>{policy.rebate_agency ? `${Number(policy.rebate_agency).toLocaleString()}원` : '-'}</span>
                        </div>
                        <div className="info-item">
                            <label>판매점 리베이트</label>
                            <span>{policy.rebate_retail ? `${Number(policy.rebate_retail).toLocaleString()}원` : '-'}</span>
                        </div>
                    </div>
                </div>

                <div className="policy-section">
                    <h3>생성 정보</h3>
                    <div className="info-grid">
                        <div className="info-item">
                            <label>생성일</label>
                            <span>{formatDate(policy.created_at)}</span>
                        </div>
                        <div className="info-item">
                            <label>수정일</label>
                            <span>{formatDate(policy.updated_at)}</span>
                        </div>
                        <div className="info-item">
                            <label>생성자</label>
                            <span>{policy.created_by_username || '-'}</span>
                        </div>
                        {/* 배정 업체 수는 본사만 표시 */}
                        {user?.companyType === 'headquarters' && (
                            <div className="info-item">
                                <label>배정 업체 수</label>
                                <span>{policy.assignment_count || 0}개</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* 노출된 업체 목록 (본사만 표시) */}
                {user?.companyType === 'headquarters' && (
                    <div className="policy-section">
                        <h3>노출된 협력업체</h3>
                        {exposedCompanies.length > 0 ? (
                            <div className="exposed-companies">
                                {exposedCompanies.map((company, index) => (
                                    <div key={index} className="exposed-company-item">
                                        <div className="company-info">
                                            <span className="company-name">{company.name}</span>
                                            <span className="company-code">({company.code})</span>
                                        </div>
                                        <div className="exposure-date">
                                            노출일: {formatDate(company.exposed_at)}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="no-exposed-companies">노출된 협력업체가 없습니다.</p>
                        )}
                    </div>
                )}

                {policy.html_content && (
                    <div className="policy-section">
                        <h3>정책 상세 내용</h3>
                        <div 
                            className="policy-html-content"
                            dangerouslySetInnerHTML={{ __html: policy.html_content }}
                        />
                    </div>
                )}
            </div>

            {/* 주문서 양식 편집 모달 */}
            <OrderFormBuilderModal
                isOpen={orderFormModal.isOpen}
                policy={policy}
                onClose={handleOrderFormModalClose}
                onSuccess={handleOrderFormSuccess}
            />
        </div>
    );
};

export default PolicyDetailPage;
