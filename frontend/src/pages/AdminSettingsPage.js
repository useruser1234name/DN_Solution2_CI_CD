import React, { useState } from 'react';
import { Card, Tabs, Typography, Space, Divider } from 'antd';
import { SettingOutlined, ShopOutlined, MobileOutlined, DollarOutlined } from '@ant-design/icons';
import CarrierPlanSelector from '../components/common/CarrierPlanSelector';
import DeviceSelector from '../components/common/DeviceSelector';
import OrderFormBuilder from '../components/OrderFormBuilder';
import CarrierPlanManagementPage from './CarrierPlanManagementPage';
import './AdminSettingsPage.css';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

const AdminSettingsPage = () => {
  const [activeTab, setActiveTab] = useState('carrier-plans');

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
        <div className="carrier-plan-tab-content">
          <CarrierPlanManagementPage />
        </div>
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
    </div>
  );
};

export default AdminSettingsPage;

