/**
 * 정책 생성 모달
 * 새로운 정책을 생성하는 다이얼로그
 */

import React, { useState } from 'react';
import { Form, Input, Select, Switch, message } from 'antd';
import CustomModal from '../common/CustomModal';
import { policyAPI, handleAPIError } from '../../services/api';

const { Option } = Select;
const { TextArea } = Input;

const PolicyCreateModal = ({ open, onCancel, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const policyData = {
        title: values.title,
        description: values.description || '',
        form_type: values.form_type,
        carrier: values.carrier,
        type: values.type,
        status: 'draft', // 기본값은 초안
        expose: values.expose !== undefined ? values.expose : true,
        premium_market_expose: values.premium_market_expose !== undefined ? values.premium_market_expose : false,
        contract_period: values.contract_period,
        // 리베이트는 나중에 별도로 설정
        rebate_agency: 0,
        rebate_retail: 0,
      };

      const result = await policyAPI.createPolicy(policyData);
      
      message.success('정책이 성공적으로 생성되었습니다.');
      form.resetFields();
      onSuccess?.(result);
      onCancel();

    } catch (error) {
      console.error('정책 생성 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <CustomModal
      title="새 정책 생성"
      open={open}
      onCancel={handleCancel}
      onOk={handleOk}
      loading={loading}
      width={600}
      okText="생성"
      cancelText="취소"
    >
      <Form
        form={form}
        layout="vertical"
        requiredMark={false}
        initialValues={{
          form_type: 'general',
          carrier: 'all',
          type: 'mobile',
          expose: true,
          premium_market_expose: false,
          contract_period: 24,
        }}
      >
        <Form.Item
          name="title"
          label="정책명"
          rules={[
            { required: true, message: '정책명을 입력해주세요.' },
            { min: 2, message: '정책명은 최소 2자 이상이어야 합니다.' },
            { max: 100, message: '정책명은 최대 100자까지 입력 가능합니다.' },
          ]}
        >
          <Input placeholder="정책명을 입력하세요" />
        </Form.Item>

        <Form.Item
          name="description"
          label="정책 설명"
          rules={[
            { max: 500, message: '설명은 최대 500자까지 입력 가능합니다.' },
          ]}
        >
          <TextArea 
            rows={3} 
            placeholder="정책에 대한 설명을 입력하세요 (선택사항)"
          />
        </Form.Item>

        <Form.Item
          name="form_type"
          label="신청서 타입"
          rules={[{ required: true, message: '신청서 타입을 선택해주세요.' }]}
        >
          <Select placeholder="신청서 타입 선택">
            <Option value="general">일반 신청서</Option>
            <Option value="premium">프리미엄 신청서</Option>
            <Option value="enterprise">기업 신청서</Option>
            <Option value="student">학생 신청서</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="carrier"
          label="통신사"
          rules={[{ required: true, message: '통신사를 선택해주세요.' }]}
        >
          <Select placeholder="통신사 선택">
            <Option value="all">전체 통신사</Option>
            <Option value="skt">SKT</Option>
            <Option value="kt">KT</Option>
            <Option value="lg">LG U+</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="type"
          label="상품 타입"
          rules={[{ required: true, message: '상품 타입을 선택해주세요.' }]}
        >
          <Select placeholder="상품 타입 선택">
            <Option value="mobile">모바일</Option>
            <Option value="internet">인터넷</Option>
            <Option value="tv">TV</Option>
            <Option value="combo">결합상품</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="contract_period"
          label="기본 계약기간 (개월)"
          rules={[{ required: true, message: '계약기간을 선택해주세요.' }]}
        >
          <Select placeholder="계약기간 선택">
            <Option value={3}>3개월</Option>
            <Option value={6}>6개월</Option>
            <Option value={9}>9개월</Option>
            <Option value={12}>12개월</Option>
            <Option value={24}>24개월</Option>
            <Option value={36}>36개월</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="expose"
          label="일반 노출"
          valuePropName="checked"
        >
          <Switch />
          <span style={{ marginLeft: 8, color: '#8c8c8c' }}>
            일반 업체에게 이 정책을 노출할지 여부
          </span>
        </Form.Item>

        <Form.Item
          name="premium_market_expose"
          label="프리미엄 마켓 노출"
          valuePropName="checked"
        >
          <Switch />
          <span style={{ marginLeft: 8, color: '#8c8c8c' }}>
            프리미엄 마켓에 이 정책을 노출할지 여부
          </span>
        </Form.Item>
      </Form>

      <div style={{ 
        marginTop: 16, 
        padding: 12, 
        background: '#f6ffed', 
        border: '1px solid #b7eb8f',
        borderRadius: 4,
        fontSize: 13,
        color: '#52c41a'
      }}>
        💡 정책 생성 후 다음 작업이 자동으로 진행됩니다:
        <ul style={{ margin: '4px 0 0 16px', paddingLeft: 0 }}>
          <li>기본 주문서 양식 생성</li>
          <li>리베이트 매트릭스 템플릿 생성</li>
          <li>HTML 콘텐츠 자동 생성</li>
        </ul>
      </div>
    </CustomModal>
  );
};

export default PolicyCreateModal;

