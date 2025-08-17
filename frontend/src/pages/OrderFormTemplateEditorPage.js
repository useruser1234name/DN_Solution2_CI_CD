import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get, post, put } from '../services/api';
import './OrderFormTemplateEditorPage.css';

const OrderFormTemplateEditorPage = () => {
    const { id } = useParams(); // policy ID
    const { user } = useAuth();
    const navigate = useNavigate();
    
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [policy, setPolicy] = useState(null);
    const [template, setTemplate] = useState({
        title: '',
        description: '',
        fields: []
    });
    const [viewMode, setViewMode] = useState('view'); // 'view', 'edit'

    // 사용 가능한 필드 타입들
    const FIELD_TYPES = [
        { value: 'text', label: '텍스트' },
        { value: 'number', label: '숫자' },
        { value: 'email', label: '이메일' },
        { value: 'phone', label: '전화번호' },
        { value: 'date', label: '날짜' },
        { value: 'select', label: '드롭다운' },
        { value: 'textarea', label: '긴 텍스트' },
        { value: 'customer_name', label: '고객명' },
        { value: 'birth_date', label: '생년월일' },
        { value: 'join_type', label: '가입유형' },
        { value: 'device_model', label: '모델명' },
        { value: 'device_color', label: '색상' },
        { value: 'carrier_plan', label: '요금제' },
        { value: 'sim_type', label: '유심타입' },
        { value: 'payment_method', label: '결제방법' },
        { value: 'installment_months', label: '할부개월수' },
        { value: 'insurance', label: '보험' }
    ];

    useEffect(() => {
        fetchPolicyAndTemplate();
    }, [id]);

    const fetchPolicyAndTemplate = async () => {
        try {
            setLoading(true);
            
            // 정책 정보 가져오기
            const policyResponse = await get(`api/policies/${id}/`);
            if (policyResponse.success) {
                setPolicy(policyResponse.data);
            }

            // 기존 템플릿 가져오기
            try {
                console.log('[OrderFormTemplateEditor] 템플릿 조회 시작:', `api/policies/${id}/form-template/`);
                const templateResponse = await get(`api/policies/${id}/form-template/`);
                console.log('[OrderFormTemplateEditor] 템플릿 응답:', templateResponse);
                console.log('[OrderFormTemplateEditor] 응답 타입:', typeof templateResponse);
                console.log('[OrderFormTemplateEditor] 응답 키들:', Object.keys(templateResponse || {}));
                
                if (templateResponse && templateResponse.success && templateResponse.data) {
                    console.log('[OrderFormTemplateEditor] 기존 템플릿 로드:', templateResponse.data);
                    
                    // API 서비스에서 한 번 더 래핑된 응답 처리
                    let templateData = templateResponse.data;
                    
                    // 이중 래핑 확인 및 처리
                    if (templateData.success && templateData.data) {
                        console.log('[OrderFormTemplateEditor] 이중 래핑된 응답 감지, 내부 데이터 사용');
                        templateData = templateData.data;
                    }
                    console.log('[OrderFormTemplateEditor] 템플릿 데이터:', templateData);
                    console.log('[OrderFormTemplateEditor] 템플릿 데이터 타입:', typeof templateData);
                    console.log('[OrderFormTemplateEditor] 템플릿 데이터 키들:', Object.keys(templateData || {}));
                    
                    const fields = templateData.fields || [];
                    console.log('[OrderFormTemplateEditor] 원본 필드 배열:', fields);
                    console.log('[OrderFormTemplateEditor] 필드 배열 타입:', typeof fields);
                    console.log('[OrderFormTemplateEditor] 필드 배열 길이:', fields.length);
                    
                    // 필드에 고유 ID 추가 (없는 경우)
                    const processedFields = fields.map((field, index) => ({
                        ...field,
                        id: field.id || `field_${index}_${Date.now()}`,
                        order: field.order || index + 1
                    }));
                    
                    console.log('[OrderFormTemplateEditor] 처리된 필드들:', processedFields);
                    console.log('[OrderFormTemplateEditor] 필드 개수:', processedFields.length);
                    
                    const newTemplate = {
                        title: templateData.title || `${policyResponse.data?.title || '정책'} 주문서`,
                        description: templateData.description || '주문서 양식입니다.',
                        fields: processedFields
                    };
                    
                    console.log('[OrderFormTemplateEditor] 설정할 템플릿:', newTemplate);
                    setTemplate(newTemplate);
                } else {
                    console.log('[OrderFormTemplateEditor] 기존 템플릿 없음, 기본 템플릿 사용');
                    console.log('[OrderFormTemplateEditor] 응답 상세:', {
                        success: templateResponse?.success,
                        data: templateResponse?.data,
                        message: templateResponse?.message
                    });
                    
                    // 이중 래핑된 응답에서 실패 케이스도 확인
                    if (templateResponse?.data?.success === false) {
                        console.log('[OrderFormTemplateEditor] 이중 래핑된 실패 응답:', templateResponse.data);
                    }
                    // 기본 템플릿 설정
                    setTemplate({
                        title: `${policyResponse.data?.title || '정책'} 주문서`,
                        description: '주문서 양식입니다.',
                        fields: getDefaultFields()
                    });
                }
            } catch (templateError) {
                console.warn('[OrderFormTemplateEditor] 템플릿 로딩 실패, 기본 템플릿 사용:', templateError);
                setTemplate({
                    title: `${policyResponse.data?.title || '정책'} 주문서`,
                    description: '주문서 양식입니다.',
                    fields: getDefaultFields()
                });
            }
        } catch (error) {
            console.error('데이터 로딩 실패:', error);
        } finally {
            setLoading(false);
        }
    };

    const getDefaultFields = () => [
        { id: '1', field_name: 'customer_name', field_label: '고객명', field_type: 'customer_name', is_required: true, order: 1 },
        { id: '2', field_name: 'birth_date', field_label: '생년월일', field_type: 'birth_date', is_required: true, order: 2 },
        { id: '3', field_name: 'phone_number', field_label: '개통번호', field_type: 'phone', is_required: true, order: 3 },
        { id: '4', field_name: 'device_model', field_label: '모델명', field_type: 'device_model', is_required: true, order: 4 },
        { id: '5', field_name: 'carrier_plan', field_label: '요금제', field_type: 'carrier_plan', is_required: true, order: 5 }
    ];

    const handleAddField = () => {
        const newField = {
            id: Date.now().toString(),
            field_name: 'new_field',
            field_label: '새 필드',
            field_type: 'text',
            is_required: false,
            placeholder: '',
            help_text: '',
            order: template.fields.length + 1,
            field_options: {}
        };
        
        setTemplate(prev => ({
            ...prev,
            fields: [...prev.fields, newField]
        }));
    };

    const handleFieldChange = (fieldId, property, value) => {
        setTemplate(prev => ({
            ...prev,
            fields: prev.fields.map(field => 
                field.id === fieldId 
                    ? { ...field, [property]: value }
                    : field
            )
        }));
    };

    const handleDeleteField = (fieldId) => {
        if (window.confirm('이 필드를 삭제하시겠습니까?')) {
            setTemplate(prev => ({
                ...prev,
                fields: prev.fields.filter(field => field.id !== fieldId)
            }));
        }
    };

    const handleMoveField = (fieldId, direction) => {
        const fields = [...template.fields];
        const index = fields.findIndex(f => f.id === fieldId);
        
        if (direction === 'up' && index > 0) {
            [fields[index], fields[index - 1]] = [fields[index - 1], fields[index]];
        } else if (direction === 'down' && index < fields.length - 1) {
            [fields[index], fields[index + 1]] = [fields[index + 1], fields[index]];
        }
        
        // 순서 재정렬
        fields.forEach((field, idx) => {
            field.order = idx + 1;
        });
        
        setTemplate(prev => ({ ...prev, fields }));
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            
            const saveData = {
                title: template.title,
                description: template.description,
                fields: template.fields
            };

            const response = await post(`api/policies/${id}/form-template/`, saveData);
            
            if (response.success) {
                alert('주문서 양식이 저장되었습니다.');
                setViewMode('view'); // 저장 후 보기 모드로 전환
            } else {
                alert('저장에 실패했습니다: ' + (response.message || '알 수 없는 오류'));
            }
        } catch (error) {
            console.error('저장 실패:', error);
            alert('저장 중 오류가 발생했습니다.');
        } finally {
            setSaving(false);
        }
    };

    const renderFieldEditor = (field) => (
        <div key={field.id} className="field-editor">
            <div className="field-header">
                <div className="field-controls">
                    <button 
                        type="button"
                        onClick={() => handleMoveField(field.id, 'up')}
                        disabled={field.order === 1}
                        className="btn-icon"
                        title="위로 이동"
                    >
                        ↑
                    </button>
                    <button 
                        type="button"
                        onClick={() => handleMoveField(field.id, 'down')}
                        disabled={field.order === template.fields.length}
                        className="btn-icon"
                        title="아래로 이동"
                    >
                        ↓
                    </button>
                    <button 
                        type="button"
                        onClick={() => handleDeleteField(field.id)}
                        className="btn-icon btn-danger"
                        title="삭제"
                    >
                        🗑️
                    </button>
                </div>
                <span className="field-order">#{field.order}</span>
            </div>
            
            <div className="field-config">
                <div className="config-row">
                    <div className="config-group">
                        <label>필드명</label>
                        <input
                            type="text"
                            value={field.field_name}
                            onChange={(e) => handleFieldChange(field.id, 'field_name', e.target.value)}
                        />
                    </div>
                    <div className="config-group">
                        <label>라벨</label>
                        <input
                            type="text"
                            value={field.field_label}
                            onChange={(e) => handleFieldChange(field.id, 'field_label', e.target.value)}
                        />
                    </div>
                </div>
                
                <div className="config-row">
                    <div className="config-group">
                        <label>타입</label>
                        <select
                            value={field.field_type}
                            onChange={(e) => handleFieldChange(field.id, 'field_type', e.target.value)}
                        >
                            {FIELD_TYPES.map(type => (
                                <option key={type.value} value={type.value}>
                                    {type.label}
                                </option>
                            ))}
                        </select>
                    </div>
                    <div className="config-group">
                        <label>
                            <input
                                type="checkbox"
                                checked={field.is_required}
                                onChange={(e) => handleFieldChange(field.id, 'is_required', e.target.checked)}
                            />
                            필수 필드
                        </label>
                    </div>
                </div>
                
                <div className="config-row">
                    <div className="config-group">
                        <label>플레이스홀더</label>
                        <input
                            type="text"
                            value={field.placeholder || ''}
                            onChange={(e) => handleFieldChange(field.id, 'placeholder', e.target.value)}
                        />
                    </div>
                    <div className="config-group">
                        <label>도움말</label>
                        <input
                            type="text"
                            value={field.help_text || ''}
                            onChange={(e) => handleFieldChange(field.id, 'help_text', e.target.value)}
                        />
                    </div>
                </div>
            </div>
        </div>
    );

    const renderPreview = () => (
        <div className="form-preview">
            <h3>{template.title}</h3>
            {template.description && <p>{template.description}</p>}
            
            <form className="preview-form">
                {template.fields.map(field => (
                    <div key={field.id} className="preview-field">
                        <label>
                            {field.field_label}
                            {field.is_required && <span className="required">*</span>}
                        </label>
                        
                        {field.field_type === 'textarea' ? (
                            <textarea 
                                placeholder={field.placeholder}
                                disabled
                            />
                        ) : field.field_type === 'select' || 
                             field.field_type === 'carrier_plan' || 
                             field.field_type === 'device_model' ? (
                            <select disabled>
                                <option>{field.placeholder || '선택하세요'}</option>
                            </select>
                        ) : (
                            <input 
                                type={field.field_type === 'number' ? 'number' : 
                                      field.field_type === 'email' ? 'email' :
                                      field.field_type === 'date' ? 'date' : 'text'}
                                placeholder={field.placeholder}
                                disabled
                            />
                        )}
                        
                        {field.help_text && (
                            <small className="help-text">{field.help_text}</small>
                        )}
                    </div>
                ))}
            </form>
        </div>
    );

    if (loading) {
        return (
            <div className="form-template-editor">
                <div className="loading">데이터를 불러오는 중...</div>
            </div>
        );
    }

    // 디버깅용 로그
    console.log('[OrderFormTemplateEditor] 현재 템플릿 상태:', template);
    console.log('[OrderFormTemplateEditor] 필드 개수:', template.fields?.length || 0);

    return (
        <div className="form-template-editor">
            <div className="page-header">
                <div className="header-content">
                    <button 
                        className="back-btn" 
                        onClick={() => navigate('/policies')}
                    >
                        ← 목록으로
                    </button>
                    <h1>{viewMode === 'edit' ? '주문서 양식 편집' : '주문서 양식'}</h1>
                    <p>{policy?.title} 정책의 주문서 양식{viewMode === 'edit' ? '을 편집합니다' : '입니다'}.</p>
                </div>
                <div className="header-actions">
                    {viewMode === 'view' ? (
                        <>
                            <button 
                                className="btn btn-info"
                                onClick={() => {
                                    console.log('[OrderFormTemplateEditor] 수정 버튼 클릭 - 현재 템플릿 상태:', template);
                                    console.log('[OrderFormTemplateEditor] 수정 버튼 클릭 - 필드 개수:', template.fields?.length || 0);
                                    setViewMode('edit');
                                }}
                            >
                                수정
                            </button>
                            <button 
                                className="btn btn-secondary"
                                onClick={() => navigate('/policies')}
                            >
                                확인
                            </button>
                        </>
                    ) : (
                        <>
                            <button 
                                className="btn btn-secondary"
                                onClick={() => setViewMode('view')}
                                disabled={saving}
                            >
                                미리보기
                            </button>
                            <button 
                                className="btn btn-primary"
                                onClick={handleSave}
                                disabled={saving}
                            >
                                {saving ? '저장 중...' : '저장'}
                            </button>
                        </>
                    )}
                </div>
            </div>

            <div className="editor-container">
                {(() => {
                    console.log('[OrderFormTemplateEditor] 컨테이너 렌더링 - viewMode:', viewMode);
                    console.log('[OrderFormTemplateEditor] 컨테이너 렌더링 - template:', template);
                    return null;
                })()}
                {viewMode === 'edit' ? (
                    <>
                        {/* 기본 정보 */}
                        <div className="basic-info-section">
                            <h3>기본 정보</h3>
                            <div className="form-group">
                                <label>제목</label>
                                <input
                                    type="text"
                                    value={template.title}
                                    onChange={(e) => setTemplate(prev => ({ ...prev, title: e.target.value }))}
                                />
                            </div>
                            <div className="form-group">
                                <label>설명</label>
                                <textarea
                                    value={template.description}
                                    onChange={(e) => setTemplate(prev => ({ ...prev, description: e.target.value }))}
                                    rows="3"
                                />
                            </div>
                        </div>

                        {/* 필드 구성 - 크기 확대 */}
                        <div className="fields-section">
                            <div className="section-header">
                                <h3>필드 구성</h3>
                                <button 
                                    className="btn btn-success"
                                    onClick={handleAddField}
                                >
                                    + 필드 추가
                                </button>
                            </div>
                            
                            <div className="fields-container">
                                {(() => {
                                    console.log('[OrderFormTemplateEditor] 렌더링 시점 필드 확인:', {
                                        hasFields: template.fields && template.fields.length > 0,
                                        fieldsLength: template.fields?.length || 0,
                                        fields: template.fields
                                    });
                                    
                                    if (template.fields && template.fields.length > 0) {
                                        console.log('[OrderFormTemplateEditor] 필드 렌더링 시작');
                                        return template.fields.map(renderFieldEditor);
                                    } else {
                                        console.log('[OrderFormTemplateEditor] 필드 없음 메시지 표시');
                                        return (
                                            <div className="no-fields-message">
                                                <p>아직 필드가 없습니다. '+ 필드 추가' 버튼을 클릭하여 필드를 추가해보세요.</p>
                                                <p style={{fontSize: '12px', color: '#999', marginTop: '10px'}}>
                                                    디버그: 필드 개수 = {template.fields?.length || 0}
                                                </p>
                                            </div>
                                        );
                                    }
                                })()}
                            </div>
                        </div>
                    </>
                ) : (
                    <div className="preview-section">
                        <h3>주문서 양식 미리보기</h3>
                        {renderPreview()}
                    </div>
                )}
            </div>
        </div>
    );
};

export default OrderFormTemplateEditorPage;
