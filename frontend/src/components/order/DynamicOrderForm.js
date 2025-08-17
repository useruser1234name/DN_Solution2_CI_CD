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
    // 기본 필드들 생성
    const defaultFields = [
      { field_name: 'customer_name', field_label: '고객명', field_type: 'text', is_required: true, order: 1 },
      { field_name: 'phone_number', field_label: '개통번호', field_type: 'phone', is_required: true, order: 2 },
      { field_name: 'carrier_plan', field_label: '요금제', field_type: 'carrier_plan', is_required: true, order: 3 },
      { field_name: 'device_model', field_label: '모델명', field_type: 'device_model', is_required: true, order: 4 },
      { field_name: 'device_color', field_label: '색상', field_type: 'device_color', is_required: true, order: 5 },
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
      const orderData = {
        ...values,
        policy_id: policyId,
        rebate_data: rebateData
      };

      let response;
      if (mode === 'create') {
        response = await post('api/orders/', orderData);
        message.success('주문이 성공적으로 생성되었습니다.');
      } else {
        response = await post(`api/orders/${initialValues.id}/`, orderData);
        message.success('주문이 성공적으로 수정되었습니다.');
      }

      if (onSubmit) {
        onSubmit(response.data);
      }
    } catch (error) {
      console.error('주문 처리 오류:', error);
      message.error('주문 처리 중 오류가 발생했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  // 필드들을 섹션별로 그룹화
  const groupFieldsBySection = (fields) => {
    const sections = {
      customer: { title: '고객 정보', fields: [] },
      device: { title: '기기 정보', fields: [] },
      plan: { title: '요금제 및 통신', fields: [] },
      payment: { title: '결제 정보', fields: [] },
      additional: { title: '추가 정보', fields: [] }
    };

    fields.forEach(field => {
      if (['customer_name', 'birth_date', 'phone_number', 'join_type', 'foreigner_info'].includes(field.field_name)) {
        sections.customer.fields.push(field);
      } else if (['device_model', 'device_color', 'serial_number'].includes(field.field_name)) {
        sections.device.fields.push(field);
      } else if (['carrier_plan', 'sim_type', 'contract_period'].includes(field.field_name)) {
        sections.plan.fields.push(field);
      } else if (['payment_method', 'installment_months', 'installment_principal'].includes(field.field_name)) {
        sections.payment.fields.push(field);
      } else {
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
                        device_model: formValues.device_model
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