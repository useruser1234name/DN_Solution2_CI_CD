/**
 * 사용자 승인 관리 모달
 * 업체별 사용자 승인/거부 및 관리 기능
 */

import React, { useState, useEffect } from 'react';
import { 
  Table, 
  Button, 
  Space, 
  Tag, 
  message, 
  Popconfirm,
  Input,
  Select,
  Badge,
  Avatar,
  Descriptions,
  Tabs,
  Alert
} from 'antd';
import { 
  UserOutlined,
  CheckOutlined,
  CloseOutlined,
  SearchOutlined,
  ReloadOutlined,
  MailOutlined,
  PhoneOutlined,
  CalendarOutlined
} from '@ant-design/icons';
import CustomModal from '../common/CustomModal';
import { companyAPI, handleAPIError } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './UserManagementModal.css';

const { Search } = Input;
const { Option } = Select;
const { TabPane } = Tabs;

const UserManagementModal = ({ open, onCancel, onSuccess, company }) => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [activeTab, setActiveTab] = useState('pending');
  
  const { hasPermission, user: currentUser } = useAuth();

  useEffect(() => {
    if (open && company) {
      loadUsers();
    }
  }, [open, company]);

  // 사용자 목록 로드
  const loadUsers = async () => {
    setLoading(true);
    try {
      const response = await companyAPI.getCompanyUsers({
        company_id: company.id,
      });
      setUsers(response.results || response || []);
    } catch (error) {
      console.error('사용자 목록 로드 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  };

  // 사용자 승인
  const handleApproveUser = async (userId, username) => {
    setActionLoading(prev => ({ ...prev, [userId]: true }));
    try {
      await companyAPI.approveUser(userId);
      message.success(`${username} 사용자가 승인되었습니다.`);
      loadUsers();
      onSuccess?.();
    } catch (error) {
      console.error('사용자 승인 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: false }));
    }
  };

  // 사용자 거부
  const handleRejectUser = async (userId, username) => {
    setActionLoading(prev => ({ ...prev, [userId]: true }));
    try {
      await companyAPI.rejectUser(userId);
      message.success(`${username} 사용자가 거부되었습니다.`);
      loadUsers();
      onSuccess?.();
    } catch (error) {
      console.error('사용자 거부 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: false }));
    }
  };

  // 필터링된 사용자 목록
  const getFilteredUsers = () => {
    let filtered = users;

    // 탭별 필터링
    switch (activeTab) {
      case 'pending':
        filtered = filtered.filter(user => user.status === 'pending');
        break;
      case 'approved':
        filtered = filtered.filter(user => user.status === 'approved' || user.is_approved);
        break;
      case 'rejected':
        filtered = filtered.filter(user => user.status === 'rejected');
        break;
      case 'all':
      default:
        break;
    }

    // 검색 필터링
    if (searchText) {
      filtered = filtered.filter(user => 
        user.username?.toLowerCase().includes(searchText.toLowerCase()) ||
        user.django_user?.email?.toLowerCase().includes(searchText.toLowerCase()) ||
        user.django_user?.first_name?.toLowerCase().includes(searchText.toLowerCase()) ||
        user.django_user?.last_name?.toLowerCase().includes(searchText.toLowerCase())
      );
    }

    // 상태 필터링
    if (statusFilter) {
      filtered = filtered.filter(user => user.status === statusFilter);
    }

    return filtered;
  };

  // 사용자 통계
  const getUserStats = () => {
    const pending = users.filter(user => user.status === 'pending').length;
    const approved = users.filter(user => user.status === 'approved' || user.is_approved).length;
    const rejected = users.filter(user => user.status === 'rejected').length;
    
    return { pending, approved, rejected, total: users.length };
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: '사용자',
      key: 'user',
      render: (_, record) => (
        <div className="user-info">
          <Avatar 
            icon={<UserOutlined />} 
            size="small"
            style={{ backgroundColor: '#1890ff', marginRight: 8 }}
          />
          <div>
            <div className="username">{record.username}</div>
            {record.django_user?.email && (
              <div className="email">
                <MailOutlined style={{ marginRight: 4 }} />
                {record.django_user.email}
              </div>
            )}
          </div>
        </div>
      ),
    },
    {
      title: '역할',
      dataIndex: 'role',
      key: 'role',
      render: (role) => {
        const colors = {
          admin: 'red',
          staff: 'blue',
        };
        const labels = {
          admin: '관리자',
          staff: '직원',
        };
        return <Tag color={colors[role]}>{labels[role] || role}</Tag>;
      },
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      render: (status, record) => {
        // 이전 버전 호환성
        const actualStatus = status || (record.is_approved ? 'approved' : 'pending');
        
        const configs = {
          pending: { color: 'warning', text: '승인 대기' },
          approved: { color: 'success', text: '승인됨' },
          rejected: { color: 'error', text: '거부됨' },
        };
        
        const config = configs[actualStatus] || { color: 'default', text: '알 수 없음' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '신청일',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date) => (
        <div className="date-info">
          <CalendarOutlined style={{ marginRight: 4 }} />
          {new Date(date).toLocaleDateString()}
        </div>
      ),
    },
    {
      title: '마지막 로그인',
      dataIndex: 'last_login',
      key: 'last_login',
      render: (date) => date ? new Date(date).toLocaleString() : '-',
    },
  ];

  // 액션 컬럼 (승인 대기 탭에서만 표시)
  if (activeTab === 'pending' && hasPermission('company.approve_user')) {
    columns.push({
      title: '액션',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Popconfirm
            title="사용자 승인"
            description={`${record.username} 사용자를 승인하시겠습니까?`}
            onConfirm={() => handleApproveUser(record.id, record.username)}
            okText="승인"
            cancelText="취소"
          >
            <Button
              type="primary"
              icon={<CheckOutlined />}
              size="small"
              loading={actionLoading[record.id]}
            >
              승인
            </Button>
          </Popconfirm>
          
          <Popconfirm
            title="사용자 거부"
            description={`${record.username} 사용자를 거부하시겠습니까?`}
            onConfirm={() => handleRejectUser(record.id, record.username)}
            okText="거부"
            cancelText="취소"
            okType="danger"
          >
            <Button
              danger
              icon={<CloseOutlined />}
              size="small"
              loading={actionLoading[record.id]}
            >
              거부
            </Button>
          </Popconfirm>
        </Space>
      ),
    });
  }

  const stats = getUserStats();
  const filteredUsers = getFilteredUsers();

  const handleCancel = () => {
    setSearchText('');
    setStatusFilter('');
    setActiveTab('pending');
    onCancel();
  };

  return (
    <CustomModal
      title={`사용자 관리 - ${company?.name}`}
      open={open}
      onCancel={handleCancel}
      width={1000}
      customFooter
      footer={[
        <Button key="close" onClick={handleCancel}>
          닫기
        </Button>,
        <Button 
          key="refresh" 
          icon={<ReloadOutlined />} 
          onClick={loadUsers}
          loading={loading}
        >
          새로고침
        </Button>,
      ]}
      className="user-management-modal"
    >
      {/* 업체 정보 */}
      <Descriptions 
        size="small" 
        column={3} 
        style={{ marginBottom: 16 }}
        bordered
      >
        <Descriptions.Item label="업체명">{company?.name}</Descriptions.Item>
        <Descriptions.Item label="업체코드">{company?.code}</Descriptions.Item>
        <Descriptions.Item label="타입">
          <Tag color={company?.type === 'headquarters' ? 'red' : 
                     company?.type === 'agency' ? 'blue' : 'green'}>
            {company?.type === 'headquarters' ? '본사' : 
             company?.type === 'agency' ? '협력사' : '판매점'}
          </Tag>
        </Descriptions.Item>
      </Descriptions>

      {/* 통계 알림 */}
      {stats.pending > 0 && (
        <Alert
          message={`승인 대기 중인 사용자가 ${stats.pending}명 있습니다.`}
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 검색 및 필터 */}
      <div className="filter-section">
        <Search
          placeholder="사용자명 또는 이메일로 검색"
          allowClear
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ width: 300, marginRight: 16 }}
        />
      </div>

      {/* 탭 */}
      <Tabs 
        activeKey={activeTab} 
        onChange={setActiveTab}
        style={{ marginTop: 16 }}
      >
        <TabPane 
          tab={
            <Badge count={stats.pending} size="small">
              승인 대기
            </Badge>
          } 
          key="pending"
        />
        <TabPane 
          tab={
            <Badge count={stats.approved} size="small" style={{ backgroundColor: '#52c41a' }}>
              승인됨
            </Badge>
          } 
          key="approved"
        />
        <TabPane 
          tab={
            <Badge count={stats.rejected} size="small" style={{ backgroundColor: '#ff4d4f' }}>
              거부됨
            </Badge>
          } 
          key="rejected"
        />
        <TabPane 
          tab={`전체 (${stats.total})`}
          key="all"
        />
      </Tabs>

      {/* 사용자 테이블 */}
      <Table
        columns={columns}
        dataSource={filteredUsers}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => 
            `${range[0]}-${range[1]} / 총 ${total}명`,
        }}
        locale={{
          emptyText: activeTab === 'pending' ? 
            '승인 대기 중인 사용자가 없습니다.' :
            '사용자가 없습니다.',
        }}
        size="small"
      />
    </CustomModal>
  );
};

export default UserManagementModal;


