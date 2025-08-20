import React, { useState, useEffect } from 'react';
import { 
  Form, 
  Input, 
  InputNumber, 
  Select, 
  Button, 
  Card, 
  Typography, 
  Row, 
  Col, 
  Space,
  Divider,
  Switch,
  message 
} from 'antd';
import { SaveOutlined, PlusOutlined } from '@ant-design/icons';
import CommissionGradeInput from '../components/CommissionGradeInput';

const { Title, Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

/**
 * 정책 생성/수정 폼 컴포넌트
 */
const PolicyForm = ({ 
  initialValues = null, 
  onSubmit, 
  loading = false, 
  mode = 'create' // 'create' | 'edit'
}) => {
  const [form] = Form.useForm();
  const [commissionGrades, setCommissionGrades] = useState([]);

  useEffect(() => {
    if (initialValues) {
      form.setFieldsValue(initialValues);
      // 기존 수수료 그레이드 설정 로드
      if (initialValues.commission_grades) {
        setCommissionGrades(initialValues.commission_grades);
      }
    }
  }, [initialValues, form]);

  // 폼 제출 처리
  const handleSubmit = async (values) => {
    try {
      // 수수료 그레이드 데이터 추가
      const formData = {
        ...values,
        commission_grades: commissionGrades
      };

      console.log('Policy Form Data:', formData);

      if (onSubmit) {
        await onSubmit(formData);
      }
    } catch (error) {
      console.error('Form submission error:', error);
      message.error('정책 저장 중 오류가 발생했습니다.');
    }
  };

  // 수수료 그레이드 변경 처리
  const handleCommissionGradesChange = (grades) => {
    setCommissionGrades(grades);
    // 폼 필드에도 반영 (선택사항)
    form.setFieldsValue({ commission_grades: grades });
  };

  return (
    <div className="policy-form">
      <Card>
        <Title level={3}>
          {mode === 'create' ? '새 정책 생성' : '정책 수정'}
        </Title>
        
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            form_type: 'general',
            type: 'normal',
            status: 'draft',
            carrier: 'all',
            join_type: 'all',
            contract_period: 'all',
            commission_agency: 0,
            commission_retail: 0,
            grade_period_type: 'monthly',
            expose: true,
            premium_market_expose: false,
            commission_grades: []
          }}
        >
          {/* 기본 정보 섹션 */}
          <Card title="기본 정보" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="title"
                  label="정책 제목"
                  rules={[
                    { required: true, message: '정책 제목을 입력해주세요' },
                    { min: 2, message: '제목은 최소 2자 이상이어야 합니다' }
                  ]}
                >
                  <Input placeholder="정책 제목을 입력하세요" maxLength={200} />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="form_type"
                  label="신청서 타입"
                  rules={[{ required: true, message: '신청서 타입을 선택해주세요' }]}
                >
                  <Select>
                    <Option value="general">일반 신청서</Option>
                    <Option value="link">링크 신청서</Option>
                    <Option value="offline">오프라인 신청서</Option>
                    <Option value="egg">에그 신청서</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="description"
              label="정책 설명"
              rules={[
                { required: true, message: '정책 설명을 입력해주세요' },
                { min: 10, message: '설명은 최소 10자 이상이어야 합니다' }
              ]}
            >
              <TextArea 
                rows={4} 
                placeholder="정책에 대한 상세한 설명을 입력하세요"
                maxLength={1000}
                showCount
              />
            </Form.Item>

            <Row gutter={16}>
              <Col span={8}>
                <Form.Item name="type" label="정책 타입">
                  <Select>
                    <Option value="normal">일반</Option>
                    <Option value="special">특별</Option>
                    <Option value="event">이벤트</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="status" label="정책 상태">
                  <Select>
                    <Option value="draft">초안</Option>
                    <Option value="active">활성</Option>
                    <Option value="inactive">비활성</Option>
                    <Option value="expired">만료</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item name="carrier" label="통신사">
                  <Select>
                    <Option value="all">전체</Option>
                    <Option value="skt">SKT</Option>
                    <Option value="kt">KT</Option>
                    <Option value="lg">LG U+</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="join_type" label="가입유형">
                  <Select>
                    <Option value="all">전체</Option>
                    <Option value="number_transfer">번호이동</Option>
                    <Option value="device_change">기기변경</Option>
                    <Option value="new_subscription">신규가입</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="contract_period" label="가입기간">
                  <Select>
                    <Option value="all">전체</Option>
                    <Option value="12">12개월</Option>
                    <Option value="24">24개월</Option>
                    <Option value="36">36개월</Option>
                  </Select>
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 기본 수수료 설정 섹션 */}
          <Card title="기본 수수료 설정" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="commission_agency"
                  label="대리점 수수료"
                  rules={[{ required: true, message: '대리점 수수료를 입력해주세요' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    max={999999}
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value.replace(/\$\s?|(,*)/g, '')}
                    placeholder="0"
                    addonAfter="원"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="commission_retail"
                  label="판매점 수수료"
                  rules={[{ required: true, message: '판매점 수수료를 입력해주세요' }]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    min={0}
                    max={999999}
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value.replace(/\$\s?|(,*)/g, '')}
                    placeholder="0"
                    addonAfter="원"
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 수수료 그레이드 설정 섹션 */}
          <div style={{ marginBottom: 24 }}>
            <CommissionGradeInput
              value={commissionGrades}
              onChange={handleCommissionGradesChange}
              title="수수료 그레이드 설정"
            />
          </div>

          {/* 그레이드 적용 기간 설정 */}
          <Card title="그레이드 적용 설정" size="small" style={{ marginBottom: 24 }}>
            <Form.Item
              name="grade_period_type"
              label="그레이드 적용 기간"
              tooltip="그레이드 달성을 위한 주문량 집계 기간을 설정합니다"
            >
              <Select>
                <Option value="monthly">월별 (매월 1일 기준 리셋)</Option>
                <Option value="quarterly">분기별 (분기 시작일 기준 리셋)</Option>
                <Option value="yearly">연간 (매년 1월 1일 기준 리셋)</Option>
                <Option value="policy_lifetime">정책 전체 기간 (정책 활성화 이후 누적)</Option>
              </Select>
            </Form.Item>
          </Card>

          {/* 노출 설정 섹션 */}
          <Card title="노출 설정" size="small" style={{ marginBottom: 24 }}>
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item name="expose" label="정책 노출" valuePropName="checked">
                  <Switch 
                    checkedChildren="노출" 
                    unCheckedChildren="비노출"
                    defaultChecked={true}
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="premium_market_expose" label="프리미엄 마켓 노출" valuePropName="checked">
                  <Switch 
                    checkedChildren="노출" 
                    unCheckedChildren="비노출"
                    defaultChecked={false}
                  />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          {/* 히든 필드 - commission_grades */}
          <Form.Item name="commission_grades" style={{ display: 'none' }}>
            <Input type="hidden" />
          </Form.Item>

          {/* 제출 버튼 */}
          <div style={{ textAlign: 'center', marginTop: 32 }}>
            <Space size="middle">
              <Button size="large">
                취소
              </Button>
              <Button 
                type="primary" 
                htmlType="submit" 
                size="large"
                loading={loading}
                icon={<SaveOutlined />}
              >
                {mode === 'create' ? '정책 생성' : '정책 수정'}
              </Button>
            </Space>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default PolicyForm;
