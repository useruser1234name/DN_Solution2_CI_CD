import React, { useState, useEffect } from 'react';
import { 
  Form, 
  Card, 
  Row, 
  Col, 
  Button, 
  message, 
  Spin,
  Typography,
  Divider,
  Space
} from 'antd';
import { SaveOutlined, CalculatorOutlined } from '@ant-design/icons';
import DynamicOrderField from './DynamicOrderField';
import RebateCalculator from '../common/RebateCalculator';
import { get, post } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './DynamicOrderForm.css';

const { Title, Text } = Typography;

const DynamicOrderForm = ({ 
  policyId, 
  onSubmit, 
  initialValues = {},
  mode = 'create'
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [policy, setPolicy] = useState(null);
  const [template, setTemplate] = useState(null);
  const [fields, setFields] = useState([]);
  const [formValues, setFormValues] = useState({});
  const [rebateData, setRebateData] = useState(null);
  
  const { user } = useAuth();

  // 정책 및 템플릿 로드
  useEffect(() => {
    if (policyId) {
      loadPolicyAndTemplate();
    }
  }, [policyId]);

  // 초기값 설정
  useEffect(() => {
    if (initialValues && Object.keys(initialValues).length > 0) {
      form.setFieldsValue(initialValues);
      setFormValues(initialValues);
    }
  }, [initialValues, form]);

  const loadPolicyAndTemplate = async () => {
    setLoading(true);
    try {
      // 정책 정보 로드
      const policyResponse = await get(`api/policies/${policyId}/`);
      if (policyResponse.success) {
        setPolicy(policyResponse.data);
      }

      // 주문서 템플릿 로드
      const templateResponse = await get(`api/policies/${policyId}/form-template/`);
      if (templateResponse.success && templateResponse.data) {
        setTemplate(templateResponse.data);
        
        // 필드들을 순서대로 정렬
        const sortedFields = (templateResponse.data.fields || []).sort((a, b) => a.order - b.order);
        setFields(sortedFields);
      } else {
        message.warning('주문서 템플릿이 설정되지 않았습니다. 기본 양식을 사용합니다.');
        createDefaultFields();
      }
    } catch (error) {
      console.error('정책/템플릿 로드 오류:', error);
      message.error('정책 정보를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const createDefaultFields = () => {
    // 개선된 기본 필드들 생성
    const defaultFields = [
      // 자동 입력 필드
      { field_name: 'order_id', field_label: '주문번호', field_type: 'text', is_required: true, is_readonly: true, auto_generate: true, order: 1 },
      { field_name: 'received_date', field_label: '접수일자', field_type: 'datetime', is_required: true, is_readonly: true, auto_fill: 'current_datetime', order: 2 },
      { field_name: 'primary_id', field_label: '1차 ID', field_type: 'text', is_required: true, is_readonly: true, auto_fill: 'current_user', order: 3 },
      { field_name: 'carrier', field_label: '통신사', field_type: 'text', is_required: true, is_readonly: true, auto_fill: 'from_policy', order: 4 },
      { field_name: 'subscription_type', field_label: '가입유형', field_type: 'text', is_required: true, is_readonly: true, auto_fill: 'from_policy', order: 5 },
      
      // 고객 정보
      { field_name: 'customer_name', field_label: '고객명', field_type: 'text', is_required: true, order: 6 },
      { field_name: 'customer_type', field_label: '고객유형', field_type: 'select', is_required: true, order: 7 },
      { field_name: 'phone_number', field_label: '개통번호', field_type: 'phone', is_required: true, order: 8 },
      { field_name: 'ssn', field_label: '주민등록번호', field_type: 'text', is_required: true, is_masked: true, order: 9 },
      
      // 기기 정보 (바코드 스캔 가능)
      { field_name: 'device_model', field_label: '단말기 모델', field_type: 'text', is_required: true, order: 11 },
      { field_name: 'device_serial_number', field_label: '단말기 일련번호', field_type: 'barcode_scan', is_required: true, allow_manual: true, order: 12 },
      { field_name: 'imei', field_label: 'IMEI', field_type: 'barcode_scan', is_required: true, allow_manual: true, order: 13 },
      { field_name: 'imei2', field_label: 'IMEI2', field_type: 'barcode_scan', is_required: false, allow_manual: true, order: 14 },
      { field_name: 'eid', field_label: 'EID', field_type: 'barcode_scan', is_required: false, allow_manual: true, order: 15 },
      
      // 요금제
      { field_name: 'plan_name', field_label: '요금상품명', field_type: 'dropdown_from_policy', is_required: true, data_source: 'policy_plans', order: 16 },
      
      // 메모
      { field_name: 'customer_memo', field_label: '고객 메모', field_type: 'large_textarea', is_required: false, rows: 8, order: 27 },
      { field_name: 'reference_url', field_label: '참조 URL', field_type: 'url', is_required: false, order: 26 },
    ];
    setFields(defaultFields);
  };

  const handleFormChange = (changedValues, allValues) => {
    setFormValues(allValues);
    
    // 리베이트 계산 트리거 (필요한 필드들이 모두 입력된 경우)
    if (allValues.carrier_plan && allValues.contract_period && allValues.sim_type) {
      calculateRebate(allValues);
    }
  };

  const calculateRebate = async (values) => {
    try {
      const response = await get('api/policies/calculate-rebate/', {
        params: {
          policy_id: policyId,
          plan_id: values.carrier_plan,
          contract_period: values.contract_period,
          sim_type: values.sim_type
        }
      });
      
      if (response.success) {
        setRebateData(response.data);
      }
    } catch (error) {
      console.error('리베이트 계산 오류:', error);
    }
  };

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      // 자동 입력 필드 추가
      const orderData = {
        ...values,
        policy_id: policyId,
        rebate_data: rebateData,
        // 자동 입력 필드들
        order_id: `ORD-${Date.now()}`, // 임시 주문번호 생성
        received_date: new Date().toISOString(),
        primary_id: user?.username || 'unknown',
        carrier: policy?.carrier || 'unknown',
        subscription_type: policy?.join_type || 'unknown'
      };

      let response;
      if (mode === 'create') {
        response = await post('api/orders/', orderData);
        if (response.success) {
          message.success(`주문이 성공적으로 생성되었습니다. 주문번호: ${response.data.order_number}`);
        } else {
          throw new Error(response.message || '주문 생성 실패');
        }
      } else {
        response = await post(`api/orders/${initialValues.id}/`, orderData);
        message.success('주문이 성공적으로 수정되었습니다.');
      }

      if (onSubmit) {
        onSubmit(response.data);
      }
    } catch (error) {
      console.error('주문 처리 오류:', error);
      message.error(error.message || '주문 처리 중 오류가 발생했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  // 필드들을 섹션별로 그룹화
  const groupFieldsBySection = (fields) => {
    const sections = {
      auto: { title: '자동 입력 정보', fields: [] },
      customer: { title: '고객 정보', fields: [] },
      device: { title: '기기 정보', fields: [] },
      plan: { title: '요금제 및 서비스', fields: [] },
      sim: { title: '유심 정보', fields: [] },
      porting: { title: '번호이동 정보', fields: [] },
      payment: { title: '결제 정보', fields: [] },
      additional: { title: '추가 정보', fields: [] }
    };

    fields.forEach(field => {
      // 자동 입력 필드
      if (['order_id', 'received_date', 'primary_id', 'carrier', 'subscription_type'].includes(field.field_name)) {
        sections.auto.fields.push(field);
      }
      // 고객 정보
      else if (['customer_name', 'customer_type', 'phone_number', 'ssn', 'customer_address'].includes(field.field_name)) {
        sections.customer.fields.push(field);
      }
      // 기기 정보
      else if (['device_model', 'device_serial_number', 'imei', 'imei2', 'eid'].includes(field.field_name)) {
        sections.device.fields.push(field);
      }
      // 요금제 및 서비스
      else if (['plan_name', 'contract_period'].includes(field.field_name)) {
        sections.plan.fields.push(field);
      }
      // 유심 정보
      else if (['sim_model', 'sim_serial_number'].includes(field.field_name)) {
        sections.sim.fields.push(field);
      }
      // 번호이동 정보
      else if (['previous_carrier', 'mvno_carrier'].includes(field.field_name)) {
        sections.porting.fields.push(field);
      }
      // 결제 정보
      else if (['payment_method', 'account_holder', 'bank_name', 'account_number'].includes(field.field_name)) {
        sections.payment.fields.push(field);
      }
      // 추가 정보
      else {
        sections.additional.fields.push(field);
      }
    });

    return sections;
  };

  if (loading) {
    return (
      <div className="dynamic-order-form loading">
        <Spin size="large" />
        <Text style={{ marginTop: 16 }}>주문서 양식을 불러오는 중...</Text>
      </div>
    );
  }

  const sections = groupFieldsBySection(fields);

  return (
    <div className="dynamic-order-form">
      <Card className="form-header">
        <Title level={3}>
          {mode === 'create' ? '새 주문 생성' : '주문 수정'}
        </Title>
        {policy && (
          <Text type="secondary">
            정책: {policy.title} | 통신사: {policy.carrier_display || policy.carrier}
          </Text>
        )}
        {template && (
          <Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
            양식: {template.title}
          </Text>
        )}
      </Card>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        onValuesChange={handleFormChange}
        className="order-form"
      >
        <Row gutter={24}>
          {Object.entries(sections).map(([sectionKey, section]) => {
            if (section.fields.length === 0) return null;
            
            return (
              <Col xs={24} lg={12} key={sectionKey}>
                <Card title={section.title} className="form-section">
                  {section.fields.map(field => (
                    <DynamicOrderField
                      key={field.field_name}
                      field={field}
                      form={form}
                      dependencies={{
                        carrier: formValues.carrier,
                        device_model: formValues.device_model,
                        policy_carrier: policy?.carrier,
                        policy_join_type: policy?.join_type,
                        current_user: user?.username
                      }}
                    />
                  ))}
                </Card>
              </Col>
            );
          })}
        </Row>

        {/* 리베이트 계산기 */}
        {rebateData && (
          <Card title="리베이트 정보" className="rebate-section">
            <Row gutter={16}>
              <Col span={8}>
                <div className="rebate-item">
                  <Text strong>기본 리베이트</Text>
                  <div className="rebate-amount">
                    {rebateData.base_rebate?.toLocaleString()}원
                  </div>
                </div>
              </Col>
              <Col span={8}>
                <div className="rebate-item">
                  <Text strong>유심비 조정</Text>
                  <div className={`rebate-amount ${rebateData.sim_adjustment >= 0 ? 'positive' : 'negative'}`}>
                    {rebateData.sim_adjustment >= 0 ? '+' : ''}{rebateData.sim_adjustment?.toLocaleString()}원
                  </div>
                </div>
              </Col>
              <Col span={8}>
                <div className="rebate-item">
                  <Text strong>최종 리베이트</Text>
                  <div className="rebate-amount final">
                    {rebateData.final_rebate?.toLocaleString()}원
                  </div>
                </div>
              </Col>
            </Row>
          </Card>
        )}

        <Divider />

        <div className="form-actions">
          <Space>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={submitting}
              icon={<SaveOutlined />}
              size="large"
            >
              {mode === 'create' ? '주문 생성' : '주문 수정'}
            </Button>
            <Button 
              type="default" 
              onClick={() => calculateRebate(formValues)}
              icon={<CalculatorOutlined />}
              disabled={!formValues.carrier_plan || !formValues.contract_period}
            >
              리베이트 재계산
            </Button>
          </Space>
        </div>
      </Form>
    </div>
  );
};

export default DynamicOrderForm;