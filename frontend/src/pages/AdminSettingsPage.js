import React, { useState } from 'react';
import { Card, Tabs, Typography, Space, Divider } from 'antd';
import { SettingOutlined, ShopOutlined, MobileOutlined, DollarOutlined } from '@ant-design/icons';
import DeviceSelector from '../components/common/DeviceSelector';
import OrderFormBuilder from '../components/OrderFormBuilder';
import './AdminSettingsPage.css';

// 요금제 관리 컴포넌트 import
import { 
  Table, 
  Button, 
  Modal, 
  Form, 
  Input, 
  Select, 
  InputNumber, 
  message, 
  Popconfirm,
  Pagination
} from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import { get, post, put, del } from '../services/api';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

const AdminSettingsPage = () => {
  const [activeTab, setActiveTab] = useState('carrier-plans');
  
  // 요금제 관리 상태 변수
  const [loading, setLoading] = useState(false);
  const [carrierPlans, setCarrierPlans] = useState([]);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [activeCarrier, setActiveCarrier] = useState('all');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // 요금제 로드
  // 페이지네이션을 위한 데이터 처리 함수
  const getPaginatedData = (data, current, pageSize) => {
    const startIndex = (current - 1) * pageSize;
    const endIndex = startIndex + pageSize;
    return data.slice(startIndex, endIndex);
  };

  const loadCarrierPlans = async (carrier = 'all') => {
    setLoading(true);
    try {
      let endpoint = '/policies/carrier-plans/';
      if (carrier !== 'all') {
        endpoint += `?carrier=${carrier}`;
      }
      
      console.log('[CarrierPlanManagement] API 요청 URL:', endpoint);
      
      const response = await get(endpoint);
      
      console.log('[CarrierPlanManagement] API 응답:', response);
      
      // API 응답 처리
      let plansData = [];
      
      if (response.success) {
        // 이중 래핑 처리
        if (response.data?.data && Array.isArray(response.data.data)) {
          plansData = response.data.data;
        } 
        // 단일 래핑 처리
        else if (Array.isArray(response.data)) {
          plansData = response.data;
        }
        // 페이지네이션 처리
        else if (response.data?.results && Array.isArray(response.data.results)) {
          plansData = response.data.results;
        }
        
        console.log('[CarrierPlanManagement] 최종 처리된 요금제 데이터:', plansData);
        
        // 전체 데이터 저장 (페이지네이션을 위해)
        setCarrierPlans(plansData);
        setPagination(prev => ({
          ...prev,
          total: plansData.length
        }));
      } else {
        message.error('요금제 정보를 불러오는데 실패했습니다.');
      }
    } catch (error) {
      console.error('[CarrierPlanManagement] 요금제 로드 오류:', error);
      message.error('요금제 정보를 불러오는 중 오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  // 컴포넌트 마운트 시 요금제 로드
  React.useEffect(() => {
    loadCarrierPlans(activeCarrier);
  }, [activeCarrier]);

  // 통신사 변경 핸들러
  const handleCarrierChange = (carrier) => {
    setActiveCarrier(carrier);
  };

  // 요금제 추가 모달 열기
  const showAddModal = () => {
    form.resetFields();
    if (activeCarrier !== 'all') {
      form.setFieldsValue({ carrier: activeCarrier });
    }
    setModalVisible(true);
  };

  // 모달 닫기
  const handleCancel = () => {
    setModalVisible(false);
  };

  // 요금제 추가
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      
      // 새 요금제 추가
      const response = await post('/policies/carrier-plans/', values);
      if (response.success) {
        message.success('새 요금제가 성공적으로 추가되었습니다.');
        loadCarrierPlans(activeCarrier);
        setModalVisible(false);
      } else {
        message.error('요금제 추가에 실패했습니다.');
      }
    } catch (error) {
      console.error('[CarrierPlanManagement] 요금제 추가 오류:', error);
    }
  };

  // 요금제 삭제
  const handleDelete = async (id) => {
    try {
      const response = await del(`/policies/carrier-plans/${id}/`);
      if (response.success) {
        message.success('요금제가 성공적으로 삭제되었습니다.');
        loadCarrierPlans(activeCarrier);
      } else {
        message.error('요금제 삭제에 실패했습니다.');
      }
    } catch (error) {
      console.error('[CarrierPlanManagement] 요금제 삭제 오류:', error);
      message.error('요금제 삭제 중 오류가 발생했습니다.');
    }
  };

  // 페이지네이션 변경 핸들러 - 페이지 변경 시
  const handlePageChange = (page, pageSize) => {
    setPagination(prev => ({
      ...prev,
      current: page,
      pageSize: pageSize
    }));
  };

  // 페이지 크기 변경 핸들러
  const handlePageSizeChange = (value) => {
    setPagination(prev => ({
      ...prev,
      pageSize: value,
      current: 1 // 페이지 크기 변경 시 첫 페이지로 이동
    }));
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: '통신사',
      dataIndex: 'carrier',
      key: 'carrier',
      render: (carrier) => {
        const carrierMap = {
          'skt': 'SKT',
          'kt': 'KT',
          'lg': 'LG U+'
        };
        return carrierMap[carrier] || carrier;
      }
    },
    {
      title: '요금제명',
      dataIndex: 'plan_name',
      key: 'plan_name',
    },
    {
      title: '요금제 가격',
      dataIndex: 'plan_price',
      key: 'plan_price',
      render: (price) => `${price?.toLocaleString() || 0}원`,
      sorter: (a, b) => a.plan_price - b.plan_price
    },
    {
      title: '설명',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '삭제',
      key: 'action',
      render: (_, record) => (
        <Popconfirm
          title="이 요금제를 삭제하시겠습니까?"
          onConfirm={() => handleDelete(record.id)}
          okText="예"
          cancelText="아니오"
        >
          <Button 
            danger 
            icon={<DeleteOutlined />} 
            size="small"
          >
            삭제
          </Button>
        </Popconfirm>
      ),
    },
  ];

  // 통신사 탭 옵션
  const carrierTabs = [
    { key: 'all', label: '전체 요금제' },
    { key: 'skt', label: 'SKT' },
    { key: 'kt', label: 'KT' },
    { key: 'lg', label: 'LG U+' }
  ];

  const tabItems = [
    {
      key: 'carrier-plans',
      label: (
        <span>
          <ShopOutlined />
          통신사 요금제 관리
        </span>
      ),
      children: (
        <Card title="통신사 요금제 관리" className="settings-card">
          <Text type="secondary" className="card-description">
            통신사별 요금제를 관리하고 새로운 요금제를 추가할 수 있습니다.
          </Text>
          <Divider />
          <div className="carrier-plan-management">
            <div className="card-header">
              <div className="carrier-tabs">
                {carrierTabs.map(tab => (
                  <div 
                    key={tab.key}
                    className={`carrier-tab ${activeCarrier === tab.key ? 'active' : ''}`}
                    onClick={() => handleCarrierChange(tab.key)}
                  >
                    {tab.label}
                  </div>
                ))}
              </div>
              <Button 
                type="primary" 
                icon={<PlusOutlined />}
                onClick={showAddModal}
                className="add-button"
              >
                새 요금제 추가
              </Button>
            </div>

            <Divider style={{ margin: '16px 0' }} />
            
            <div className="table-header">
              <div className="total-count">
                총 {carrierPlans.length}개 요금제
              </div>
              <div className="page-size-selector">
                <Select 
                  value={pagination.pageSize} 
                  onChange={handlePageSizeChange}
                  dropdownMatchSelectWidth={false}
                >
                  <Option value={10}>10 / page</Option>
                  <Option value={20}>20 / page</Option>
                  <Option value={50}>50 / page</Option>
                </Select>
              </div>
            </div>
            
            <div className="table-wrapper">
              <Table 
                columns={columns} 
                dataSource={getPaginatedData(carrierPlans, pagination.current, pagination.pageSize)} 
                rowKey="id"
                loading={loading}
                pagination={false} // 페이지네이션 비활성화
              />
            </div>
            
            {/* 페이지네이션 별도 컨테이너로 분리 */}
            <div className="pagination-container">
              <div className="pagination-wrapper">
                <Pagination
                  total={pagination.total}
                  current={pagination.current}
                  pageSize={pagination.pageSize}
                  onChange={handlePageChange}
                  showSizeChanger={true}
                  pageSizeOptions={['10', '20', '50']}
                  onShowSizeChange={handlePageChange}
                  showTotal={(total, range) => `${range[0]}-${range[1]} / ${total}개 항목`}
                />
              </div>
            </div>
          </div>
        </Card>
      )
    },
    {
      key: 'devices',
      label: (
        <span>
          <MobileOutlined />
          기기 관리
        </span>
      ),
      children: (
        <Card title="기기 모델 및 색상 관리" className="settings-card">
          <Text type="secondary" className="card-description">
            기기 모델과 색상을 관리하고 새로운 기기를 추가할 수 있습니다.
          </Text>
          <Divider />
          <DeviceSelector 
            showAddButton={true}
            showManagement={true}
          />
        </Card>
      )
    },
    {
      key: 'order-form',
      label: (
        <span>
          <SettingOutlined />
          주문서 양식 관리
        </span>
      ),
      children: (
        <Card title="주문서 양식 빌더" className="settings-card">
          <Text type="secondary" className="card-description">
            주문서 양식을 커스터마이징하고 필드를 추가/수정할 수 있습니다.
          </Text>
          <Divider />
          <OrderFormBuilder />
        </Card>
      )
    }
  ];

  return (
    <div className="admin-settings-page">
      <div className="page-header">
        <Title level={2}>
          <SettingOutlined /> 관리자 설정
        </Title>
        <Text type="secondary">
          시스템 전반의 설정을 관리할 수 있습니다.
        </Text>
      </div>

      <div className="settings-content">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          type="card"
          size="large"
          items={tabItems}
        />
      </div>
      
      {/* 요금제 추가 모달 */}
      <Modal
        title="새 요금제 추가"
        open={modalVisible}
        onOk={handleSave}
        onCancel={handleCancel}
        okText="추가"
        cancelText="취소"
        maskClosable={false}
      >
        <Form
          form={form}
          layout="vertical"
        >
          <Form.Item
            name="carrier"
            label="통신사"
            rules={[{ required: true, message: '통신사를 선택하세요' }]}
          >
            <Select placeholder="통신사 선택">
              <Option value="skt">SKT</Option>
              <Option value="kt">KT</Option>
              <Option value="lg">LG U+</Option>
            </Select>
          </Form.Item>
          
          <Form.Item
            name="plan_name"
            label="요금제명"
            rules={[{ required: true, message: '요금제명을 입력하세요' }]}
          >
            <Input placeholder="요금제명 입력" />
          </Form.Item>
          
          <Form.Item
            name="plan_price"
            label="요금제 가격 (원)"
            rules={[{ required: true, message: '요금제 가격을 입력하세요' }]}
          >
            <InputNumber 
              placeholder="가격 입력" 
              min={0}
              formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value.replace(/\$\s?|(,*)/g, '')}
              style={{ width: '100%' }}
            />
          </Form.Item>
          
          <Form.Item
            name="description"
            label="요금제 설명"
          >
            <Input.TextArea 
              placeholder="요금제에 대한 설명을 입력하세요" 
              rows={4}
            />
          </Form.Item>
          
          <Form.Item name="is_active" hidden initialValue={true}>
            <Input type="hidden" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default AdminSettingsPage;

