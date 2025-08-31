import React, { useState, useEffect, useCallback } from 'react';
import { 
  Form, 
  Button, 
  Row, 
  Col, 
  Card, 
  Typography, 
  message, 
  Spin,
  Divider
} from 'antd';
import { 
  ShoppingCartOutlined, 
  LoadingOutlined
} from '@ant-design/icons';
import { get, post } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';

// 필드 컴포넌트 import
import DynamicOrderField from '../order/DynamicOrderField';
import EnhancedRebateCalculator from './EnhancedRebateCalculator';

import './ComprehensiveOrderForm.css';

const { Text } = Typography;

const ComprehensiveOrderForm = ({ 
  policyId, 
  onSubmit, 
  initialValues = {},
  mode = 'create',
  formTemplate = null // 부모 컴포넌트에서 전달받은 템플릿
}) => {
  const { user } = useAuth();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [policy, setPolicy] = useState(null);
  const [template, setTemplate] = useState(null);
  const [fields, setFields] = useState([]);
  const [formValues, setFormValues] = useState(initialValues);

  // 초기 마운트 시 formTemplate이 전달되었는지 확인
  useEffect(() => {
    if (formTemplate) {
      console.log('[ComprehensiveOrderForm] 부모로부터 전달받은 템플릿 사용:', formTemplate);
      setTemplate(formTemplate);
      processTemplate(formTemplate);
      
      // 정책 정보만 로드
      if (policyId) {
        loadPolicyOnly();
      }
    } else if (policyId) {
      // 템플릿이 없으면 정책과 템플릿 모두 로드
      loadPolicyAndTemplate();
    }
  }, [policyId, formTemplate]);

  // 폼 자동 채움: 정책/사용자 의존값이 준비되면 auto_fill 지정 필드에 값 주입
  useEffect(() => {
    if (!fields || fields.length === 0 || !form) return;
    const values = {};
    fields.forEach(f => {
      if (!f.auto_fill && !f.auto_generate) return;
      if (f.auto_generate && f.field_name === 'order_number') return; // 백엔드 생성
      if (f.auto_fill === 'current_datetime') {
        values[f.field_name] = new Date().toISOString().slice(0, 19).replace('T', ' ');
      } else if (f.auto_fill === 'current_user') {
        if (['company_code','agency_code','primary_id','first_id'].includes(f.field_name)) {
          values[f.field_name] = user?.company?.code || '';
        } else if (f.field_name === 'retailer_name') {
          values[f.field_name] = user?.company?.name || '';
        } else {
          values[f.field_name] = user?.username || '';
        }
      } else if (f.auto_fill === 'from_policy') {
        if (f.field_name === 'carrier') values[f.field_name] = policy?.carrier || '';
        if (f.field_name === 'subscription_type') values[f.field_name] = policy?.join_type || '';
        if (f.field_name === 'reference_url') values[f.field_name] = policy?.external_url || '';
      }
    });
    if (Object.keys(values).length > 0) {
      // 필드 마운트 이후 안전하게 주입
      setTimeout(() => form.setFieldsValue(values), 0);
    }
  }, [fields, policy, user, form]);

  // 정책 정보만 로드하는 함수
  const loadPolicyOnly = useCallback(async () => {
    setLoading(true);
    try {
      console.log('[ComprehensiveOrderForm] 정책 정보만 로딩 시작:', policyId);
      
      const policyResponse = await get(`api/policies/${policyId}/`);
      
      if (policyResponse.success && policyResponse.data) {
        let policyData = policyResponse.data;
        
        // 이중래핑 처리
        if (policyData.data && typeof policyData.data === 'object') {
          console.log('[ComprehensiveOrderForm] 정책 이중래핑 감지, data.data 사용');
          policyData = policyData.data;
        }
        
        console.log('[ComprehensiveOrderForm] 정책 정보 로드 완료:', policyData);
        
        // 정책에서 통신사 정보 가져오기
        if (policyData.carrier) {
          console.log('[ComprehensiveOrderForm] 정책에서 통신사 정보 가져오기:', policyData.carrier);
          // 폼에 통신사 정보 자동 설정
          if (form) {
            form.setFieldsValue({ carrier: policyData.carrier });
          }
        }
        
        setPolicy(policyData);
      } else {
        console.warn('[ComprehensiveOrderForm] 정책 정보 없음:', policyResponse);
        message.error('정책 정보를 불러올 수 없습니다.');
      }
    } catch (error) {
      console.error('[ComprehensiveOrderForm] 정책 정보 로딩 실패:', error);
      message.error('정책 정보를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  }, [policyId, form]);

  const loadPolicyAndTemplate = useCallback(async () => {
    setLoading(true);
    try {
      console.log('[ComprehensiveOrderForm] 정책 및 템플릿 로딩 시작:', policyId);
      
      // 정책 정보와 주문서 템플릿을 병렬로 로드
      const [policyResponse, templateResponse] = await Promise.all([
        get(`api/policies/${policyId}/`),
        get(`api/policies/${policyId}/form-template/`)
      ]);

      if (policyResponse.success && policyResponse.data) {
        let policyData = policyResponse.data;
        
        // 이중래핑 처리
        if (policyData.data && typeof policyData.data === 'object') {
          console.log('[ComprehensiveOrderForm] 정책 이중래핑 감지, data.data 사용');
          policyData = policyData.data;
        }
        
        setPolicy(policyData);
        console.log('[ComprehensiveOrderForm] 정책 로드 완료:', policyData);
        
        // 정책에서 통신사 정보 가져오기
        if (policyData.carrier) {
          console.log('[ComprehensiveOrderForm] 정책에서 통신사 정보 가져오기:', policyData.carrier);
          // 폼에 통신사 정보 자동 설정
          if (form) {
            form.setFieldsValue({ carrier: policyData.carrier });
          }
        }
      }

      if (templateResponse.success && templateResponse.data) {
        let templateData = templateResponse.data;
        
        // 이중래핑 처리
        if (templateData.data && typeof templateData.data === 'object') {
          console.log('[ComprehensiveOrderForm] 템플릿 이중래핑 감지, data.data 사용');
          templateData = templateData.data;
        }
        
        setTemplate(templateData);
        processTemplate(templateData);
        console.log('[ComprehensiveOrderForm] 템플릿 로드 완료:', templateData);
      } else {
        // 기본 필드 생성
        const defaultFields = createDefaultFields();
        setFields(defaultFields);
        console.log('[ComprehensiveOrderForm] 기본 필드 사용:', defaultFields);
      }

    } catch (error) {
      console.error('[ComprehensiveOrderForm] 로딩 실패:', error);
      message.error('주문서 양식을 불러오는데 실패했습니다.');
      
      // 에러 시에도 기본 필드 제공
      const defaultFields = createDefaultFields();
      setFields(defaultFields);
    } finally {
      setLoading(false);
    }
  }, [policyId, form]);

  // 템플릿 데이터 처리 함수
  const processTemplate = (templateData) => {
    if (!templateData) {
      console.warn('[ComprehensiveOrderForm] 템플릿 데이터가 없음');
      setFields([]);
      return;
    }
    
    // 필드 정보 처리
    if (templateData.fields && Array.isArray(templateData.fields)) {
      console.log('[ComprehensiveOrderForm] 템플릿 필드 처리:', templateData.fields.length, '개');
      setFields(templateData.fields);
    } else {
      console.warn('[ComprehensiveOrderForm] 템플릿에 필드가 없음:', templateData);
      setFields([]);
    }
  };

  const createDefaultFields = () => {
    return [
      // 주문서 생성일자 (오늘 날짜+시간, 자동 설정)
      { 
        field_name: 'order_date', 
        field_label: '주문서 생성일자', 
        field_type: 'datetime', 
        is_required: false, 
        order: 0,
        auto_generate: true,
        default_value: new Date().toLocaleString('ko-KR')
      },
      
      // 1차 ID (판매점 코드, 자동 설정)
      { 
        field_name: 'first_id', 
        field_label: '1차 ID', 
        field_type: 'text', 
        is_required: true, 
        order: 0.5,
        auto_generate: true,
        placeholder: '자동 설정됨'
      },
      
      // 주문번호 (자동 생성)
      { 
        field_name: 'order_number', 
        field_label: '주문번호', 
        field_type: 'text', 
        is_required: false, 
        order: 0.7,
        auto_generate: true,
        placeholder: '자동 생성됨'
      },
      
      // 고객 정보
      { field_name: 'customer_name', field_label: '고객명', field_type: 'text', is_required: true, order: 1, placeholder: '고객명을 입력하세요' },
      { field_name: 'subscription_type', field_label: '고객유형', field_type: 'subscription_type', is_required: true, order: 2 },
      { field_name: 'phone_number', field_label: '개통번호', field_type: 'phone', is_required: true, order: 3, placeholder: '010-0000-0000' },
      
      // 기기 및 통신 정보 (6개)
      { field_name: 'device_model', field_label: '모델명', field_type: 'device_model', is_required: true, order: 5 },
      { field_name: 'device_color', field_label: '색상', field_type: 'device_color', is_required: true, order: 6 },
      { field_name: 'serial_number', field_label: '일련번호', field_type: 'text', is_required: true, order: 7, placeholder: '예: 189150' },
      { 
        field_name: 'carrier_plan', 
        field_label: '요금상품명', 
        field_type: 'carrier_plan', 
        is_required: true, 
        order: 8,
        field_options: {
          dynamic: true,
          source: 'CarrierPlan'
        }
      },
      { field_name: 'sim_type', field_label: '유심타입', field_type: 'sim_type', is_required: true, order: 9 },
      
      // 결제 및 지원금 정보 (7개)
      { field_name: 'payment_method', field_label: '현금/할부', field_type: 'payment_method', is_required: true, order: 11 },
      { field_name: 'installment_months', field_label: '할부개월수', field_type: 'installment_months', is_required: false, order: 12 },
      { field_name: 'common_support', field_label: '공통지원금', field_type: 'common_support', is_required: false, order: 13, placeholder: '예: 600000' },
      { field_name: 'additional_support', field_label: '추가지원금', field_type: 'additional_support', is_required: false, order: 14 },
      { field_name: 'free_amount', field_label: '프리금액', field_type: 'free_amount', is_required: false, order: 15, placeholder: '예: 500000' },
      { field_name: 'installment_principal', field_label: '할부원금', field_type: 'installment_principal', is_required: false, order: 16, placeholder: '예: 385000' },
      { field_name: 'additional_fee', field_label: '부가', field_type: 'additional_fee', is_required: false, order: 17 },
      
      // 부가 서비스 정보 (4개)
      { field_name: 'course', field_label: '코스', field_type: 'course', is_required: false, order: 18 },
      { field_name: 'insurance', field_label: '보험', field_type: 'insurance', is_required: false, order: 19 },
      { field_name: 'welfare', field_label: '복지', field_type: 'welfare', is_required: false, order: 20 },
      { field_name: 'legal_info', field_label: '법대정보', field_type: 'legal_info', is_required: false, order: 21 },
      { field_name: 'foreigner_info', field_label: '외국인정보', field_type: 'foreigner_info', is_required: false, order: 22 }
    ];
  };

  const handleFormChange = (changedValues, allValues) => {
    setFormValues(allValues);
    console.log('[ComprehensiveOrderForm] 폼 값 변경:', changedValues, '전체 값:', allValues);
  };

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      console.log('[ComprehensiveOrderForm] 주문 제출:', values);
      
      const orderData = {
        policy_id: policyId,
        ...values,
        // 추가 메타데이터
        form_template_id: template?.id,
        created_by: user?.id,
        company_id: user?.company?.id,
        company_code: user?.company?.code
      };

      const response = await post('api/orders/', orderData);
      
      if (response.success) {
        message.success('주문이 성공적으로 생성되었습니다!');
        if (onSubmit) {
          onSubmit(response.data);
        }
      } else {
        throw new Error(response.message || '주문 생성에 실패했습니다.');
      }
      
    } catch (error) {
      console.error('[ComprehensiveOrderForm] 주문 제출 실패:', error);
      message.error(error.message || '주문 생성 중 오류가 발생했습니다.');
    } finally {
      setSubmitting(false);
    }
  };



  if (loading) {
    return (
      <div className="comprehensive-order-form loading">
        <Spin size="large" />
        <Text style={{ display: 'block', marginTop: 16, textAlign: 'center' }}>
          주문서 양식을 불러오고 있습니다...
        </Text>
      </div>
    );
  }

  return (
    <div className="comprehensive-order-form">

      {/* 주문서 폼 */}
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        onValuesChange={handleFormChange}
        initialValues={initialValues}
        className="comprehensive-order-form-content"
      >
        <Card 
          title="주문서 입력"
          className="form-card"
          styles={{
            header: {
              background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
              color: 'white',
              borderRadius: '8px 8px 0 0'
            }
          }}
        >
          <Row gutter={[24, 16]}>
            {fields.length > 0 ? (
              fields.map(field => (
                <Col xs={24} sm={12} md={8} key={field.field_name}>
                  <DynamicOrderField
                    field={field}
                    form={form}
                    dependencies={{
                      ...formValues,
                      policy_carrier: policy?.carrier, // 정책의 통신사 정보 전달
                      policy_id: policy?.id, // 정책 ID 전달
                      policy_contract_period: policy?.contract_period, // 정책의 계약기간 전달
                      policy_external_url: policy?.external_url, // 정책 외부 URL 전달
                      company_code: user?.company?.code, // 업체코드 전달
                      current_user: user?.username // 현재 사용자 전달
                    }}
                  />
                </Col>
              ))
            ) : (
              <Col span={24}>
                <div style={{ textAlign: 'center', padding: '40px 0' }}>
                  <Text type="secondary">
                    주문서 양식이 정의되지 않았습니다. 관리자에게 문의하세요.
                  </Text>
                </div>
              </Col>
            )}
          </Row>
        </Card>

        {/* 리베이트 계산기 - 숨김 처리 */}
        <div style={{ display: 'none' }}>
          <EnhancedRebateCalculator
            policyId={policyId}
            carrierPlan={formValues.carrier_plan}
            contractPeriod={formValues.contract_period}
            simType={formValues.sim_type}
            formValues={formValues}
          />
        </div>

        {/* 제출 버튼 */}
        <div style={{ textAlign: 'center', marginTop: 32, marginBottom: 32 }}>
          <Button 
            type="primary" 
            htmlType="submit" 
            size="large"
            loading={submitting}
            icon={submitting ? <LoadingOutlined /> : <ShoppingCartOutlined />}
            style={{ 
              minWidth: 240,
              height: 56,
              fontSize: '18px',
              fontWeight: 600,
              background: 'linear-gradient(135deg, #1890ff 0%, #096dd9 100%)',
              border: 'none',
              boxShadow: '0 8px 16px rgba(24, 144, 255, 0.2)'
            }}
          >
            {submitting ? '주문 생성 중...' : '주문서 제출하기'}
          </Button>
        </div>
      </Form>
    </div>
  );
};

export default ComprehensiveOrderForm;
