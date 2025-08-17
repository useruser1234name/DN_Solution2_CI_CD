import React, { useState, useEffect } from 'react';
import { 
  Form, 
  Input, 
  Select, 
  Button, 
  Card, 
  Row, 
  Col, 
  message, 
  Divider,
  Space,
  Typography,
  Spin
} from 'antd';
import { SaveOutlined, CalculatorOutlined } from '@ant-design/icons';
import CarrierPlanSelector from '../common/CarrierPlanSelector';
import DeviceSelector from '../common/DeviceSelector';
import RebateCalculator from '../common/RebateCalculator';
import { get, post } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './EnhancedOrderForm.css';

const { Option } = Select;
const { TextArea } = Input;
const { Title, Text } = Typography;

const EnhancedOrderForm = ({ 
  policyId, 
  onSubmit, 
  initialValues = {},
  mode = 'create' // 'create' or 'edit'
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [policy, setPolicy] = useState(null);
  
  // 폼 상태
  const [selectedCarrier, setSelectedCarrier] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [selectedColor, setSelectedColor] = useState(null);
  const [contractPeriod, setContractPeriod] = useState(null);
  const [simType, setSimType] = useState(null);
  
  const { user, isRetail } = useAuth();

  // 정책 정보 로드
  useEffect(() => {
    if (policyId) {
      loadPolicy();
    }
  }, [policyId]);

  // 초기값 설정
  useEffect(() => {
    if (initialValues && Object.keys(initialValues).length > 0) {
      form.setFieldsValue(initialValues);
      setSelectedCarrier(initialValues.carrier);
      setSelectedPlan(initialValues.plan_id);
      setSelectedModel(initialValues.device_model);
      setSelectedColor(initialValues.device_color);
      setContractPeriod(initialValues.contract_period);
      setSimType(initialValues.sim_type);
    }
  }, [initialValues, form]);

  const loadPolicy = async () => {
    setLoading(true);
    try {
      const response = await get(`/api/policies/${policyId}/`);
      if (response.success) {
        setPolicy(response.data);
      } else {
        message.error('정책 정보를 불러오는데 실패했습니다.');
      }
    } catch (error) {
      console.error('정책 로드 오류:', error);
      message.error('정책 정보를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (values) => {
    setSubmitting(true);
    try {
      const orderData = {
        ...values,
        policy_id: policyId,
        carrier: selectedCarrier,
        plan_id: selectedPlan,
        device_model: selectedModel,
        device_color: selectedColor,
        contract_period: contractPeriod,
        sim_type: simType
      };

      if (mode === 'create') {
        await post('/api/orders/', orderData);
        message.success('주문이 성공적으로 생성되었습니다.');
      } else {
        await post(`/api/orders/${initialValues.id}/`, orderData);
        message.success('주문이 성공적으로 수정되었습니다.');
      }

      if (onSubmit) {
        onSubmit(orderData);
      }
    } catch (error) {
      console.error('주문 처리 오류:', error);
      message.error('주문 처리 중 오류가 발생했습니다.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCarrierChange = (carrier) => {
    setSelectedCarrier(carrier);
    setSelectedPlan(null); // 통신사 변경 시 요금제 초기화
    form.setFieldsValue({ plan_id: null });
  };

  const handlePlanSelect = (planData) => {
    setSelectedPlan(planData?.id);
  };

  const handleDeviceSelect = ({ type, data }) => {
    if (type === 'model') {
      setSelectedModel(data?.id);
      setSelectedColor(null); // 모델 변경 시 색상 초기화
      form.setFieldsValue({ device_color: null });
    } else if (type === 'color') {
      setSelectedColor(data?.id);
    }
  };

  const handleRebateCalculated = (rebateData) => {
    // 리베이트 계산 결과를 폼에 반영할 수 있음
    console.log('계산된 리베이트:', rebateData);
  };

  if (loading) {
    return (
      <div className="enhanced-order-form loading">
        <Spin size="large" />
        <Text style={{ marginTop: 16 }}>정책 정보를 불러오는 중...</Text>
      </div>
    );
  }

  return (
    <div className="enhanced-order-form">
      <Card className="form-header">
        <Title level={3}>
          {mode === 'create' ? '새 주문 생성' : '주문 수정'}
        </Title>
        {policy && (
          <Text type="secondary">
            정책: {policy.title} | 통신사: {policy.carrier_display}
          </Text>
        )}
      </Card>

      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        className="order-form"
      >
        <Row gutter={24}>
          {/* 고객 정보 */}
          <Col xs={24} lg={12}>
            <Card title="고객 정보" className="form-section">
              <Form.Item
                name="customer_name"
                label="고객명"
                rules={[{ required: true, message: '고객명을 입력하세요' }]}
              >
                <Input placeholder="예: 홍길동" />
              </Form.Item>

              <Form.Item
                name="birth_date"
                label="생년월일"
                rules={[{ required: true, message: '생년월일을 입력하세요' }]}
              >
                <Input placeholder="예: 901234" />
              </Form.Item>

              <Form.Item
                name="phone_number"
                label="개통번호"
                rules={[{ required: true, message: '개통번호를 입력하세요' }]}
              >
                <Input placeholder="예: 010-1234-5678" />
              </Form.Item>

              <Form.Item
                name="join_type"
                label="가입유형"
                rules={[{ required: true, message: '가입유형을 선택하세요' }]}
              >
                <Select placeholder="가입유형을 선택하세요">
                  <Option value="new_subscription">신규가입</Option>
                  <Option value="number_transfer">번호이동</Option>
                  <Option value="device_change">기기변경</Option>
                </Select>
              </Form.Item>
            </Card>
          </Col>

          {/* 통신사 및 요금제 */}
          <Col xs={24} lg={12}>
            <Card title="통신사 및 요금제" className="form-section">
              <Form.Item
                name="carrier"
                label="통신사"
                rules={[{ required: true, message: '통신사를 선택하세요' }]}
              >
                <Select 
                  placeholder="통신사를 선택하세요"
                  onChange={handleCarrierChange}
                >
                  <Option value="skt">SKT</Option>
                  <Option value="kt">KT</Option>
                  <Option value="lg">LG U+</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="plan_id"
                label="요금제"
                rules={[{ required: true, message: '요금제를 선택하세요' }]}
              >
                <CarrierPlanSelector
                  value={selectedPlan}
                  onChange={setSelectedPlan}
                  carrier={selectedCarrier}
                  onPlanSelect={handlePlanSelect}
                />
              </Form.Item>

              <Form.Item
                name="contract_period"
                label="계약기간"
                rules={[{ required: true, message: '계약기간을 선택하세요' }]}
              >
                <Select 
                  placeholder="계약기간을 선택하세요"
                  onChange={setContractPeriod}
                >
                  <Option value={12}>12개월</Option>
                  <Option value={24}>24개월</Option>
                  <Option value={36}>36개월</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="sim_type"
                label="유심 타입"
                rules={[{ required: true, message: '유심 타입을 선택하세요' }]}
              >
                <Select 
                  placeholder="유심 타입을 선택하세요"
                  onChange={setSimType}
                >
                  <Option value="prepaid">선불 (본사 7,700원 지급)</Option>
                  <Option value="postpaid">후불 (본사 7,700원 차감)</Option>
                  <Option value="esim">eSIM</Option>
                  <Option value="reuse">재사용</Option>
                </Select>
              </Form.Item>
            </Card>
          </Col>
        </Row>

        <Row gutter={24}>
          {/* 기기 정보 */}
          <Col xs={24} lg={12}>
            <Card title="기기 정보" className="form-section">
              <DeviceSelector
                modelValue={selectedModel}
                colorValue={selectedColor}
                onModelChange={setSelectedModel}
                onColorChange={setSelectedColor}
                onDeviceSelect={handleDeviceSelect}
              />

              <Form.Item
                name="serial_number"
                label="일련번호"
                rules={[{ required: true, message: '일련번호를 입력하세요' }]}
              >
                <Input placeholder="예: 189150" />
              </Form.Item>
            </Card>
          </Col>

          {/* 결제 정보 */}
          <Col xs={24} lg={12}>
            <Card title="결제 정보" className="form-section">
              <Form.Item
                name="payment_method"
                label="현금/할부"
                rules={[{ required: true, message: '결제 방법을 선택하세요' }]}
              >
                <Select placeholder="결제 방법을 선택하세요">
                  <Option value="cash">현금</Option>
                  <Option value="installment">할부</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="installment_months"
                label="할부개월수"
              >
                <Select placeholder="할부개월수를 선택하세요">
                  <Option value={12}>12개월</Option>
                  <Option value={24}>24개월</Option>
                  <Option value={36}>36개월</Option>
                </Select>
              </Form.Item>

              <Form.Item
                name="common_support"
                label="공통지원금"
              >
                <Input placeholder="예: 600,000" />
              </Form.Item>

              <Form.Item
                name="additional_support"
                label="추가지원금"
              >
                <Input placeholder="추가지원금을 입력하세요" />
              </Form.Item>

              <Form.Item
                name="free_amount"
                label="프리금액"
              >
                <Input placeholder="예: 500,000" />
              </Form.Item>

              <Form.Item
                name="installment_principal"
                label="할부원금"
              >
                <Input placeholder="예: 385,000" />
              </Form.Item>
            </Card>
          </Col>
        </Row>

        {/* 추가 정보 */}
        <Row gutter={24}>
          <Col xs={24}>
            <Card title="추가 정보" className="form-section">
              <Row gutter={16}>
                <Col xs={24} sm={8}>
                  <Form.Item name="course" label="코스">
                    <Input placeholder="예: 심플" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="additional" label="부가">
                    <Input placeholder="부가 서비스" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={8}>
                  <Form.Item name="insurance" label="보험">
                    <Input placeholder="예: 파손" />
                  </Form.Item>
                </Col>
              </Row>

              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <Form.Item name="welfare" label="복지">
                    <Input placeholder="복지 혜택" />
                  </Form.Item>
                </Col>
                <Col xs={24} sm={12}>
                  <Form.Item name="legal_info" label="법대정보">
                    <Input placeholder="법정대리인 정보" />
                  </Form.Item>
                </Col>
              </Row>

              <Form.Item name="foreigner_info" label="외국인(국적/발급일자)">
                <Input placeholder="외국인인 경우 국적과 발급일자" />
              </Form.Item>

              <Form.Item name="notes" label="비고">
                <TextArea rows={3} placeholder="추가 메모사항" />
              </Form.Item>
            </Card>
          </Col>
        </Row>

        {/* 리베이트 계산 */}
        {isRetail() && (
          <Row gutter={24}>
            <Col xs={24}>
              <RebateCalculator
                policyId={policyId}
                carrier={selectedCarrier}
                planId={selectedPlan}
                contractPeriod={contractPeriod}
                simType={simType}
                onRebateCalculated={handleRebateCalculated}
              />
            </Col>
          </Row>
        )}

        {/* 제출 버튼 */}
        <Row>
          <Col xs={24}>
            <div className="form-actions">
              <Space size="middle">
                <Button 
                  type="primary" 
                  htmlType="submit" 
                  loading={submitting}
                  icon={<SaveOutlined />}
                  size="large"
                >
                  {mode === 'create' ? '주문 생성' : '주문 수정'}
                </Button>
                <Button size="large">
                  취소
                </Button>
              </Space>
            </div>
          </Col>
        </Row>
      </Form>
    </div>
  );
};

export default EnhancedOrderForm;

