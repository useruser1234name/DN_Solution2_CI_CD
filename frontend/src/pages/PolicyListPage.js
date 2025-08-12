import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Button, Card, Table, Tag, Space, message, Spin, Alert } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons';
import { get, post } from '../services/api';
import './PolicyListPage.css';

const PolicyListPage = () => {
    const [receivedPolicies, setReceivedPolicies] = useState([]);
    const [assignedPolicies, setAssignedPolicies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [showCreateForm, setShowCreateForm] = useState(false);
    const location = useLocation();
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        form_type: 'individual',
        carrier: 'skt',
        contract_period: '24',
        rebate_agency: 0,
        rebate_retail: 0,
        expose: true,
        premium_market_expose: false
    });
    const [childCompanies, setChildCompanies] = useState([]);
    const [selectedChildCompany, setSelectedChildCompany] = useState('');

    console.log('[PolicyListPage] 컴포넌트 렌더링');

    const fetchPolicies = async () => {
        console.log('[PolicyListPage] 정책 목록 가져오기 시작');
        
        try {
            setLoading(true);
            setError(null);
            
            const response = await get('policies/api/list/');
            console.log('[PolicyListPage] 정책 목록 응답:', response);

            if (response.success) {
                console.log('[PolicyListPage] 정책 목록 성공:', response.data);
                setReceivedPolicies(response.data.received_policies || []);
                setAssignedPolicies(response.data.assigned_policies || []);
            } else {
                console.error('[PolicyListPage] 정책 목록 실패:', response.message);
                setError('정책 목록을 불러오는데 실패했습니다.');
            }
        } catch (error) {
            console.error('[PolicyListPage] 정책 목록 로딩 실패:', error);
            setError('정책 목록을 불러오는 중 오류가 발생했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const fetchChildCompanies = async () => {
        try {
            const response = await get('companies/api/child-companies/');
            if (response.success) {
                setChildCompanies(response.data.data); // 배열로 세팅
            } else {
                console.error('자식 회사 목록 로딩 실패:', response.message);
            }
        } catch (error) {
            console.error('자식 회사 목록 로딩 중 오류:', error);
        }
    };

    useEffect(() => {
        console.log('[PolicyListPage] useEffect 실행 - fetchPolicies 호출');
        fetchPolicies();
        
        // URL이 /policies/create인 경우 폼 자동 표시
        if (location.pathname === '/policies/create') {
            console.log('[PolicyListPage] 정책 생성 페이지로 이동 - 폼 자동 표시');
            setShowCreateForm(true);
        }
        fetchChildCompanies();
    }, [location.pathname]);

    const handleInputChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleChildCompanyChange = (e) => {
        setSelectedChildCompany(e.target.value);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        console.log('[PolicyListPage] 정책 등록 시작:', formData);
        
        const dataToSubmit = {
            ...formData,
            assigned_to: selectedChildCompany
        };
        
        try {
            const response = await post('policies/api/create/', dataToSubmit);
            console.log('[PolicyListPage] 정책 등록 응답:', response);

            if (response.success) {
                console.log('[PolicyListPage] 정책 등록 성공');
                alert('정책이 성공적으로 등록되었습니다.');
                setShowCreateForm(false);
                setFormData({
                    title: '',
                    description: '',
                    form_type: 'individual',
                    carrier: 'skt',
                    contract_period: '24',
                    rebate_agency: 0,
                    rebate_retail: 0,
                    expose: true,
                    premium_market_expose: false
                });
                setSelectedChildCompany('');
                fetchPolicies(); // 목록 새로고침
                
                // URL이 /policies/create인 경우 /policies로 리다이렉트
                if (location.pathname === '/policies/create') {
                    window.history.pushState(null, '', '/policies');
                }
            } else {
                console.error('[PolicyListPage] 정책 등록 실패:', response);
                alert(response.message || '정책 등록에 실패했습니다.');
            }
        } catch (error) {
            console.error('[PolicyListPage] 정책 등록 중 오류:', error);
            alert('네트워크 오류가 발생했습니다.');
        }
    };

    const handleCancel = () => {
        setShowCreateForm(false);
        setFormData({
            title: '',
            description: '',
            form_type: 'individual',
            carrier: 'skt',
            contract_period: '24',
            rebate_agency: 0,
            rebate_retail: 0,
            expose: true,
            premium_market_expose: false
        });
        setSelectedChildCompany('');
        
        // URL이 /policies/create인 경우 /policies로 리다이렉트
        if (location.pathname === '/policies/create') {
            window.history.pushState(null, '', '/policies');
        }
    };

    const handleCreatePolicy = () => {
        navigate('/policies/create');
    };

    if (loading) {
        return (
            <div className="policy-list-page">
                <div className="page-header">
                    <h1>📋 정책 목록</h1>
                    <p>정책 목록을 불러오는 중...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="policy-list-page">
            <div className="page-header">
                <div className="header-content">
                    <h1>📋 정책 관리</h1>
                    <p>생성된 정책들을 확인하고 관리할 수 있습니다.</p>
                </div>
                <div className="header-actions">
                    <Button 
                        type="primary" 
                        icon={<PlusOutlined />}
                        onClick={handleCreatePolicy}
                        size="large"
                    >
                        새 정책 생성
                    </Button>
                </div>
            </div>

            {error && (
                <div className="error-message">
                    {error}
                </div>
            )}

            {showCreateForm && (
                <div className="create-form-overlay">
                    <div className="create-form">
                        <h2>새 정책 등록</h2>
                        <form onSubmit={handleSubmit}>
                            <div className="form-group">
                                <label htmlFor="title">정책명 *</label>
                                <input
                                    type="text"
                                    id="title"
                                    name="title"
                                    value={formData.title}
                                    onChange={handleInputChange}
                                    required
                                    placeholder="정책명을 입력하세요"
                                />
                            </div>

                            <div className="form-group">
                                <label htmlFor="description">설명</label>
                                <textarea
                                    id="description"
                                    name="description"
                                    value={formData.description}
                                    onChange={handleInputChange}
                                    placeholder="정책 설명을 입력하세요"
                                    rows="3"
                                />
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label htmlFor="form_type">신청서 타입</label>
                                    <select
                                        id="form_type"
                                        name="form_type"
                                        value={formData.form_type}
                                        onChange={handleInputChange}
                                    >
                                        <option value="individual">개인</option>
                                        <option value="business">법인</option>
                                    </select>
                                </div>

                                <div className="form-group">
                                    <label htmlFor="carrier">통신사</label>
                                    <select
                                        id="carrier"
                                        name="carrier"
                                        value={formData.carrier}
                                        onChange={handleInputChange}
                                    >
                                        <option value="skt">SKT</option>
                                        <option value="kt">KT</option>
                                        <option value="lg">LG U+</option>
                                    </select>
                                </div>

                                <div className="form-group">
                                    <label htmlFor="contract_period">가입기간</label>
                                    <select
                                        id="contract_period"
                                        name="contract_period"
                                        value={formData.contract_period}
                                        onChange={handleInputChange}
                                    >
                                        <option value="12">12개월</option>
                                        <option value="24">24개월</option>
                                        <option value="36">36개월</option>
                                    </select>
                                </div>
                            </div>

                            <div className="form-row">
                                <div className="form-group">
                                    <label htmlFor="rebate_agency">대리점 리베이트</label>
                                    <input
                                        type="number"
                                        id="rebate_agency"
                                        name="rebate_agency"
                                        value={formData.rebate_agency}
                                        onChange={handleInputChange}
                                        placeholder="0"
                                    />
                                </div>

                                <div className="form-group">
                                    <label htmlFor="rebate_retail">소매점 리베이트</label>
                                    <input
                                        type="number"
                                        id="rebate_retail"
                                        name="rebate_retail"
                                        value={formData.rebate_retail}
                                        onChange={handleInputChange}
                                        placeholder="0"
                                    />
                                </div>
                            </div>

                            <div className="form-group checkbox-group">
                                <label>
                                    <input
                                        type="checkbox"
                                        name="expose"
                                        checked={formData.expose}
                                        onChange={handleInputChange}
                                    />
                                    노출 상태
                                </label>
                            </div>

                            <div className="form-group checkbox-group">
                                <label>
                                    <input
                                        type="checkbox"
                                        name="premium_market_expose"
                                        checked={formData.premium_market_expose}
                                        onChange={handleInputChange}
                                    />
                                    프리미엄 마켓 노출
                                </label>
                            </div>

                            <div className="form-group">
                                <label htmlFor="assigned_to">할당할 자식 회사</label>
                                <select
                                    id="assigned_to"
                                    name="assigned_to"
                                    value={selectedChildCompany}
                                    onChange={handleChildCompanyChange}
                                >
                                    <option value="">선택하세요</option>
                                    {childCompanies.map(company => (
                                        <option key={company.id} value={company.id}>{company.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div className="form-actions">
                                <button
                                    type="button"
                                    className="btn btn-secondary"
                                    onClick={handleCancel}
                                >
                                    취소
                                </button>
                                <button
                                    type="submit"
                                    className="btn btn-primary"
                                >
                                    정책 등록
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <div className="policies-container">
                <section className="policy-section">
                    <h2>⬆️ 상위에서 받은 정책</h2>
                    {receivedPolicies.length > 0 ? (
                        <div className="policies-grid">
                            {receivedPolicies.map((policy) => (
                                <div key={policy.id} className="policy-card">
                                    <div className="policy-header">
                                        <h3>{policy.title}</h3>
                                        <span className={`status ${policy.expose ? 'active' : 'inactive'}`}>
                                            {policy.expose ? '노출' : '비노출'}
                                        </span>
                                        <span className="policy-label received">상위 정책</span>
                                    </div>
                                    <div className="policy-content">
                                        <p className="description">{policy.description}</p>
                                        <div className="policy-details">
                                            <span className="carrier">{policy.carrier}</span>
                                            <span className="contract-period">{policy.contract_period}개월</span>
                                            <span className="form-type">{policy.form_type}</span>
                                        </div>
                                        <div className="policy-rebates">
                                            <span>대리점: {policy.rebate_agency}원</span>
                                            <span>소매점: {policy.rebate_retail}원</span>
                                        </div>
                                    </div>
                                    <div className="policy-actions">
                                        <button className="btn btn-small btn-primary">수정</button>
                                        <button className="btn btn-small btn-danger">삭제</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="no-policies">
                            <p>상위에서 받은 정책이 없습니다.</p>
                        </div>
                    )}
                </section>

                <section className="policy-section">
                    <h2>⬇️ 내가 하위에 할당한 정책</h2>
                    {assignedPolicies.length > 0 ? (
                        <div className="policies-grid">
                            {assignedPolicies.map((policy) => (
                                <div key={policy.id} className="policy-card">
                                    <div className="policy-header">
                                        <h3>{policy.title}</h3>
                                        <span className={`status ${policy.expose ? 'active' : 'inactive'}`}>
                                            {policy.expose ? '노출' : '비노출'}
                                        </span>
                                        <span className="policy-label assigned">내가 할당</span>
                                    </div>
                                    <div className="policy-content">
                                        <p className="description">{policy.description}</p>
                                        <div className="policy-details">
                                            <span className="carrier">{policy.carrier}</span>
                                            <span className="contract-period">{policy.contract_period}개월</span>
                                            <span className="form-type">{policy.form_type}</span>
                                        </div>
                                        <div className="policy-rebates">
                                            <span>대리점: {policy.rebate_agency}원</span>
                                            <span>소매점: {policy.rebate_retail}원</span>
                                        </div>
                                        {policy.assigned_to && (
                                            <div className="policy-assigned-to">
                                                <span>할당된 회사: {policy.assigned_to_name}</span>
                                            </div>
                                        )}
                                    </div>
                                    <div className="policy-actions">
                                        <button className="btn btn-small btn-primary">수정</button>
                                        <button className="btn btn-small btn-danger">삭제</button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="no-policies">
                            <p>내가 하위에 할당한 정책이 없습니다.</p>
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
};

export default PolicyListPage; 