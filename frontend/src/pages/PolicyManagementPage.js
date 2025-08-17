/**
 * 정책 관리 페이지
 * 테이블 기반 목록 + 다이얼로그 방식의 관리 시스템
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Button, 
  Space, 
  Tag, 
  message, 
  Popconfirm,
  Tooltip,
  Badge
} from 'antd';
import { 
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  TeamOutlined,
  FormOutlined,
  DollarOutlined,
  EyeOutlined
} from '@ant-design/icons';

import SearchableTable from '../components/common/SearchableTable';
import PolicyCreateModal from '../components/policy/PolicyCreateModal';
import CompanyAssignmentModal from '../components/policy/CompanyAssignmentModal';
import OrderFormEditModal from '../components/policy/OrderFormEditModal';
import RebateEditModal from '../components/policy/RebateEditModal';
import AgencyRebateModal from '../components/AgencyRebateModal';
import { policyAPI, handleAPIError } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import './PolicyManagementPage.css';

const PolicyManagementPage = () => {
  // 상태 관리
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
    carrier: '',
    form_type: '',
  });

  // 모달 상태
  const [modals, setModals] = useState({
    create: false,
    assignment: false,
    orderForm: false,
    rebate: false,
    agencyRebate: false,
  });

  // 선택된 정책 정보
  const [selectedPolicy, setSelectedPolicy] = useState(null);

  // 인증 정보
  const { user, hasPermission } = useAuth();

  // 데이터 로드
  const loadPolicies = useCallback(async (params = {}) => {
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

      const response = await policyAPI.getPolicies(queryParams);
      
      setPolicies(response.results || []);
      setPagination(prev => ({
        ...prev,
        total: response.count || 0,
      }));

    } catch (error) {
      console.error('정책 목록 로드 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  }, [pagination.current, pagination.pageSize, searchValue, filters]);

  // 초기 로드
  useEffect(() => {
    loadPolicies();
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

  // 테이블 변경 핸들러 (페이지네이션, 정렬 등)
  const handleTableChange = (paginationInfo, filtersInfo, sorter) => {
    setPagination(prev => ({
      ...prev,
      current: paginationInfo.current,
      pageSize: paginationInfo.pageSize,
    }));
  };

  // 새로고침
  const handleRefresh = () => {
    loadPolicies();
  };

  // 모달 제어
  const openModal = (type, policy = null) => {
    setSelectedPolicy(policy);
    setModals(prev => ({ ...prev, [type]: true }));
  };

  const closeModal = (type) => {
    setModals(prev => ({ ...prev, [type]: false }));
    setSelectedPolicy(null);
  };

  // 정책 삭제
  const handleDeletePolicy = async (policyId, policyTitle) => {
    try {
      await policyAPI.deletePolicy(policyId);
      message.success(`"${policyTitle}" 정책이 삭제되었습니다.`);
      loadPolicies();
    } catch (error) {
      console.error('정책 삭제 오류:', error);
      message.error(handleAPIError(error));
    }
  };

  // 정책 상세 보기
  const handleViewPolicy = (policy) => {
    // TODO: 정책 상세 페이지 구현
    message.info('정책 상세 페이지는 준비 중입니다.');
  };

  // 테이블 컬럼 정의
  const columns = [
    {
      title: '정책명',
      dataIndex: 'title',
      key: 'title',
      width: 200,
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500, marginBottom: 4 }}>
            {text}
          </div>
          {record.description && (
            <div style={{ fontSize: 12, color: '#8c8c8c' }}>
              {record.description.length > 50 
                ? `${record.description.substring(0, 50)}...` 
                : record.description
              }
            </div>
          )}
        </div>
      ),
    },
    {
      title: '상태',
      dataIndex: 'status_display',
      key: 'status',
      width: 80,
      render: (text, record) => {
        const colors = {
          draft: 'default',
          active: 'success',
          inactive: 'error',
          pending: 'warning',
        };
        return <Tag color={colors[record.status]}>{text}</Tag>;
      },
    },
    {
      title: '통신사',
      dataIndex: 'carrier_display',
      key: 'carrier',
      width: 80,
    },
    {
      title: '신청서 타입',
      dataIndex: 'form_type_display',
      key: 'form_type',
      width: 100,
    },
    {
      title: '배정업체',
      dataIndex: 'assigned_companies_count',
      key: 'assigned_companies_count',
      width: 80,
      render: (count) => (
        <Badge count={count} showZero style={{ backgroundColor: '#52c41a' }} />
      ),
    },
    {
      title: '주문서',
      dataIndex: 'has_order_form',
      key: 'has_order_form',
      width: 70,
      render: (hasForm) => hasForm ? '✓' : '✗',
    },
    {
      title: '리베이트',
      dataIndex: 'rebate_matrix_count',
      key: 'rebate_matrix_count',
      width: 70,
      render: (count) => count > 0 ? '✓' : '✗',
    },
    {
      title: '생성자',
      dataIndex: 'created_by_username',
      key: 'created_by_username',
      width: 100,
    },
    {
      title: '생성일',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 100,
      render: (date) => new Date(date).toLocaleDateString(),
    },
    {
      title: '액션',
      key: 'action',
      width: 200,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4} className="action-buttons">
          <Tooltip title="상세보기">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewPolicy(record)}
              size="small"
            />
          </Tooltip>

          {record.can_edit && (
            <Tooltip title="정책 수정">
              <Button
                type="text"
                icon={<EditOutlined />}
                onClick={() => openModal('edit', record)}
                size="small"
              />
            </Tooltip>
          )}

          {record.can_assign_companies && (
            <Tooltip title="업체 배정">
              <Button
                type="text"
                icon={<TeamOutlined />}
                onClick={() => openModal('assignment', record)}
                size="small"
              />
            </Tooltip>
          )}

          {record.can_edit_order_form && (
            <Tooltip title="주문서 양식">
              <Button
                type="text"
                icon={<FormOutlined />}
                onClick={() => openModal('orderForm', record)}
                size="small"
              />
            </Tooltip>
          )}

          {record.can_edit && (
            <Tooltip title="리베이트 설정">
              <Button
                type="text"
                icon={<DollarOutlined />}
                onClick={() => openModal('rebate', record)}
                size="small"
              />
            </Tooltip>
          )}

          {user?.companyType === 'agency' && record.is_assigned_to_user && (
            <Tooltip title="판매점 리베이트 설정">
              <Button
                type="text"
                icon={<DollarOutlined />}
                onClick={() => openModal('agencyRebate', record)}
                size="small"
                style={{ color: '#52c41a' }}
              />
            </Tooltip>
          )}

          {record.can_delete && (
            <Popconfirm
              title="정책 삭제"
              description={`"${record.title}" 정책을 삭제하시겠습니까?`}
              onConfirm={() => handleDeletePolicy(record.id, record.title)}
              okText="삭제"
              cancelText="취소"
              okType="danger"
            >
              <Tooltip title="삭제">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                  size="small"
                />
              </Tooltip>
            </Popconfirm>
          )}
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
        { value: 'draft', label: '초안' },
        { value: 'active', label: '활성' },
        { value: 'inactive', label: '비활성' },
        { value: 'pending', label: '대기' },
      ],
    },
    {
      key: 'carrier',
      type: 'select',
      placeholder: '통신사 선택',
      options: [
        { value: 'all', label: '전체 통신사' },
        { value: 'skt', label: 'SKT' },
        { value: 'kt', label: 'KT' },
        { value: 'lg', label: 'LG U+' },
      ],
    },
    {
      key: 'form_type',
      type: 'select',
      placeholder: '신청서 타입',
      options: [
        { value: 'general', label: '일반 신청서' },
        { value: 'premium', label: '프리미엄 신청서' },
        { value: 'enterprise', label: '기업 신청서' },
        { value: 'student', label: '학생 신청서' },
      ],
    },
  ];

  return (
    <div className="policy-management-page">
      <SearchableTable
        title="정책 관리"
        columns={columns}
        dataSource={policies}
        loading={loading}
        rowKey="id"
        pagination={pagination}
        onChange={handleTableChange}
        searchPlaceholder="정책명 또는 설명으로 검색"
        searchValue={searchValue}
        onSearch={handleSearch}
        filters={tableFilters}
        filterValues={filters}
        onFilterChange={handleFilterChange}
        showCreateButton={hasPermission('policy.create')}
        createButtonText="정책 생성"
        onCreateClick={() => openModal('create')}
        onRefresh={handleRefresh}
      />

      {/* 정책 생성 모달 */}
      <PolicyCreateModal
        open={modals.create}
        onCancel={() => closeModal('create')}
        onSuccess={() => {
          loadPolicies();
          closeModal('create');
        }}
      />

      {/* 업체 배정 모달 */}
      {selectedPolicy && (
        <CompanyAssignmentModal
          open={modals.assignment}
          onCancel={() => closeModal('assignment')}
          onSuccess={() => {
            loadPolicies();
          }}
          policyId={selectedPolicy.id}
          policyTitle={selectedPolicy.title}
        />
      )}

      {/* 주문서 양식 편집 모달 */}
      {selectedPolicy && (
        <OrderFormEditModal
          open={modals.orderForm}
          onCancel={() => closeModal('orderForm')}
          onSuccess={() => {
            loadPolicies();
          }}
          policyId={selectedPolicy.id}
          policyTitle={selectedPolicy.title}
        />
      )}

      {/* 리베이트 설정 모달 */}
      {selectedPolicy && (
        <RebateEditModal
          open={modals.rebate}
          onCancel={() => closeModal('rebate')}
          onSuccess={() => {
            loadPolicies();
          }}
          policyId={selectedPolicy.id}
          policyTitle={selectedPolicy.title}
        />
      )}

      {/* 협력사 리베이트 설정 모달 */}
      {selectedPolicy && (
        <AgencyRebateModal
          visible={modals.agencyRebate}
          onCancel={() => closeModal('agencyRebate')}
          onSuccess={() => {
            loadPolicies();
          }}
          policy={selectedPolicy}
        />
      )}
    </div>
  );
};

export default PolicyManagementPage;
