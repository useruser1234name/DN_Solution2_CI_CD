import React, { useState } from 'react';
import { Form, Input, Select, Button, message, Card, Row, Col, Alert } from 'antd';
import { post } from '../services/api';
import PolicyExposureModal from './PolicyExposureModal';
import OrderFormBuilder from './OrderFormBuilder';
import './PolicyCreateForm.css';

const { Option } = Select;
const { TextArea } = Input;

const PolicyCreateForm = ({ onSuccess, onCancel }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [createdPolicy, setCreatedPolicy] = useState(null);
  const [showExposureModal, setShowExposureModal] = useState(false);
  const [showOrderFormModal, setShowOrderFormModal] = useState(false);

  const formTypes = [
    { value: 'individual', label: '개인' },
    { value: 'business', label: '기업' },
    { value: 'general', label: '일반' }
  ];

  const carriers = [
    { value: 'skt', label: 'SKT' },
    { value: 'kt', label: 'KT' },
    { value: 'lg', label: 'LG U+' },
    { value: 'altheon', label: '알뜰폰' }
  ];

  const contractPeriods = [
    { value: '12', label: '12개월' },
    { value: '24', label: '24개월' },
    { value: '36', label: '36개월' }
  ];

  const handleSubmit = async (values) => {
    setLoading(true);
    try {
      const response = await post('api/policies/api/create/', values);
      
      if (response.success) {
        message.success('정책이 성공적으로 생성되었습니다.');
        setCreatedPolicy(response.policy);
        
        // 정책 생성 후 협력사 선택 모달 자동 표시
        setShowExposureModal(true);
        
        if (onSuccess) {
          onSuccess(response.policy);
        }
      }
    } catch (error) {
      message.error('정책 생성에 실패했습니다.');
      console.error('Error creating policy:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleExposureModalClose = () => {
    setShowExposureModal(false);
    // 협력사 선택 완료 후 주문서 양식 설계 모달 표시
    setShowOrderFormModal(true);
  };

  const handleOrderFormModalClose = () => {
    setShowOrderFormModal(false);
    // 모든 모달이 닫힌 후 폼 초기화
    form.resetFields();
    setCreatedPolicy(null);
  };

  return (
    <>
      <Card title="새 정책 생성" className="policy-create-card">
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            form_type: 'general',
            carrier: 'skt',
            contract_period: '24',
            expose: true,
            premium_market_expose: false
          }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="title"
                label="정책명"
                rules={[{ required: true, message: '정책명을 입력하세요' }]}
              >
                <Input placeholder="정책명을 입력하세요" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="form_type"
                label="신청서 타입"
                rules={[{ required: true, message: '신청서 타입을 선택하세요' }]}
              >
                <Select placeholder="신청서 타입을 선택하세요">
                  {formTypes.map(type => (
                    <Option key={type.value} value={type.value}>
                      {type.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="carrier"
                label="통신사"
                rules={[{ required: true, message: '통신사를 선택하세요' }]}
              >
                <Select placeholder="통신사를 선택하세요">
                  {carriers.map(carrier => (
                    <Option key={carrier.value} value={carrier.value}>
                      {carrier.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="contract_period"
                label="가입기간"
                rules={[{ required: true, message: '가입기간을 선택하세요' }]}
              >
                <Select placeholder="가입기간을 선택하세요">
                  {contractPeriods.map(period => (
                    <Option key={period.value} value={period.value}>
                      {period.period}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="정책 설명"
          >
            <TextArea rows={3} placeholder="정책에 대한 설명을 입력하세요" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={24}>
              <Alert
                message="리베이트 설정 안내"
                description="본사는 협력사에게 줄 리베이트만 설정합니다. 판매점 리베이트는 각 협력사가 마진을 고려하여 개별 설정합니다."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="rebate_agency"
                label="협력사 리베이트"
                rules={[{ required: true, message: '협력사 리베이트를 입력하세요' }]}
              >
                <Input 
                  placeholder="협력사에게 지급할 리베이트" 
                  suffix="원"
                  type="number"
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <div style={{ padding: '32px 0', textAlign: 'center', color: '#666' }}>
                <div style={{ fontSize: '14px', marginBottom: '8px' }}>
                  📊 <strong>판매점 리베이트</strong>
                </div>
                <div style={{ fontSize: '12px' }}>
                  협력사가 개별 설정
                </div>
              </div>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="expose"
                label="일반 노출"
                valuePropName="checked"
              >
                <Select>
                  <Option value={true}>노출</Option>
                  <Option value={false}>비노출</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="premium_market_expose"
                label="프리미엄 마켓 노출"
                valuePropName="checked"
              >
                <Select>
                  <Option value={true}>노출</Option>
                  <Option value={false}>비노출</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item>
            <div className="form-actions">
              <Button onClick={onCancel}>
                취소
              </Button>
              <Button 
                type="primary" 
                htmlType="submit"
                loading={loading}
              >
                정책 생성
              </Button>
            </div>
          </Form.Item>
        </Form>
      </Card>

      {/* 협력사 선택 모달 */}
      {createdPolicy && (
        <PolicyExposureModal
          visible={showExposureModal}
          onClose={handleExposureModalClose}
          policyId={createdPolicy.id}
          policyTitle={createdPolicy.title}
        />
      )}

      {/* 주문서 양식 설계 모달 */}
      {createdPolicy && (
        <OrderFormBuilder
          visible={showOrderFormModal}
          onClose={handleOrderFormModalClose}
          policyId={createdPolicy.id}
          policyTitle={createdPolicy.title}
        />
      )}
    </>
  );
};

export default PolicyCreateForm;
