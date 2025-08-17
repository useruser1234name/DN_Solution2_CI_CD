/**
 * 업체 계층형 트리 뷰 컴포넌트
 * 본사 → 협력사 → 판매점 구조를 시각적으로 표현
 */

import React, { useState, useEffect } from 'react';
import { 
  Tree, 
  Card, 
  Space, 
  Button, 
  Tag, 
  Tooltip, 
  Dropdown, 
  message,
  Badge,
  Input,
  Row,
  Col
} from 'antd';
import { 
  TeamOutlined,
  UserOutlined,
  MoreOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  EyeOutlined,
  SearchOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { companyAPI, handleAPIError } from '../../services/api';
import { useAuth } from '../../contexts/AuthContext';
import './CompanyTreeView.css';

const { Search } = Input;

const CompanyTreeView = ({ 
  onCompanySelect, 
  onCompanyEdit, 
  onCompanyCreate,
  onUserManage,
  selectedCompanyId 
}) => {
  const [treeData, setTreeData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedKeys, setExpandedKeys] = useState([]);
  const [searchValue, setSearchValue] = useState('');
  const [autoExpandParent, setAutoExpandParent] = useState(true);
  
  const { hasPermission, user } = useAuth();

  useEffect(() => {
    loadCompanies();
  }, []);

  // 업체 데이터 로드
  const loadCompanies = async () => {
    setLoading(true);
    try {
      const response = await companyAPI.getCompanies();
      const companies = response.results || response || [];
      
      const treeStructure = buildTreeStructure(companies);
      setTreeData(treeStructure);
      
      // 기본적으로 모든 노드 확장
      const allKeys = getAllKeys(treeStructure);
      setExpandedKeys(allKeys);
      
    } catch (error) {
      console.error('업체 목록 로드 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  };

  // 트리 구조 빌드
  const buildTreeStructure = (companies) => {
    const companyMap = new Map();
    const rootCompanies = [];

    // 1단계: 모든 업체를 맵에 저장
    companies.forEach(company => {
      companyMap.set(company.id, {
        ...company,
        children: []
      });
    });

    // 2단계: 계층 구조 구성
    companies.forEach(company => {
      const companyNode = companyMap.get(company.id);
      
      if (company.parent_company) {
        const parent = companyMap.get(company.parent_company);
        if (parent) {
          parent.children.push(companyNode);
        } else {
          rootCompanies.push(companyNode);
        }
      } else {
        rootCompanies.push(companyNode);
      }
    });

    // 3단계: Tree 컴포넌트용 데이터 변환
    return convertToTreeData(rootCompanies);
  };

  // Tree 데이터 형식으로 변환
  const convertToTreeData = (companies) => {
    return companies.map(company => ({
      key: company.id,
      title: renderTreeNode(company),
      icon: getCompanyIcon(company.type),
      children: company.children ? convertToTreeData(company.children) : [],
      company: company, // 원본 데이터 보관
    }));
  };

  // 트리 노드 렌더링
  const renderTreeNode = (company) => {
    const isSelected = selectedCompanyId === company.id;
    const hasUsers = company.user_count > 0;
    const hasPendingUsers = company.pending_user_count > 0;

    return (
      <div className={`tree-node ${isSelected ? 'selected' : ''}`}>
        <div className="node-info">
          <div className="company-name">
            {company.name}
            <Tag 
              color={getCompanyTypeColor(company.type)} 
              size="small"
              style={{ marginLeft: 8 }}
            >
              {getCompanyTypeLabel(company.type)}
            </Tag>
            {!company.status && (
              <Tag color="red" size="small">비활성</Tag>
            )}
          </div>
          <div className="company-details">
            <span className="company-code">{company.code}</span>
            {hasUsers && (
              <Badge 
                count={company.user_count} 
                size="small" 
                style={{ backgroundColor: '#52c41a', marginLeft: 8 }}
                title="등록된 사용자 수"
              />
            )}
            {hasPendingUsers && (
              <Badge 
                count={company.pending_user_count} 
                size="small" 
                style={{ backgroundColor: '#faad14', marginLeft: 4 }}
                title="승인 대기 사용자 수"
              />
            )}
          </div>
        </div>
        
        <div className="node-actions">
          <Dropdown
            menu={{
              items: getActionMenuItems(company),
            }}
            trigger={['click']}
            placement="bottomRight"
          >
            <Button 
              type="text" 
              icon={<MoreOutlined />} 
              size="small"
              className="action-button"
            />
          </Dropdown>
        </div>
      </div>
    );
  };

  // 액션 메뉴 아이템
  const getActionMenuItems = (company) => {
    const items = [];

    // 상세 보기
    items.push({
      key: 'view',
      icon: <EyeOutlined />,
      label: '상세 보기',
      onClick: () => onCompanySelect?.(company),
    });

    // 사용자 관리
    if (hasPermission('company.approve_user') || company.user_count > 0) {
      items.push({
        key: 'users',
        icon: <UserOutlined />,
        label: `사용자 관리 ${company.pending_user_count > 0 ? `(${company.pending_user_count})` : ''}`,
        onClick: () => onUserManage?.(company),
      });
    }

    // 하위 업체 추가 (협력사만)
    if (hasPermission('company.create') && company.type === 'agency') {
      items.push({
        key: 'add-child',
        icon: <PlusOutlined />,
        label: '판매점 추가',
        onClick: () => onCompanyCreate?.(company.id, 'retail'),
      });
    }

    // 수정
    if (hasPermission('company.edit')) {
      items.push({
        type: 'divider',
      });
      items.push({
        key: 'edit',
        icon: <EditOutlined />,
        label: '수정',
        onClick: () => onCompanyEdit?.(company),
      });
    }

    // 삭제
    if (hasPermission('company.delete') && company.children?.length === 0) {
      items.push({
        key: 'delete',
        icon: <DeleteOutlined />,
        label: '삭제',
        danger: true,
        onClick: () => handleDeleteCompany(company),
      });
    }

    return items;
  };

  // 업체 삭제
  const handleDeleteCompany = async (company) => {
    try {
      await companyAPI.deleteCompany(company.id);
      message.success(`${company.name}이 삭제되었습니다.`);
      loadCompanies();
    } catch (error) {
      console.error('업체 삭제 오류:', error);
      message.error(handleAPIError(error));
    }
  };

  // 모든 키 가져오기 (확장용)
  const getAllKeys = (data) => {
    const keys = [];
    const extract = (nodes) => {
      nodes.forEach(node => {
        keys.push(node.key);
        if (node.children) {
          extract(node.children);
        }
      });
    };
    extract(data);
    return keys;
  };

  // 검색 기능
  const handleSearch = (value) => {
    setSearchValue(value);
    if (value) {
      // 검색어가 포함된 노드들의 키를 찾아서 확장
      const expandKeys = [];
      const searchNodes = (data, searchValue) => {
        data.forEach(node => {
          const company = node.company;
          if (company.name.toLowerCase().includes(searchValue.toLowerCase()) ||
              company.code.toLowerCase().includes(searchValue.toLowerCase())) {
            expandKeys.push(node.key);
            // 부모 노드들도 확장되도록 경로 추가
            let parent = findParentKey(treeData, node.key);
            while (parent) {
              expandKeys.push(parent);
              parent = findParentKey(treeData, parent);
            }
          }
          if (node.children) {
            searchNodes(node.children, searchValue);
          }
        });
      };
      searchNodes(treeData, value);
      setExpandedKeys(expandKeys);
      setAutoExpandParent(true);
    } else {
      setExpandedKeys(getAllKeys(treeData));
    }
  };

  // 부모 키 찾기
  const findParentKey = (data, targetKey, parentKey = null) => {
    for (const node of data) {
      if (node.key === targetKey) {
        return parentKey;
      }
      if (node.children) {
        const found = findParentKey(node.children, targetKey, node.key);
        if (found !== null) {
          return found;
        }
      }
    }
    return null;
  };

  // 업체 타입별 아이콘
  const getCompanyIcon = (type) => {
    switch (type) {
      case 'headquarters': return <TeamOutlined style={{ color: '#ff4d4f' }} />;
      case 'agency': return <TeamOutlined style={{ color: '#1890ff' }} />;
      case 'retail': return <TeamOutlined style={{ color: '#52c41a' }} />;
      default: return <TeamOutlined />;
    }
  };

  // 업체 타입별 색상
  const getCompanyTypeColor = (type) => {
    switch (type) {
      case 'headquarters': return 'red';
      case 'agency': return 'blue';
      case 'retail': return 'green';
      default: return 'default';
    }
  };

  // 업체 타입별 라벨
  const getCompanyTypeLabel = (type) => {
    switch (type) {
      case 'headquarters': return '본사';
      case 'agency': return '협력사';
      case 'retail': return '판매점';
      default: return '알 수 없음';
    }
  };

  // 트리 노드 선택
  const handleSelect = (selectedKeys, { node }) => {
    if (selectedKeys.length > 0) {
      onCompanySelect?.(node.company);
    }
  };

  // 트리 확장/축소
  const handleExpand = (expandedKeys) => {
    setExpandedKeys(expandedKeys);
    setAutoExpandParent(false);
  };

  return (
    <Card 
      title="업체 구조" 
      className="company-tree-view"
      extra={
        <Space>
          {hasPermission('company.create') && (
            <Tooltip title="협력사 추가">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                size="small"
                onClick={() => onCompanyCreate?.(null, 'agency')}
              >
                협력사 추가
              </Button>
            </Tooltip>
          )}
          <Tooltip title="새로고침">
            <Button
              icon={<ReloadOutlined />}
              size="small"
              onClick={loadCompanies}
              loading={loading}
            />
          </Tooltip>
        </Space>
      }
    >
      {/* 검색 */}
      <div style={{ marginBottom: 16 }}>
        <Search
          placeholder="업체명 또는 코드로 검색"
          allowClear
          onSearch={handleSearch}
          style={{ width: '100%' }}
        />
      </div>

      {/* 트리 */}
      <Tree
        showIcon
        showLine={{ showLeafIcon: false }}
        treeData={treeData}
        expandedKeys={expandedKeys}
        autoExpandParent={autoExpandParent}
        onExpand={handleExpand}
        onSelect={handleSelect}
        selectedKeys={selectedCompanyId ? [selectedCompanyId] : []}
        className="company-tree"
        loading={loading}
      />

      {treeData.length === 0 && !loading && (
        <div className="empty-state">
          <TeamOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
          <p>등록된 업체가 없습니다.</p>
          {hasPermission('company.create') && (
            <Button 
              type="primary" 
              icon={<PlusOutlined />}
              onClick={() => onCompanyCreate?.(null, 'agency')}
            >
              첫 협력사 추가
            </Button>
          )}
        </div>
      )}
    </Card>
  );
};

export default CompanyTreeView;


