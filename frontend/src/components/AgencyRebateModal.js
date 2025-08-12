import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, Select, Button, Table, message, Spin } from 'antd';
import { get, post } from '../services/api';
import './AgencyRebateModal.css';

const { Option } = Select;

const AgencyRebateModal = ({ visible, onClose }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [exposedPolicies, setExposedPolicies] = useState([]);
  const [retailCompanies, setRetailCompanies] = useState([]);
  const [existingRebates, setExistingRebates] = useState([]);

  useEffect(() => {
    if (visible) {
      fetchData();
    }
  }, [visible]);

  const fetchData = async () => {
    setLoading(true);
    try {
      // 노출된 정책과 판매점 목록 가져오기
      const response = await get('policies/agency/rebate/');
      setExposedPolicies(response.exposed_policies || []);
      setRetailCompanies(response.retail_companies || []);
      setExistingRebates(response.existing_rebates || []);
    } catch (error) {
      message.error('데이터를 불러오는데 실패했습니다.');
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      await post('policies/agency/rebate/', {
        policy_exposure: values.policy_exposure,
        retail_company: values.retail_company,
        rebate_amount: values.rebate_amount
      });

      message.success('리베이트가 설정되었습니다.');
      form.resetFields();
      fetchData(); // 데이터 새로고침
    } catch (error) {
      if (error.errorFields) {
        message.error('필수 입력 항목을 확인해주세요.');
      } else {
        message.error('리베이트 설정에 실패했습니다.');
      }
      console.error('Error saving rebate:', error);
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      title: '정책명',
      dataIndex: 'policy_title',
      key: 'policy_title',
      render: (text, record) => record.policy_exposure?.policy?.title || text
    },
    {
      title: '판매점',
      dataIndex: 'retail_company_name',
      key: 'retail_company_name',
      render: (text, record) => record.retail_company?.name || text
    },
    {
      title: '리베이트 금액',
      dataIndex: 'rebate_amount',
      key: 'rebate_amount',
      render: (amount) => amount ? `${amount.toLocaleString()}원` : '-'
    },
    {
      title: '설정일',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => date ? new Date(date).toLocaleDateString() : '-'
    }
  ];

  return (
    <Modal
      title="협력사 리베이트 설정"
      visible={visible}
      onCancel={onClose}
      width={800}
      footer={null}
    >
      <div className="rebate-modal-content">
        {loading ? (
          <div className="loading-container">
            <Spin size="large" />
          </div>
        ) : (
          <>
            {/* 리베이트 설정 폼 */}
            <div className="rebate-form-section">
              <h3>새 리베이트 설정</h3>
              <Form form={form} layout="vertical" onFinish={handleSave}>
                <div className="form-row">
                  <Form.Item
                    name="policy_exposure"
                    label="정책"
                    rules={[{ required: true, message: '정책을 선택하세요' }]}
                    style={{ flex: 1 }}
                  >
                    <Select placeholder="정책을 선택하세요">
                      {exposedPolicies.map(policy => (
                        <Option key={policy.id} value={policy.id}>
                          {policy.policy.title}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>

                  <Form.Item
                    name="retail_company"
                    label="판매점"
                    rules={[{ required: true, message: '판매점을 선택하세요' }]}
                    style={{ flex: 1 }}
                  >
                    <Select placeholder="판매점을 선택하세요">
                      {retailCompanies.map(company => (
                        <Option key={company.id} value={company.id}>
                          {company.name}
                        </Option>
                      ))}
                    </Select>
                  </Form.Item>
                </div>

                <Form.Item
                  name="rebate_amount"
                  label="리베이트 금액"
                  rules={[{ required: true, message: '리베이트 금액을 입력하세요' }]}
                >
                  <Input 
                    placeholder="리베이트 금액을 입력하세요" 
                    suffix="원"
                    type="number"
                  />
                </Form.Item>

                <Form.Item>
                  <Button 
                    type="primary" 
                    htmlType="submit"
                    loading={saving}
                    style={{ width: '100%' }}
                  >
                    리베이트 설정
                  </Button>
                </Form.Item>
              </Form>
            </div>

            {/* 기존 리베이트 목록 */}
            <div className="existing-rebates-section">
              <h3>설정된 리베이트 목록</h3>
              <Table
                columns={columns}
                dataSource={existingRebates}
                rowKey="id"
                pagination={false}
                size="small"
                className="rebates-table"
              />
            </div>
          </>
        )}
      </div>
    </Modal>
  );
};

export default AgencyRebateModal;
