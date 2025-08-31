import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { get } from '../services/api';
import { Card, Select, Typography, message, Spin } from 'antd';
import { UserOutlined } from '@ant-design/icons';
import ComprehensiveOrderForm from '../components/order/ComprehensiveOrderForm';
import './OrderCreatePage.css';

const { Text } = Typography;
const { Option } = Select;

const OrderCreatePageNew = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(false);
    const [policies, setPolicies] = useState([]);
    const [selectedPolicy, setSelectedPolicy] = useState(null);
    const [orderFormTemplate, setOrderFormTemplate] = useState(null);
    const [loadingTemplate, setLoadingTemplate] = useState(false);

    useEffect(() => {
        fetchPolicies();
    }, []);

    const fetchPolicies = async () => {
        try {
            console.log('[OrderCreatePageNew] 정책 목록 가져오기 시작...');
            setLoading(true);
            
            const response = await get('api/policies/?only_active=1');
            console.log('[OrderCreatePageNew] 정책 API 응답:', response);
            
            if (response.success && response.data) {
                let policiesData = [];
                
                // 이중래핑 문제 디버깅을 위한 로그 추가
                console.log('[OrderCreatePageNew] 원본 응답 데이터 구조:', {
                    hasDataProperty: !!response.data,
                    dataType: typeof response.data,
                    hasNestedData: !!(response.data && response.data.data),
                    nestedDataType: response.data && response.data.data ? typeof response.data.data : 'none',
                    isArrayDirectly: Array.isArray(response.data),
                    isArrayNested: response.data && response.data.data ? Array.isArray(response.data.data) : false
                });
                
                // API 응답 구조 처리 - 이중래핑 처리 강화
                let actualData = response.data;
                
                // 이중래핑 처리 (api.js에서 한번, 백엔드에서 한번)
                if (actualData.data && typeof actualData.data === 'object') {
                    console.log('[OrderCreatePageNew] 이중래핑 감지, data.data 사용');
                    actualData = actualData.data;
                }
                
                if (actualData.results && Array.isArray(actualData.results)) {
                    console.log('[OrderCreatePageNew] results 배열 형태 데이터 사용');
                    policiesData = actualData.results;
                } else if (Array.isArray(actualData)) {
                    console.log('[OrderCreatePageNew] 직접 배열 형태 데이터 사용');
                    policiesData = actualData;
                } else {
                    console.warn('[OrderCreatePageNew] 예상하지 못한 데이터 구조:', response.data);
                }
                
                console.log('[OrderCreatePageNew] 파싱된 정책 데이터:', policiesData);
                
                // 백엔드에서 only_active=1을 적용하므로 추가 필터 없이 그대로 사용
                setPolicies(policiesData);
            } else {
                console.warn('[OrderCreatePageNew] 정책 데이터 없음:', response);
                message.warning('사용 가능한 정책이 없습니다.');
            }
        } catch (error) {
            console.error('[OrderCreatePageNew] 정책 로딩 실패:', error);
            message.error('정책 목록을 불러오는데 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

        // 필드 매핑 함수 - 백엔드 필드를 프론트엔드 형식으로 변환
    const mapFormFields = (fields) => {
        if (!fields || !Array.isArray(fields)) return [];
        
        return fields.map(field => {
            // 필드 이름 처리 (name 또는 field_name 사용)
            const fieldName = field.field_name || field.name || `field_${Math.random().toString(36).substring(2, 9)}`;
            
            // 필드 타입 처리
            let fieldType = field.field_type || field.type || 'text';
            
            // 필드 라벨 처리
            const fieldLabel = field.field_label || field.label || fieldName;
            
            // 필수 여부 처리
            const isRequired = field.is_required || field.required || false;
            
            // 순서 처리
            const order = field.order || 0;
            
            // 플레이스홀더 처리
            const placeholder = field.placeholder || `${fieldLabel}을(를) 입력하세요`;
            
            // 옵션 처리
            const fieldOptions = field.field_options || field.options || {};
            
            // 최종 매핑된 필드 반환
            return {
                field_name: fieldName,
                field_label: fieldLabel,
                field_type: fieldType,
                is_required: isRequired,
                order: order,
                placeholder: placeholder,
                field_options: fieldOptions,
                // 확장 메타 전달
                is_readonly: field.is_readonly || false,
                is_masked: field.is_masked || false,
                auto_fill: field.auto_fill || '',
                auto_generate: field.auto_generate || false,
                allow_manual: field.allow_manual !== undefined ? field.allow_manual : true,
                data_source: field.data_source || '',
                rows: field.rows || 3,
                multiple: field.multiple || false,
                max_files: field.max_files || 4,
                accept: field.accept || 'image/*,.pdf,.doc,.docx'
            };
        });
    };

    // 주문서 양식을 가져오는 함수
    const fetchOrderFormTemplate = async (policyId) => {
        try {
            setLoadingTemplate(true);
            console.log('[OrderCreatePageNew] 주문서 양식 가져오기 시작:', policyId);
            
            const response = await get(`api/policies/${policyId}/form-template/`);
            console.log('[OrderCreatePageNew] 주문서 양식 API 응답:', response);
            
            if (response.success && response.data) {
                let templateData = response.data;
                
                // 이중래핑 처리
                if (templateData.data && typeof templateData.data === 'object') {
                    console.log('[OrderCreatePageNew] 주문서 양식 이중래핑 감지, data.data 사용');
                    templateData = templateData.data;
                }
                
                console.log('[OrderCreatePageNew] 최종 주문서 양식 데이터:', templateData);
                
                // 필드 구조 상세 분석
                if (templateData.fields && Array.isArray(templateData.fields)) {
                    console.log('[OrderCreatePageNew] 필드 개수:', templateData.fields.length);
                    console.log('[OrderCreatePageNew] 첫 번째 필드 구조:', templateData.fields[0]);
                    console.log('[OrderCreatePageNew] 필드 속성 키:', Object.keys(templateData.fields[0]));
                    
                    // 필드 매핑 확인
                    const fieldNames = templateData.fields.map(f => f.name || f.field_name);
                    console.log('[OrderCreatePageNew] 필드 이름 목록:', fieldNames);
                    
                    // 필드 매핑 적용
                    templateData.fields = mapFormFields(templateData.fields);
                    console.log('[OrderCreatePageNew] 매핑된 필드:', templateData.fields);
                }
                
                setOrderFormTemplate(templateData);
                return templateData;
            } else {
                console.warn('[OrderCreatePageNew] 주문서 양식 없음:', response);
                message.info('이 정책에는 주문서 양식이 없습니다. 기본 양식을 사용합니다.');
                setOrderFormTemplate(null);
                return null;
            }
        } catch (error) {
            console.error('[OrderCreatePageNew] 주문서 양식 로딩 실패:', error);
            message.error('주문서 양식을 불러오는데 실패했습니다.');
            setOrderFormTemplate(null);
            return null;
        } finally {
            setLoadingTemplate(false);
        }
    };
    
    const handlePolicySelect = async (policyId) => {
        console.log('[OrderCreatePageNew] 정책 선택 시도:', policyId);
        console.log('[OrderCreatePageNew] 사용 가능한 정책 목록:', policies);
        
        const policy = policies.find(p => p.id === policyId);
        console.log('[OrderCreatePageNew] 선택된 정책 데이터:', policy);
        
        setSelectedPolicy(policy);
        
        // 정책이 선택되면 해당 정책의 주문서 양식 가져오기
        if (policy) {
            await fetchOrderFormTemplate(policyId);
        }
    };

    const handleOrderSubmit = (orderData) => {
        console.log('[OrderCreatePageNew] 주문 제출:', orderData);
        message.success('주문이 성공적으로 생성되었습니다!');
        navigate('/orders');
    };

    return (
        <div className="order-create-page">

            {/* 정책 선택 */}
            <Card 
                title={<><UserOutlined /> 정책 선택</>}
                className="form-card"
                style={{ marginBottom: 24 }}
            >
                <Select
                    placeholder="정책을 선택하세요"
                    onChange={handlePolicySelect}
                    loading={loading}
                    size="large"
                    style={{ width: '100%' }}
                    showSearch
                    filterOption={(input, option) =>
                        option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
                    }
                >
                    {policies.map(policy => (
                        <Option key={policy.id} value={policy.id} label={`${policy.title} - ${policy.carrier_display || policy.carrier}`}>
                            {policy.title} - {policy.carrier_display || policy.carrier}
                        </Option>
                    ))}
                </Select>


            </Card>

            {/* 로딩 상태 표시 */}
            {selectedPolicy && loadingTemplate && (
                <Card style={{ marginBottom: 24, textAlign: 'center', padding: '40px 0' }}>
                    <Spin size="large" />
                    <div style={{ marginTop: 16 }}>
                        <Text>주문서 양식을 불러오는 중...</Text>
                    </div>
                </Card>
            )}
            
            {/* 종합 주문서 양식 */}
            {selectedPolicy && (
                <ComprehensiveOrderForm
                    policyId={selectedPolicy.id}
                    formTemplate={orderFormTemplate}
                    onSubmit={handleOrderSubmit}
                    mode="create"
                />
            )}

            {!selectedPolicy && policies.length === 0 && !loading && (
                <Card style={{ textAlign: 'center', padding: 40 }}>
                    <Text type="secondary">
                        사용 가능한 정책이 없습니다. 관리자에게 문의하세요.
                    </Text>
                </Card>
            )}
        </div>
    );
};

export default OrderCreatePageNew;
