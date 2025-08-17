/**
 * 주문 관리 페이지
 * 동적 폼 렌더링 + 승인 워크플로우
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Button, 
  Space, 
  Tag, 
  message, 
  Dropdown, 
  Tooltip,
  Modal,
  Badge,
  Card,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  PlusOutlined,
  EyeOutlined,
  EditOutlined,
  CheckOutlined,
  CloseOutlined,
  FileTextOutlined,
  FilterOutlined,
  DownloadOutlined,
  MoreOutlined
} from '@ant-design/icons';

import SearchableTable from '../components/common/SearchableTable';
import DynamicOrderForm from '../components/order/DynamicOrderForm';
import OrderApprovalModal from '../components/order/OrderApprovalModal';
import { orderAPI, policyAPI, handleAPIError } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './OrderManagementPage.css';

const OrderManagementPage = () => {
  // 상태 관리
  const [orders, setOrders] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
  });

  // 검색/필터 상태
  const [searchValue, setSearchValue] = useState('');
  const [filters, setFilters] = useState({
    status: '',
    policy: '',
    date_range: null,
  });

  // 모달 상태
  const [modals, setModals] = useState({
    create: false,
    edit: false,
    approval: false,
    view: false,
  });

  // 선택된 주문/정책 정보
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [selectedPolicy, setSelectedPolicy] = useState(null);

  // 통계 정보
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    approved: 0,
    rejected: 0,
  });

  // 인증 정보
  const { hasPermission, user } = useAuth();

  // 데이터 로드
  const loadOrders = useCallback(async (params = {}) => {
    setLoading(true);
    try {
      const queryParams = {
        page: pagination.current,
        page_size: pagination.pageSize,
        search: searchValue,
        ...filters,
        ...params,
      };

      // 빈 값 제거
      Object.keys(queryParams).forEach(key => {
        if (!queryParams[key]) {
          delete queryParams[key];
        }
      });

      const response = await orderAPI.getOrders(queryParams);
      
      setOrders(response.results || []);
      setPagination(prev => ({
        ...prev,
        total: response.count || 0,
      }));

    } catch (error) {
      console.error('주문 목록 로드 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  }, [pagination.current, pagination.pageSize, searchValue, filters]);

  // 통계 로드
  const loadStats = useCallback(async () => {
    try {
      const response = await orderAPI.getOrderStats();
      if (response.success) {
        setStats(response.data);
      }
    } catch (error) {
      console.error('주문 통계 로드 오류:', error);
    }
  }, []);

  // 정책 목록 로드
  const loadPolicies = useCallback(async () => {
    try {
      const response = await policyAPI.getPolicies({ page_size: 100 });
      setPolicies(response.results || []);
    } catch (error) {
      console.error('정책 목록 로드 오류:', error);
    }
  }, []);

  // 초기 로드
  useEffect(() => {
    loadOrders();
    loadPolicies();
    loadStats();
  }, []);

  // 검색 핸들러
  const handleSearch = (value) => {
    setSearchValue(value);
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  // 필터 변경 핸들러
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPagination(prev => ({ ...prev, current: 1 }));
  };

  // 테이블 변경 핸들러
  const handleTableChange = (paginationInfo, filtersInfo, sorter) => {
    setPagination(prev => ({
      ...prev,
      current: paginationInfo.current,
      pageSize: paginationInfo.pageSize,
    }));
  };

  // 새로고침
  const handleRefresh = () => {
    loadOrders();
  };

  // 모달 제어
  const openModal = (type, order = null, policy = null) => {
    setSelectedOrder(order);
    setSelectedPolicy(policy);
    setModals(prev => ({ ...prev, [type]: true }));
  };

  const closeModal = (type) => {
    setModals(prev => ({ ...prev, [type]: false }));
    setSelectedOrder(null);
    setSelectedPolicy(null);
  };

  // 주문 승인
  const handleApproveOrder = async (orderId) => {
    try {
      await orderAPI.approveOrder(orderId);
      message.success('주문이 승인되었습니다.');
      loadOrders();
      loadStats(); // 통계도 함께 업데이트
    } catch (error) {
      console.error('주문 승인 오류:', error);
      message.error(handleAPIError(error));
    }
  };

  // 주문 거부
  const handleRejectOrder = async (orderId, reason) => {
    try {
      await orderAPI.rejectOrder(orderId, reason);
      message.success('주문이 거부되었습니다.');
      loadOrders();
      loadStats(); // 통계도 함께 업데이트
    } catch (error) {
      console.error('주문 거부 오류:', error);
      message.error(handleAPIError(error));
    }
  };

  // 정책 선택 모달
  const handleCreateOrder = () => {
    if (policies.length === 0) {
      message.error('주문할 수 있는 정책이 없습니다.');
      return;
    }

    // 정책 선택 모달 표시
    Modal.confirm({
      title: '정책 선택',
      content: (
        <div>
          <p>주문서를 작성할 정책을 선택하세요:</p>
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {policies.map(policy => (
              <Card 
                key={policy.id}
                size="small"
                hoverable
                style={{ marginBottom: 8, cursor: 'pointer' }}
                onClick={() => {
                  Modal.destroyAll();
                  openModal('create', null, policy);
                }}
              >
                <div>
                  <div style={{ fontWeight: 500 }}>{policy.title}</div>
                  <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                    {policy.carrier_display} | {policy.form_type_display}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      ),
      okText: '취소',
      cancelText: null,
      onOk: () => {},
    });
  };

  // 액션 메뉴 아이템
  const getActionMenuItems = (record) => {
    const items = [];

    // 상세 보기
    items.push({
      key: 'view',
      icon: <EyeOutlined />,
      label: '상세 보기',
      onClick: () => openModal('view', record),
    });

    // 수정 (본인이 작성한 임시저장/거부된 주문만)
    if (hasPermission('order.edit') && 
        record.created_by_username === user?.username &&
        ['draft', 'rejected'].includes(record.status)) {
      items.push({
        key: 'edit',
        icon: <EditOutlined />,
        label: '수정',
        onClick: () => openModal('edit', record),
      });
    }

    // 승인 처리 (승인 권한이 있고 대기 상태인 경우)
    if (hasPermission('order.approve') && record.status === 'pending') {
      items.push({
        type: 'divider',
      });
      items.push({
        key: 'approve-modal',
        icon: <CheckOutlined />,
        label: '승인 처리',
        onClick: () => openModal('approval', record),
      });
    }

    return items;
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: '주문번호',
      dataIndex: 'order_number',
      key: 'order_number',
      width: 120,
      render: (text) => <code>{text}</code>,
    },
    {
      title: '정책',
      dataIndex: 'policy_title',
      key: 'policy_title',
      width: 200,
      ellipsis: true,
    },
    {
      title: '고객명',
      dataIndex: 'customer_name',
      key: 'customer_name',
      width: 100,
      render: (text) => text || '-',
    },
    {
      title: '상태',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => {
        const configs = {
          draft: { color: 'default', text: '임시저장' },
          pending: { color: 'processing', text: '승인대기' },
          approved: { color: 'success', text: '승인됨' },
          rejected: { color: 'error', text: '거부됨' },
          processing: { color: 'warning', text: '처리중' },
          completed: { color: 'success', text: '완료' },
        };
        const config = configs[status] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '신청자',
      dataIndex: 'created_by_username',
      key: 'created_by_username',
      width: 100,
    },
    {
      title: '신청 업체',
      dataIndex: 'company_name',
      key: 'company_name',
      width: 150,
      ellipsis: true,
    },
    {
      title: '신청일시',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: '액션',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          <Tooltip title="상세보기">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => openModal('view', record)}
              size="small"
            />
          </Tooltip>

          {/* 승인 처리 버튼 (권한이 있고 대기 상태인 경우) */}
          {hasPermission('order.approve') && record.status === 'pending' && (
            <Tooltip title="승인 처리">
              <Button
                type="text"
                icon={<CheckOutlined />}
                onClick={() => openModal('approval', record)}
                size="small"
                style={{ color: '#52c41a' }}
              />
            </Tooltip>
          )}

          {/* 더보기 메뉴 */}
          <Dropdown
            menu={{ items: getActionMenuItems(record) }}
            trigger={['click']}
            placement="bottomRight"
          >
            <Button
              type="text"
              icon={<MoreOutlined />}
              size="small"
            />
          </Dropdown>
        </Space>
      ),
    },
  ];

  // 필터 설정
  const tableFilters = [
    {
      key: 'status',
      type: 'select',
      placeholder: '상태 선택',
      options: [
        { value: 'draft', label: '임시저장' },
        { value: 'pending', label: '승인대기' },
        { value: 'approved', label: '승인됨' },
        { value: 'rejected', label: '거부됨' },
        { value: 'processing', label: '처리중' },
        { value: 'completed', label: '완료' },
      ],
    },
    {
      key: 'policy',
      type: 'select',
      placeholder: '정책 선택',
      options: policies.map(p => ({ value: p.id, label: p.title })),
    },
    {
      key: 'date_range',
      type: 'date',
      startPlaceholder: '시작일',
      endPlaceholder: '종료일',
    },
  ];

  return (
    <div className="order-management-page">
      {/* 통계 카드 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="전체 주문"
              value={stats.total}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="승인 대기"
              value={stats.pending}
              prefix={<Badge status="processing" />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="승인됨"
              value={stats.approved}
              prefix={<CheckOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="거부됨"
              value={stats.rejected}
              prefix={<CloseOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 주문 목록 테이블 */}
      <SearchableTable
        title="주문 관리"
        columns={columns}
        dataSource={orders}
        loading={loading}
        rowKey="id"
        pagination={pagination}
        onChange={handleTableChange}
        searchPlaceholder="주문번호, 고객명, 정책명으로 검색"
        searchValue={searchValue}
        onSearch={handleSearch}
        filters={tableFilters}
        filterValues={filters}
        onFilterChange={handleFilterChange}
        showCreateButton={hasPermission('order.create')}
        createButtonText="주문 생성"
        onCreateClick={handleCreateOrder}
        onRefresh={handleRefresh}
        extraActions={[
          <Button
            key="export"
            icon={<DownloadOutlined />}
            onClick={() => message.info('엑셀 내보내기 기능을 구현 중입니다.')}
          >
            내보내기
          </Button>,
        ]}
      />

      {/* 주문 생성 모달 */}
      {selectedPolicy && (
        <Modal
          title={`주문서 작성 - ${selectedPolicy.title}`}
          open={modals.create}
          onCancel={() => closeModal('create')}
          footer={null}
          width={1000}
          destroyOnClose
        >
          <DynamicOrderForm
            policyId={selectedPolicy.id}
            onSuccess={() => {
              loadOrders();
              closeModal('create');
            }}
            onCancel={() => closeModal('create')}
          />
        </Modal>
      )}

      {/* 주문 수정 모달 */}
      {selectedOrder && (
        <Modal
          title={`주문서 수정 - ${selectedOrder.order_number}`}
          open={modals.edit}
          onCancel={() => closeModal('edit')}
          footer={null}
          width={1000}
          destroyOnClose
        >
          <DynamicOrderForm
            policyId={selectedOrder.policy}
            orderId={selectedOrder.id}
            onSuccess={() => {
              loadOrders();
              closeModal('edit');
            }}
            onCancel={() => closeModal('edit')}
          />
        </Modal>
      )}

      {/* 주문 승인 모달 */}
      <OrderApprovalModal
        open={modals.approval}
        onCancel={() => closeModal('approval')}
        onSuccess={() => {
          loadOrders();
        }}
        orderId={selectedOrder?.id}
        mode="approval"
      />

      {/* 주문 상세 보기 모달 */}
      <OrderApprovalModal
        open={modals.view}
        onCancel={() => closeModal('view')}
        orderId={selectedOrder?.id}
        mode="view"
      />
    </div>
  );
};

export default OrderManagementPage;