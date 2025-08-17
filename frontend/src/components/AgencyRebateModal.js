import React, { useState, useEffect } from 'react';
import { Modal, Form, InputNumber, Button, Table, message, Spin, Card, Typography } from 'antd';
import { get, post } from '../services/api';
import './AgencyRebateModal.css';

const { Title, Text } = Typography;

const AgencyRebateModal = ({ visible, onCancel, policy }) => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [rebateData, setRebateData] = useState([]);
  const [form] = Form.useForm();

  useEffect(() => {
    if (visible && policy) {
      fetchRebateData();
    }
  }, [visible, policy]);

  const fetchRebateData = async () => {
    setLoading(true);
    try {
      const response = await get('/api/policies/agency/rebate/api/');
      if (response.success) {
        const policyData = response.data.find(item => item.policy_id === policy.id);
        if (policyData) {
          setRebateData(policyData.retail_stores || []);
        }
      } else {
        message.error(response.message || '리베이트 정보를 불러오는데 실패했습니다.');
      }
    } catch (error) {
      console.error('리베이트 데이터 로드 오류:', error);
      message.error('리베이트 정보를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveRebate = async (storeId, rebateAmount) => {
    setSaving(true);
    try {
      const response = await post('/api/policies/agency/rebate/api/', {
        policy_exposure_id: policy.exposure_id, // 정책 노출 ID가 필요
        retail_company_id: storeId,
        rebate_amount: rebateAmount
      });

      if (response.success) {
        message.success(response.message || '리베이트가 설정되었습니다.');
        fetchRebateData(); // 데이터 새로고침
      } else {
        message.error(response.message || '리베이트 설정에 실패했습니다.');
      }
    } catch (error) {
      console.error('리베이트 저장 오류:', error);
      message.error('리베이트 설정 중 오류가 발생했습니다.');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      title: '판매점명',
      dataIndex: 'store_name',
      key: 'store_name',
      width: 200,
    },
    {
      title: '현재 리베이트',
      dataIndex: 'rebate_amount',
      key: 'current_rebate',
      width: 150,
      render: (amount) => amount ? `${amount.toLocaleString()}원` : '미설정',
    },
    {
      title: '새 리베이트 설정',
      key: 'new_rebate',
      render: (_, record) => (
        <Form
          layout="inline"
          onFinish={(values) => handleSaveRebate(record.store_id, values.rebate_amount)}
        >
          <Form.Item
            name="rebate_amount"
            rules={[
              { required: true, message: '리베이트 금액을 입력하세요' },
              { type: 'number', min: 0, message: '0 이상의 금액을 입력하세요' }
            ]}
            initialValue={record.rebate_amount}
          >
            <InputNumber
              placeholder="리베이트 금액"
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value.replace(/\$\s?|(,*)/g, '')}
              style={{ width: 150 }}
            />
          </Form.Item>
          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={saving}
              size="small"
            >
              저장
            </Button>
          </Form.Item>
        </Form>
      ),
    },
  ];

  return (
    <Modal
      title={
        <div>
          <Title level={4} style={{ margin: 0 }}>
            판매점 리베이트 설정
          </Title>
          <Text type="secondary">
            {policy?.title} 정책에 대한 판매점별 리베이트를 설정합니다.
          </Text>
        </div>
      }
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="close" onClick={onCancel}>
          닫기
        </Button>
      ]}
      width={800}
      className="agency-rebate-modal"
    >
      <Spin spinning={loading}>
        <Card className="rebate-info-card">
          <div className="policy-info">
            <Text strong>정책명: </Text>
            <Text>{policy?.title}</Text>
          </div>
          <div className="default-rebate-info">
            <Text strong>기본 판매점 리베이트: </Text>
            <Text>{policy?.rebate_retail?.toLocaleString()}원</Text>
          </div>
        </Card>

        <div className="rebate-table-container">
          <Title level={5}>판매점별 리베이트 설정</Title>
          <Table
            columns={columns}
            dataSource={rebateData}
            rowKey="store_id"
            pagination={false}
            size="middle"
            locale={{
              emptyText: '설정 가능한 판매점이 없습니다.'
            }}
          />
        </div>

        <div className="rebate-help">
          <Text type="secondary">
            • 리베이트를 설정하지 않으면 기본값이 적용됩니다.<br/>
            • 설정된 리베이트는 해당 판매점의 주문 승인 시 자동으로 정산에 반영됩니다.
          </Text>
        </div>
      </Spin>
    </Modal>
  );
};

export default AgencyRebateModal;