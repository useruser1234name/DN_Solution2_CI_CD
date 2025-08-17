/**
 * 업체 배정 모달
 * 정책에 업체를 배정하거나 해제하는 다이얼로그
 */

import React, { useState, useEffect } from 'react';
import { 
  Form, 
  Select, 
  InputNumber, 
  Switch, 
  message, 
  Table, 
  Button, 
  Space,
  Tag,
  Popconfirm,
  Alert,
  Divider
} from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import CustomModal from '../common/CustomModal';
import { policyAPI, companyAPI, handleAPIError } from '../../services/api';

const { Option } = Select;

const CompanyAssignmentModal = ({ 
  open, 
  onCancel, 
  onSuccess, 
  policyId, 
  policyTitle 
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [availableCompanies, setAvailableCompanies] = useState([]);
  const [assignedCompanies, setAssignedCompanies] = useState([]);
  const [loadingData, setLoadingData] = useState(false);

  // 데이터 로드
  useEffect(() => {
    if (open && policyId) {
      loadData();
    }
  }, [open, policyId]);

  const loadData = async () => {
    setLoadingData(true);
    try {
      const [availableResponse, assignedResponse] = await Promise.all([
        companyAPI.getCompaniesForAssignment(),
        policyAPI.getAssignedCompanies(policyId)
      ]);

      setAvailableCompanies(availableResponse || []);
      setAssignedCompanies(assignedResponse || []);
    } catch (error) {
      console.error('데이터 로드 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoadingData(false);
    }
  };

  // 업체 배정
  const handleAssignCompanies = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const assignmentData = {
        company_ids: values.company_ids,
        custom_rebate: values.custom_rebate || null,
        expose_to_child: values.expose_to_child !== undefined ? values.expose_to_child : true,
      };

      await policyAPI.assignCompanies(policyId, assignmentData);
      
      message.success(`${values.company_ids.length}개 업체가 배정되었습니다.`);
      form.resetFields();
      await loadData(); // 데이터 새로고침
      onSuccess?.();

    } catch (error) {
      console.error('업체 배정 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  };

  // 업체 배정 해제
  const handleUnassignCompany = async (companyId, companyName) => {
    try {
      setLoading(true);
      await policyAPI.unassignCompanies(policyId, [companyId]);
      
      message.success(`${companyName}의 배정이 해제되었습니다.`);
      await loadData(); // 데이터 새로고침
      onSuccess?.();

    } catch (error) {
      console.error('업체 배정 해제 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  };

  // 배정 가능한 업체 필터링 (이미 배정된 업체 제외)
  const getAvailableOptions = () => {
    const assignedCompanyIds = assignedCompanies.map(item => item.company);
    return availableCompanies.filter(company => 
      !assignedCompanyIds.includes(company.id)
    );
  };

  // 배정된 업체 테이블 컬럼
  const assignedColumns = [
    {
      title: '업체명',
      dataIndex: 'company_name',
      key: 'company_name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <div style={{ fontSize: 12, color: '#8c8c8c' }}>
            {record.company_code}
          </div>
        </div>
      ),
    },
    {
      title: '업체 타입',
      dataIndex: 'company_type_display',
      key: 'company_type_display',
      render: (text, record) => {
        const colors = {
          agency: 'blue',
          retail: 'green',
          headquarters: 'red',
        };
        return <Tag color={colors[record.company_type]}>{text}</Tag>;
      },
    },
    {
      title: '사용자 정의 리베이트',
      dataIndex: 'custom_rebate',
      key: 'custom_rebate',
      render: (rebate) => rebate ? `${rebate.toLocaleString()}원` : '-',
    },
    {
      title: '하위 노출',
      dataIndex: 'expose_to_child',
      key: 'expose_to_child',
      render: (expose) => expose ? '✓' : '✗',
    },
    {
      title: '배정일시',
      dataIndex: 'assigned_at',
      key: 'assigned_at',
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: '배정자',
      dataIndex: 'assigned_by_username',
      key: 'assigned_by_username',
    },
    {
      title: '액션',
      key: 'action',
      render: (_, record) => (
        <Popconfirm
          title="배정 해제"
          description={`${record.company_name}의 배정을 해제하시겠습니까?`}
          onConfirm={() => handleUnassignCompany(record.company, record.company_name)}
          okText="해제"
          cancelText="취소"
        >
          <Button 
            type="text" 
            danger 
            icon={<DeleteOutlined />}
            loading={loading}
          >
            해제
          </Button>
        </Popconfirm>
      ),
    },
  ];

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <CustomModal
      title={`업체 배정 관리 - ${policyTitle}`}
      open={open}
      onCancel={handleCancel}
      width={1000}
      customFooter
      footer={[
        <Button key="cancel" onClick={handleCancel}>
          닫기
        </Button>,
      ]}
    >
      <div style={{ maxHeight: '70vh', overflowY: 'auto' }}>
        {/* 새 업체 배정 폼 */}
        <Alert
          message="업체 배정"
          description="선택한 업체들에게 이 정책을 배정합니다. 사용자 정의 리베이트를 설정하지 않으면 기본 리베이트가 적용됩니다."
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
        />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleAssignCompanies}
          initialValues={{
            expose_to_child: true,
          }}
        >
          <Form.Item
            name="company_ids"
            label="배정할 업체"
            rules={[{ required: true, message: '배정할 업체를 선택해주세요.' }]}
          >
            <Select
              mode="multiple"
              placeholder="업체를 선택하세요"
              loading={loadingData}
              showSearch
              filterOption={(input, option) =>
                option.children.toLowerCase().includes(input.toLowerCase())
              }
            >
              {getAvailableOptions().map(company => (
                <Option key={company.id} value={company.id}>
                  {company.name} ({company.type_display})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="custom_rebate"
            label="사용자 정의 리베이트 (선택사항)"
            help="입력하지 않으면 기본 리베이트가 적용됩니다."
          >
            <InputNumber
              placeholder="리베이트 금액"
              style={{ width: '100%' }}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value.replace(/\$\s?|(,*)/g, '')}
              min={0}
              suffix="원"
            />
          </Form.Item>

          <Form.Item
            name="expose_to_child"
            label="하위 업체 노출"
            valuePropName="checked"
          >
            <Switch />
            <span style={{ marginLeft: 8, color: '#8c8c8c' }}>
              배정받은 업체의 하위 업체들도 이 정책을 볼 수 있도록 할지 여부
            </span>
          </Form.Item>

          <Form.Item>
            <Button 
              type="primary" 
              htmlType="submit" 
              loading={loading}
              icon={<PlusOutlined />}
            >
              업체 배정
            </Button>
          </Form.Item>
        </Form>

        <Divider />

        {/* 현재 배정된 업체 목록 */}
        <div style={{ marginTop: 24 }}>
          <h4>현재 배정된 업체 ({assignedCompanies.length}개)</h4>
          <Table
            columns={assignedColumns}
            dataSource={assignedCompanies}
            rowKey="id"
            loading={loadingData || loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: false,
              showQuickJumper: false,
            }}
            locale={{
              emptyText: '배정된 업체가 없습니다.',
            }}
            size="small"
          />
        </div>
      </div>
    </CustomModal>
  );
};

export default CompanyAssignmentModal;

