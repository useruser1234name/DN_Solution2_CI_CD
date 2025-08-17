/**
 * 검색 가능한 테이블 컴포넌트
 * 필터링, 페이지네이션, 검색 기능이 통합된 테이블
 */

import React, { useState, useEffect } from 'react';
import { 
  Table, 
  Input, 
  Button, 
  Space, 
  Select, 
  DatePicker, 
  Card,
  Row,
  Col,
  Divider
} from 'antd';
import { SearchOutlined, ReloadOutlined, PlusOutlined } from '@ant-design/icons';
import './SearchableTable.css';

const { Search } = Input;
const { Option } = Select;
const { RangePicker } = DatePicker;

const SearchableTable = ({
  // 테이블 설정
  columns = [],
  dataSource = [],
  loading = false,
  rowKey = 'id',
  
  // 페이지네이션
  pagination = {},
  onChange,
  
  // 검색/필터 설정
  searchPlaceholder = '검색어를 입력하세요',
  onSearch,
  searchValue,
  onSearchChange,
  
  // 필터 설정
  filters = [],
  filterValues = {},
  onFilterChange,
  
  // 액션 버튼
  showCreateButton = false,
  createButtonText = '생성',
  onCreateClick,
  
  showRefreshButton = true,
  onRefresh,
  
  // 추가 액션
  extraActions = [],
  
  // 제목
  title,
  
  // 기타
  className = '',
  ...tableProps
}) => {
  const [localSearchValue, setLocalSearchValue] = useState(searchValue || '');

  useEffect(() => {
    setLocalSearchValue(searchValue || '');
  }, [searchValue]);

  const handleSearch = (value) => {
    setLocalSearchValue(value);
    if (onSearch) {
      onSearch(value);
    }
  };

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setLocalSearchValue(value);
    if (onSearchChange) {
      onSearchChange(value);
    }
  };

  const handleFilterChange = (filterKey, value) => {
    if (onFilterChange) {
      onFilterChange(filterKey, value);
    }
  };

  const defaultPagination = {
    current: 1,
    pageSize: 20,
    total: 0,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total, range) => 
      `${range[0]}-${range[1]} / 총 ${total}개`,
    pageSizeOptions: ['10', '20', '50', '100'],
    ...pagination,
  };

  return (
    <Card 
      className={`searchable-table ${className}`}
      title={title}
    >
      {/* 검색 및 필터 영역 */}
      <div className="table-header">
        <Row gutter={[16, 16]} align="middle">
          {/* 검색 박스 */}
          <Col xs={24} sm={12} md={8} lg={6}>
            <Search
              placeholder={searchPlaceholder}
              value={localSearchValue}
              onChange={handleSearchChange}
              onSearch={handleSearch}
              allowClear
              enterButton={<SearchOutlined />}
            />
          </Col>

          {/* 필터들 */}
          {filters.map((filter, index) => (
            <Col key={filter.key} xs={24} sm={12} md={6} lg={4}>
              {filter.type === 'select' && (
                <Select
                  placeholder={filter.placeholder}
                  value={filterValues[filter.key]}
                  onChange={(value) => handleFilterChange(filter.key, value)}
                  allowClear
                  style={{ width: '100%' }}
                >
                  {filter.options?.map(option => (
                    <Option key={option.value} value={option.value}>
                      {option.label}
                    </Option>
                  ))}
                </Select>
              )}
              
              {filter.type === 'date' && (
                <RangePicker
                  placeholder={[filter.startPlaceholder, filter.endPlaceholder]}
                  value={filterValues[filter.key]}
                  onChange={(value) => handleFilterChange(filter.key, value)}
                  style={{ width: '100%' }}
                />
              )}
              
              {filter.type === 'input' && (
                <Input
                  placeholder={filter.placeholder}
                  value={filterValues[filter.key]}
                  onChange={(e) => handleFilterChange(filter.key, e.target.value)}
                  allowClear
                />
              )}
            </Col>
          ))}

          {/* 액션 버튼들 */}
          <Col xs={24} sm={24} md={24} lg="auto" style={{ marginLeft: 'auto' }}>
            <Space>
              {extraActions}
              
              {showRefreshButton && (
                <Button
                  icon={<ReloadOutlined />}
                  onClick={onRefresh}
                  loading={loading}
                >
                  새로고침
                </Button>
              )}
              
              {showCreateButton && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={onCreateClick}
                >
                  {createButtonText}
                </Button>
              )}
            </Space>
          </Col>
        </Row>
      </div>

      <Divider style={{ margin: '16px 0' }} />

      {/* 테이블 */}
      <Table
        columns={columns}
        dataSource={dataSource}
        loading={loading}
        pagination={defaultPagination}
        onChange={onChange}
        rowKey={rowKey}
        scroll={{ x: 'max-content' }}
        {...tableProps}
      />
    </Card>
  );
};

export default SearchableTable;

