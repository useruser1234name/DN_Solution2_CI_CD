import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, post, del } from '../services/api';
import PermissionGuard from '../components/PermissionGuard';
import PolicyExposureModal from '../components/PolicyExposureModal';
import RetailRebateModal from '../components/RetailRebateModal';
import { canCreatePolicy } from '../utils/companyUtils';
import './PolicyListPage.css';

const PolicyListPage = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [policies, setPolicies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [exposureModal, setExposureModal] = useState({ isOpen: false, policy: null });
    const [rebateModal, setRebateModal] = useState({ isOpen: false, policy: null });



    const fetchPolicies = async () => {
        
        try {
            setLoading(true);
            setError(null);
            
            const response = await get('api/policies/');


            if (response.success) {
                const data = response.data;
                // 배열인지 확인하고 배열이 아니면 빈 배열로 설정
                let policiesArray = [];
                if (Array.isArray(data)) {
                    policiesArray = data;
                } else if (data && Array.isArray(data.results)) {
                    policiesArray = data.results;
                } else if (data && data.data && Array.isArray(data.data)) {
                    policiesArray = data.data;
                } else {
                    console.warn('[PolicyListPage] 예상하지 못한 데이터 형태:', data);
                    policiesArray = [];
                }
                setPolicies(policiesArray);

            } else {
                console.error('[PolicyListPage] 정책 목록 실패:', response.message);
                setError('정책 목록을 불러오는데 실패했습니다.');
                setPolicies([]); // 실패 시에도 빈 배열 설정
            }
        } catch (error) {
            console.error('[PolicyListPage] 정책 목록 로딩 실패:', error);
            setError('정책 목록을 불러오는 중 오류가 발생했습니다.');
            setPolicies([]); // 에러 시에도 빈 배열 설정
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPolicies();
    }, []);

    const handleCreatePolicy = () => {
        navigate('/policies/create');
    };

    const handleEditPolicy = (policyId) => {
        navigate(`/policies/${policyId}/edit`);
    };

    const handleViewPolicy = (policyId) => {
        navigate(`/policies/${policyId}`);
    };

    const handleFormTemplate = (policyId) => {
        navigate(`/policies/${policyId}/form-template/edit`);
    };

    const handleRebateAllocation = (policyId) => {
        navigate(`/policies/${policyId}/rebate-allocation`);
    };

    const handleDeletePolicy = async (policyId) => {
        if (!window.confirm('정말로 이 정책을 삭제하시겠습니까?')) {
            return;
        }

        try {
            const response = await del(`api/policies/${policyId}/`);
            if (response.success) {
                alert('정책이 삭제되었습니다.');
                fetchPolicies();
            } else {
                alert(response.message || '정책 삭제에 실패했습니다.');
            }
        } catch (error) {
            console.error('[PolicyListPage] 정책 삭제 실패:', error);
            alert('정책 삭제 중 오류가 발생했습니다.');
        }
    };

    const handleExposureSettings = (policy) => {

        setExposureModal({ isOpen: true, policy });
    };

    const handleExposureModalClose = () => {
        setExposureModal({ isOpen: false, policy: null });
    };

    const handleExposureSuccess = () => {

        // 필요시 정책 목록 새로고침
        fetchPolicies();
    };

    const handleRebateView = (policy) => {
        console.log('[PolicyListPage] 리베이트 조회 모달 열기:', policy);
        setRebateModal({ isOpen: true, policy });
    };

    const handleRebateModalClose = () => {
        setRebateModal({ isOpen: false, policy: null });
    };

    const getStatusBadge = (policy) => {
        // 디버그를 위해 값 출력
        console.log('[PolicyListPage] 정책 상태:', { 
            id: policy.id, 
            title: policy.title,
            is_active: policy.is_active, 
            expose: policy.expose,
            type: typeof policy.is_active
        });
        
        if (policy.is_active === false || policy.is_active === 'false') {
            return <span className="badge inactive">비활성</span>;
        }
        if (policy.expose === true || policy.expose === 'true') {
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

    if (loading) {
        return (
            <div className="policy-list-page">
                <div className="loading">정책 목록을 불러오는 중...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="policy-list-page">
                <div className="error-message">{error}</div>
            </div>
        );
    }

    return (
        <div className="policy-list-page">
            <div className="page-header">
                <div className="header-content">
                    <h1>정책 관리</h1>
                    <p>정책을 조회하고 관리할 수 있습니다.</p>
                </div>
                {canCreatePolicy(user) && (
                    <PermissionGuard permission="canManagePolicies">
                        <div className="header-actions">
                            <button 
                                className="btn btn-primary"
                                onClick={handleCreatePolicy}
                            >
                                새 정책 생성
                            </button>
                        </div>
                    </PermissionGuard>
                )}
                

            </div>

            <div className="policies-container">
                {policies.length === 0 ? (
                    <div className="no-data">
                        <p>등록된 정책이 없습니다.</p>
                        {canCreatePolicy(user) && (
                            <PermissionGuard permission="canManagePolicies">
                                <button 
                                    className="btn btn-primary"
                                    onClick={handleCreatePolicy}
                                >
                                    첫 정책 만들기
                                </button>
                            </PermissionGuard>
                        )}
                        

                    </div>
                ) : (
                    <div className="policies-table">
                        <table>
                            <thead>
                                <tr>
                                    <th>정책명</th>
                                    <th>통신사</th>
                                    <th>상태</th>
                                    <th>생성일</th>
                                    <th>작업</th>
                                </tr>
                            </thead>
                            <tbody>
                                {policies.map(policy => (
                                    <tr key={policy.id}>
                                        <td>
                                            <div className="policy-title">
                                                <strong>{policy.title}</strong>
                                                {policy.description && (
                                                    <small>{policy.description}</small>
                                                )}
                                            </div>
                                        </td>
                                        <td>{getCarrierLabel(policy.carrier)}</td>
                                        <td>{getStatusBadge(policy)}</td>
                                        <td>{new Date(policy.created_at).toLocaleDateString()}</td>
                                        <td>
                                            <div className="action-buttons">
                                                {user?.company?.type === 'agency' ? (
                                                    <button 
                                                        className="btn btn-small btn-info"
                                                        onClick={() => handleRebateAllocation(policy.id)}
                                                    >
                                                        리베이트 할당
                                                    </button>
                                                ) : user?.company?.type === 'retail' ? (
                                                    <>
                                                        <button 
                                                            className="btn btn-small btn-secondary"
                                                            onClick={() => handleFormTemplate(policy.id)}
                                                        >
                                                            주문서 양식
                                                        </button>
                                                        <button 
                                                            className="btn btn-small btn-success"
                                                            onClick={() => handleRebateView(policy)}
                                                        >
                                                            리베이트 금액
                                                        </button>
                                                    </>
                                                ) : (
                                                    <button 
                                                        className="btn btn-small btn-secondary"
                                                        onClick={() => handleFormTemplate(policy.id)}
                                                    >
                                                        주문서 양식
                                                    </button>
                                                )}
                                                <PermissionGuard permission="canManagePolicies">
                                                    <button 
                                                        className="btn btn-small btn-info"
                                                        onClick={() => handleExposureSettings(policy)}
                                                        title="협력사 노출 설정"
                                                    >
                                                        노출설정
                                                    </button>
                                                                                                                                                                <button 
                                                        className="btn btn-small btn-primary"
                                                        onClick={() => handleViewPolicy(policy.id)}
                                                        title="정책 상세 보기"
                                                    >
                                                        보기
                                                    </button>
                                                    <button 
                                                        className="btn btn-small btn-danger"
                                                        onClick={() => handleDeletePolicy(policy.id)}
                                                    >
                                                        삭제
                                                    </button>
                                                </PermissionGuard>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* 정책 노출 설정 모달 */}
            <PolicyExposureModal
                isOpen={exposureModal.isOpen}
                policy={exposureModal.policy}
                onClose={handleExposureModalClose}
                onSuccess={handleExposureSuccess}
            />

            {/* 판매점 리베이트 조회 모달 */}
            <RetailRebateModal
                isOpen={rebateModal.isOpen}
                policy={rebateModal.policy}
                onClose={handleRebateModalClose}
            />
        </div>
    );
};

export default PolicyListPage;