import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, del, put } from '../services/api';
import PermissionGuard from '../components/PermissionGuard';
import OrderFormBuilderModal from '../components/OrderFormBuilderModal';
import MatrixRebateEditor from '../components/MatrixRebateEditor';
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
    const [viewMode, setViewMode] = useState('view'); // 'view' 또는 'edit'
    const [saving, setSaving] = useState(false);
    const [errors, setErrors] = useState({});
    const [rebateMatrix, setRebateMatrix] = useState([]);
    const [formData, setFormData] = useState({
        title: '',
        description: '',
        carrier: 'skt',
        expose: true,
        is_active: true,
        activation_notes: '',
        common_notes: '',
        grades: []
    });

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
                
                // 폼 데이터 설정
                setFormData({
                    title: response.data.title || '',
                    description: response.data.description || '',
                    carrier: response.data.carrier || 'skt',
                    expose: response.data.expose !== false,
                    is_active: response.data.is_active !== false,
                    activation_notes: response.data.activation_notes || '',
                    common_notes: response.data.common_notes || '',
                    grades: response.data.grades || []
                });
                
                // 리베이트 매트릭스 로드
                await fetchRebateMatrix();
                
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

    // 리베이트 매트릭스 가져오기
    const fetchRebateMatrix = async () => {
        try {
            console.log('[PolicyDetailPage] 리베이트 매트릭스 가져오기 시작:', id);
            const matrixResponse = await get(`api/policies/${id}/rebate-matrix/`);
            console.log('[PolicyDetailPage] 리베이트 매트릭스 응답:', matrixResponse);
            
            if (matrixResponse.success && matrixResponse.data) {
                // 이중 래핑 확인 및 처리
                let matrixData = matrixResponse.data;
                
                if (matrixData.success && matrixData.data) {
                    console.log('[PolicyDetailPage] 이중 래핑된 매트릭스 응답 감지');
                    matrixData = matrixData.data;
                }
                
                if (matrixData.matrix && Array.isArray(matrixData.matrix) && matrixData.matrix.length > 0) {
                    setRebateMatrix(matrixData.matrix);
                } else {
                    setRebateMatrix(getDefaultMatrix());
                }
            } else {
                setRebateMatrix(getDefaultMatrix());
            }
        } catch (error) {
            console.error('[PolicyDetailPage] 리베이트 매트릭스 로딩 실패:', error);
            setRebateMatrix(getDefaultMatrix());
        }
    };
    
    // 기본 매트릭스 생성
    const getDefaultMatrix = () => {
        // 기본 9x3 매트릭스 생성
        const planRanges = ['11K', '22K', '33K', '44K', '55K', '66K', '77K', '88K', '99K'];
        const contractPeriods = [12, 24, 36];
        const matrix = [];

        planRanges.forEach((planRange, rowIndex) => {
            contractPeriods.forEach((period, colIndex) => {
                matrix.push({
                    id: `${rowIndex}-${colIndex}`,
                    plan_range: planRange,
                    contract_period: period,
                    rebate_amount: 0,
                    row: rowIndex,
                    col: colIndex
                });
            });
        });

        return matrix;
    };
    
    // 폼 필드 변경 핸들러
    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
        
        if (errors[name]) {
            setErrors(prev => ({
                ...prev,
                [name]: ''
            }));
        }
    };
    
    // 그레이드 추가 핸들러
    const handleAddGrade = () => {
        setFormData(prev => ({
            ...prev,
            grades: [...prev.grades, { count: '', amount: '' }]
        }));
    };
    
    // 그레이드 변경 핸들러
    const handleGradeChange = (index, field, value) => {
        const updatedGrades = [...formData.grades];
        updatedGrades[index][field] = value;
        
        setFormData(prev => ({
            ...prev,
            grades: updatedGrades
        }));
    };
    
    // 그레이드 삭제 핸들러
    const handleRemoveGrade = (index) => {
        const updatedGrades = formData.grades.filter((_, i) => i !== index);
        
        setFormData(prev => ({
            ...prev,
            grades: updatedGrades
        }));
    };
    
    // 폼 유효성 검사
    const validateForm = () => {
        const newErrors = {};

        if (!formData.title) {
            newErrors.title = '정책명을 입력해주세요.';
        }

        if (!formData.carrier) {
            newErrors.carrier = '통신사를 선택해주세요.';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };
    
    // 폼 제출 핸들러
    const handleSubmit = async (e) => {
        if (e) e.preventDefault();
        console.log('[PolicyDetailPage] 정책 저장 시작');

        if (!validateForm()) {
            console.log('[PolicyDetailPage] 유효성 검사 실패');
            return;
        }

        setSaving(true);
        setErrors({});

        try {
            // 정책 수정
            const policyResponse = await put(`api/policies/${id}/`, formData);
            console.log('[PolicyDetailPage] 정책 수정 응답:', policyResponse);

            if (policyResponse.success) {
                // 리베이트 매트릭스 저장
                if (rebateMatrix.length > 0) {
                    try {
                        const matrixResponse = await put(`api/policies/${id}/rebate-matrix/`, {
                            matrix: rebateMatrix
                        });
                        console.log('[PolicyDetailPage] 리베이트 매트릭스 수정 응답:', matrixResponse);
                    } catch (matrixError) {
                        console.warn('[PolicyDetailPage] 리베이트 매트릭스 저장 실패:', matrixError);
                    }
                }
                
                alert('정책이 성공적으로 수정되었습니다.');
                setViewMode('view'); // 저장 후 보기 모드로 전환
                fetchPolicy(); // 정책 정보 새로고침
            } else {
                setErrors({ general: policyResponse.error || '정책 수정에 실패했습니다.' });
            }
        } catch (error) {
            console.error('[PolicyDetailPage] 정책 수정 실패:', error);
            setErrors({ general: '정책 수정 중 오류가 발생했습니다.' });
        } finally {
            setSaving(false);
        }
    };
    
    const handleEdit = () => {
        console.log('[PolicyDetailPage] 편집 모드 전환');
        setViewMode('edit');
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
        if (policy.is_active) {
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

    const carriers = [
        { value: 'skt', label: 'SKT' },
        { value: 'kt', label: 'KT' },
        { value: 'lg', label: 'LG U+' }
    ];
    
    return (
        <div className="policy-detail-page">
            <div className="page-header">
                <div className="header-content">
                    <div className="header-left">
                        <button className="back-btn" onClick={handleBack}>
                            ← 목록으로
                        </button>
                        <div className="header-info">
                            <h1>
                                {viewMode === 'view' ? '정책 상세' : '정책 편집'}
                            </h1>
                            <p>
                                {policy.title} 정책의 {viewMode === 'view' ? '상세 정보입니다' : '정보를 편집합니다'}.
                            </p>
                        </div>
                    </div>
                    <PermissionGuard permission="canManagePolicies">
                        <div className="header-actions">
                            {viewMode === 'view' ? (
                                <>
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
                                </>
                            ) : (
                                <>
                                    <button 
                                        className="btn btn-secondary"
                                        onClick={() => setViewMode('view')}
                                    >
                                        취소
                                    </button>
                                    <button 
                                        className="btn btn-primary"
                                        onClick={handleSubmit}
                                        disabled={saving}
                                    >
                                        {saving ? '저장 중...' : '저장'}
                                    </button>
                                </>
                            )}
                        </div>
                    </PermissionGuard>
                </div>
            </div>

            <form className="policy-content" onSubmit={handleSubmit}>
                <div className="policy-section">
                    <h3>기본 정보</h3>
                    {viewMode === 'view' ? (
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
                            <div className="header-meta">
                                {getStatusBadge(policy)}
                                <span className="carrier-badge">{getCarrierLabel(policy.carrier)}</span>
                            </div>
                        </div>
                    ) : (
                        <div className="form-section">
                            <div className="form-group">
                                <label htmlFor="title">정책명 *</label>
                                <input
                                    type="text"
                                    id="title"
                                    name="title"
                                    value={formData.title}
                                    onChange={handleChange}
                                    disabled={saving}
                                    placeholder="정책명을 입력하세요"
                                />
                                {errors.title && <span className="error">{errors.title}</span>}
                            </div>

                            <div className="form-group">
                                <label htmlFor="description">설명</label>
                                <textarea
                                    id="description"
                                    name="description"
                                    value={formData.description}
                                    onChange={handleChange}
                                    disabled={saving}
                                    placeholder="정책 설명을 입력하세요"
                                    rows="3"
                                />
                            </div>

                            <div className="form-group">
                                <label htmlFor="carrier">통신사 *</label>
                                <select
                                    id="carrier"
                                    name="carrier"
                                    value={formData.carrier}
                                    onChange={handleChange}
                                    disabled={saving}
                                >
                                    {carriers.map(carrier => (
                                        <option key={carrier.value} value={carrier.value}>
                                            {carrier.label}
                                        </option>
                                    ))}
                                </select>
                                {errors.carrier && <span className="error">{errors.carrier}</span>}
                            </div>

                            <div className="form-row">
                                <div className="form-group checkbox-group">
                                    <label>
                                        <input
                                            type="checkbox"
                                            name="is_active"
                                            checked={formData.is_active}
                                            onChange={handleChange}
                                            disabled={saving}
                                        />
                                        정책 활성화
                                    </label>
                                    <span className="field-hint">체크하면 정책이 활성화됩니다.</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {viewMode === 'view' ? (
                    <div className="policy-section">
                        <h3>수수료 정보</h3>
                        <div className="info-grid">
                            <div className="info-item">
                                <label>협력사 수수료</label>
                                <span>{policy.rebate_agency ? `${Number(policy.rebate_agency).toLocaleString()}원` : '-'}</span>
                            </div>
                            <div className="info-item">
                                <label>판매점 수수료</label>
                                <span>{policy.rebate_retail ? `${Number(policy.rebate_retail).toLocaleString()}원` : '-'}</span>
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="form-section">
                        <h3>수수료 매트릭스</h3>
                        {errors.rebateMatrix && (
                            <div className="error-message">{errors.rebateMatrix}</div>
                        )}
                        <MatrixRebateEditor
                            matrix={rebateMatrix}
                            onChange={setRebateMatrix}
                            disabled={saving}
                            carrier={formData.carrier || 'KT'}
                        />
                    </div>
                )}
                
                {/* 그레이드 정보 */}
                <div className="policy-section">
                    <h3>그레이드 정보</h3>
                    {viewMode === 'view' ? (
                        policy.grades && policy.grades.length > 0 ? (
                            <div className="grades-container">
                                {policy.grades.map((grade, index) => (
                                    <div key={index} className="grade-item">
                                        <span className="grade-count">{grade.count}건 이상</span>
                                        <span className="grade-amount">{Number(grade.amount).toLocaleString()}원</span>
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="no-grades-message">
                                그레이드가 없습니다.
                            </div>
                        )
                    ) : (
                        <div className="grade-settings-container">
                            <div className="form-header">
                                <button 
                                    type="button" 
                                    className="btn btn-sm btn-primary" 
                                    onClick={() => handleAddGrade()}
                                    disabled={saving}
                                >
                                    그레이드 추가 +
                                </button>
                            </div>
                            
                            {formData.grades && formData.grades.length > 0 ? (
                                formData.grades.map((grade, index) => (
                                    <div key={index} className="grade-row">
                                        <div className="grade-input-group">
                                            <input
                                                type="number"
                                                value={grade.count}
                                                onChange={(e) => handleGradeChange(index, 'count', e.target.value)}
                                                disabled={saving}
                                                min="1"
                                                placeholder="건수"
                                            />
                                            <span className="grade-text">이상</span>
                                            <input
                                                type="number"
                                                value={grade.amount}
                                                onChange={(e) => handleGradeChange(index, 'amount', e.target.value)}
                                                disabled={saving}
                                                min="1000"
                                                step="1000"
                                                placeholder="수수료"
                                            />
                                            <button
                                                type="button"
                                                className="btn btn-sm btn-danger"
                                                onClick={() => handleRemoveGrade(index)}
                                                disabled={saving}
                                                title="그레이드 삭제"
                                            >
                                                삭제
                                            </button>
                                        </div>
                                    </div>
                                ))
                            ) : (
                                <div className="no-grades-message">
                                    그레이드가 없습니다. 그레이드를 추가하세요.
                                </div>
                            )}
                        </div>
                    )}
                </div>
                
                {/* 유의사항 정보 */}
                <div className="policy-section">
                    <h3>유의사항</h3>
                    {viewMode === 'view' ? (
                        <>
                            {policy.activation_notes && (
                                <div className="notes-item">
                                    <label>개통시 유의사항</label>
                                    <div className="notes-content">{policy.activation_notes}</div>
                                </div>
                            )}
                            {policy.common_notes && (
                                <div className="notes-item">
                                    <label>공통 유의사항</label>
                                    <div className="notes-content">{policy.common_notes}</div>
                                </div>
                            )}
                        </>
                    ) : (
                        <>
                            <div className="form-group">
                                <label htmlFor="activation_notes">개통시 유의사항</label>
                                <textarea
                                    id="activation_notes"
                                    name="activation_notes"
                                    value={formData.activation_notes}
                                    onChange={handleChange}
                                    disabled={saving}
                                    placeholder="개통시 유의사항을 입력하세요"
                                    rows="4"
                                />
                            </div>
                            
                            <div className="form-group">
                                <label htmlFor="common_notes">공통 유의사항</label>
                                <textarea
                                    id="common_notes"
                                    name="common_notes"
                                    value={formData.common_notes}
                                    onChange={handleChange}
                                    disabled={saving}
                                    placeholder="공통 유의사항을 입력하세요"
                                    rows="4"
                                />
                            </div>
                        </>
                    )}
                </div>

                {viewMode === 'view' && (
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
                )}

                {/* 노출된 업체 목록 (본사만 표시) */}
                {viewMode === 'view' && user?.companyType === 'headquarters' && (
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

                {viewMode === 'view' && policy.html_content && (
                    <div className="policy-section">
                        <h3>정책 상세 내용</h3>
                        <div 
                            className="policy-html-content"
                            dangerouslySetInnerHTML={{ __html: policy.html_content }}
                        />
                    </div>
                )}
                
                {errors.general && (
                    <div className="error-message">
                        {errors.general}
                    </div>
                )}
            </form>

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
