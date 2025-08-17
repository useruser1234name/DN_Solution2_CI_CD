/**
 * 주문서 양식 편집 모달
 * 정책의 주문서 양식을 생성/수정하는 다이얼로그
 */

import React, { useState, useEffect } from 'react';
import { 
  Form, 
  Input, 
  Select, 
  Switch, 
  Button, 
  message, 
  Card,
  Space,
  Alert,
  Row,
  Col,
  InputNumber,
  Divider
} from 'antd';
import { 
  PlusOutlined, 
  DeleteOutlined, 
  ArrowUpOutlined, 
  ArrowDownOutlined 
} from '@ant-design/icons';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import CustomModal from '../common/CustomModal';
import { policyAPI, handleAPIError } from '../../services/api';
import './OrderFormEditModal.css';

const { Option } = Select;
const { TextArea } = Input;

const OrderFormEditModal = ({ 
  open, 
  onCancel, 
  onSuccess, 
  policyId, 
  policyTitle 
}) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [fields, setFields] = useState([]);
  const [hasExistingForm, setHasExistingForm] = useState(false);

  // 필드 타입 옵션
  const fieldTypeOptions = [
    { value: 'text', label: '텍스트' },
    { value: 'number', label: '숫자' },
    { value: 'select', label: '선택 (드롭다운)' },
    { value: 'radio', label: '라디오 버튼' },
    { value: 'checkbox', label: '체크박스' },
    { value: 'textarea', label: '텍스트 영역' },
    { value: 'date', label: '날짜' },
    { value: 'rebate_table', label: '리베이트 테이블' },
  ];

  // 기본 필드 템플릿
  const defaultFields = [
    {
      field_name: 'customer_name',
      field_label: '고객명',
      field_type: 'text',
      is_required: true,
      placeholder: '고객명을 입력하세요',
      order: 1,
    },
    {
      field_name: 'phone',
      field_label: '전화번호',
      field_type: 'text',
      is_required: true,
      placeholder: '010-0000-0000',
      order: 2,
    },
    {
      field_name: 'carrier',
      field_label: '통신사',
      field_type: 'select',
      is_required: true,
      field_options: [
        { value: 'skt', label: 'SKT' },
        { value: 'kt', label: 'KT' },
        { value: 'lg', label: 'LG U+' },
      ],
      order: 3,
    },
    {
      field_name: 'plan',
      field_label: '요금제',
      field_type: 'select',
      is_required: true,
      field_options: [
        { value: '30000', label: '3만원대' },
        { value: '50000', label: '5만원대' },
        { value: '70000', label: '7만원대' },
        { value: '100000', label: '10만원대' },
      ],
      order: 4,
    },
    {
      field_name: 'contract_period',
      field_label: '가입기간',
      field_type: 'select',
      is_required: true,
      field_options: [
        { value: '3', label: '3개월' },
        { value: '6', label: '6개월' },
        { value: '12', label: '12개월' },
        { value: '24', label: '24개월' },
        { value: '36', label: '36개월' },
      ],
      order: 5,
    },
    {
      field_name: 'url_link',
      field_label: 'URL 링크',
      field_type: 'text',
      is_required: true,
      placeholder: 'https://example.com',
      order: 6,
    },
    {
      field_name: 'memo',
      field_label: '메모',
      field_type: 'textarea',
      is_required: false,
      placeholder: '추가 메모사항',
      order: 7,
    },
  ];

  // 데이터 로드
  useEffect(() => {
    if (open && policyId) {
      loadFormData();
    }
  }, [open, policyId]);

  const loadFormData = async () => {
    setLoadingData(true);
    try {
      const response = await policyAPI.getOrderForm(policyId);
      
      if (response.has_form !== false && response.fields) {
        // 기존 양식이 있는 경우
        setHasExistingForm(true);
        setFields(response.fields.sort((a, b) => a.order - b.order));
        form.setFieldsValue({
          title: response.title,
          description: response.description,
          is_active: response.is_active,
        });
      } else {
        // 기존 양식이 없는 경우 - 기본 템플릿 사용
        setHasExistingForm(false);
        setFields(defaultFields);
        form.setFieldsValue({
          title: `${policyTitle} 주문서`,
          description: '고객 정보를 입력해주세요.',
          is_active: true,
        });
      }
    } catch (error) {
      console.error('양식 데이터 로드 오류:', error);
      message.error(handleAPIError(error));
      // 오류 시에도 기본 템플릿 사용
      setFields(defaultFields);
    } finally {
      setLoadingData(false);
    }
  };

  // 양식 저장
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      const formData = {
        title: values.title,
        description: values.description,
        is_active: values.is_active,
        fields: fields.map((field, index) => ({
          ...field,
          order: index + 1,
        })),
      };

      await policyAPI.updateOrderForm(policyId, formData);
      
      message.success('주문서 양식이 저장되었습니다.');
      onSuccess?.();
      onCancel();

    } catch (error) {
      console.error('양식 저장 오류:', error);
      message.error(handleAPIError(error));
    } finally {
      setLoading(false);
    }
  };

  // 필드 추가
  const addField = () => {
    const newField = {
      field_name: `field_${Date.now()}`,
      field_label: '새 필드',
      field_type: 'text',
      is_required: false,
      placeholder: '',
      help_text: '',
      order: fields.length + 1,
    };
    setFields([...fields, newField]);
  };

  // 필드 삭제
  const removeField = (index) => {
    const newFields = fields.filter((_, i) => i !== index);
    setFields(newFields);
  };

  // 필드 업데이트
  const updateField = (index, updatedField) => {
    const newFields = [...fields];
    newFields[index] = { ...newFields[index], ...updatedField };
    setFields(newFields);
  };

  // 드래그 앤 드롭 처리
  const handleDragEnd = (result) => {
    if (!result.destination) return;

    const items = Array.from(fields);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    setFields(items);
  };

  // 필드 옵션 관리 (select, radio 타입용)
  const updateFieldOptions = (fieldIndex, options) => {
    updateField(fieldIndex, { field_options: options });
  };

  const handleCancel = () => {
    form.resetFields();
    setFields([]);
    onCancel();
  };

  return (
    <CustomModal
      title={`주문서 양식 편집 - ${policyTitle}`}
      open={open}
      onCancel={handleCancel}
      onOk={handleSave}
      loading={loading}
      width={1200}
      okText="저장"
      cancelText="취소"
    >
      <div className="order-form-edit">
        {loadingData ? (
          <div style={{ textAlign: 'center', padding: 40 }}>로딩 중...</div>
        ) : (
          <>
            {/* 양식 기본 정보 */}
            <Card title="양식 기본 정보" style={{ marginBottom: 16 }}>
              <Form form={form} layout="vertical">
                <Row gutter={16}>
                  <Col span={12}>
                    <Form.Item
                      name="title"
                      label="양식 제목"
                      rules={[{ required: true, message: '양식 제목을 입력해주세요.' }]}
                    >
                      <Input placeholder="양식 제목" />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item
                      name="is_active"
                      label="활성화 여부"
                      valuePropName="checked"
                    >
                      <Switch />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item
                  name="description"
                  label="양식 설명"
                >
                  <TextArea rows={2} placeholder="양식에 대한 설명" />
                </Form.Item>
              </Form>
            </Card>

            <Divider />

            {/* 필드 관리 */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3>주문서 필드 ({fields.length}개)</h3>
              <Button 
                type="primary" 
                icon={<PlusOutlined />} 
                onClick={addField}
              >
                필드 추가
              </Button>
            </div>

            {!hasExistingForm && (
              <Alert
                message="기본 주문서 템플릿"
                description="새 정책이므로 기본 주문서 템플릿이 제공됩니다. 필요에 따라 필드를 추가, 수정, 삭제할 수 있습니다."
                type="info"
                showIcon
                style={{ marginBottom: 16 }}
              />
            )}

            {/* 드래그 가능한 필드 리스트 */}
            <DragDropContext onDragEnd={handleDragEnd}>
              <Droppable droppableId="fields">
                {(provided) => (
                  <div {...provided.droppableProps} ref={provided.innerRef}>
                    {fields.map((field, index) => (
                      <Draggable
                        key={`field-${index}`}
                        draggableId={`field-${index}`}
                        index={index}
                      >
                        {(provided, snapshot) => (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            className={`field-item ${snapshot.isDragging ? 'dragging' : ''}`}
                          >
                            <FieldEditor
                              field={field}
                              index={index}
                              onUpdate={updateField}
                              onRemove={removeField}
                              onUpdateOptions={updateFieldOptions}
                              dragHandleProps={provided.dragHandleProps}
                              fieldTypeOptions={fieldTypeOptions}
                            />
                          </div>
                        )}
                      </Draggable>
                    ))}
                    {provided.placeholder}
                  </div>
                )}
              </Droppable>
            </DragDropContext>

            {fields.length === 0 && (
              <div style={{ 
                textAlign: 'center', 
                padding: 40, 
                border: '2px dashed #d9d9d9', 
                borderRadius: 4,
                color: '#8c8c8c'
              }}>
                필드가 없습니다. "필드 추가" 버튼을 클릭하여 필드를 추가해주세요.
              </div>
            )}
          </>
        )}
      </div>
    </CustomModal>
  );
};

// 개별 필드 편집 컴포넌트
const FieldEditor = ({ 
  field, 
  index, 
  onUpdate, 
  onRemove, 
  onUpdateOptions,
  dragHandleProps, 
  fieldTypeOptions 
}) => {
  const [optionsText, setOptionsText] = useState('');

  useEffect(() => {
    if (field.field_options && Array.isArray(field.field_options)) {
      const text = field.field_options
        .map(opt => `${opt.value}:${opt.label}`)
        .join('\n');
      setOptionsText(text);
    }
  }, [field.field_options]);

  const handleOptionsChange = (e) => {
    const text = e.target.value;
    setOptionsText(text);
    
    // 텍스트를 배열로 변환
    const options = text
      .split('\n')
      .filter(line => line.trim())
      .map(line => {
        const [value, label] = line.split(':');
        return {
          value: value?.trim() || '',
          label: label?.trim() || value?.trim() || '',
        };
      });
    
    onUpdateOptions(index, options);
  };

  const showOptions = ['select', 'radio', 'checkbox'].includes(field.field_type);

  return (
    <Card 
      size="small" 
      style={{ marginBottom: 8 }}
      title={
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <div {...dragHandleProps} style={{ cursor: 'grab', marginRight: 8 }}>
            ⋮⋮
          </div>
          <span>필드 #{index + 1}</span>
        </div>
      }
      extra={
        <Button
          type="text"
          danger
          icon={<DeleteOutlined />}
          onClick={() => onRemove(index)}
          size="small"
        >
          삭제
        </Button>
      }
    >
      <Row gutter={12}>
        <Col span={6}>
          <Input
            placeholder="필드명"
            value={field.field_name}
            onChange={(e) => onUpdate(index, { field_name: e.target.value })}
            size="small"
          />
        </Col>
        <Col span={6}>
          <Input
            placeholder="라벨"
            value={field.field_label}
            onChange={(e) => onUpdate(index, { field_label: e.target.value })}
            size="small"
          />
        </Col>
        <Col span={4}>
          <Select
            value={field.field_type}
            onChange={(value) => onUpdate(index, { field_type: value })}
            size="small"
            style={{ width: '100%' }}
          >
            {fieldTypeOptions.map(opt => (
              <Option key={opt.value} value={opt.value}>
                {opt.label}
              </Option>
            ))}
          </Select>
        </Col>
        <Col span={4}>
          <Input
            placeholder="플레이스홀더"
            value={field.placeholder}
            onChange={(e) => onUpdate(index, { placeholder: e.target.value })}
            size="small"
          />
        </Col>
        <Col span={4}>
          <Space>
            <Switch
              checked={field.is_required}
              onChange={(checked) => onUpdate(index, { is_required: checked })}
              size="small"
            />
            <span style={{ fontSize: 12 }}>필수</span>
          </Space>
        </Col>
      </Row>

      {showOptions && (
        <div style={{ marginTop: 8 }}>
          <TextArea
            placeholder="옵션 (value:label 형식으로 한 줄씩 입력)&#10;예:&#10;skt:SKT&#10;kt:KT"
            value={optionsText}
            onChange={handleOptionsChange}
            rows={3}
            size="small"
          />
        </div>
      )}

      {field.help_text !== undefined && (
        <div style={{ marginTop: 8 }}>
          <Input
            placeholder="도움말 텍스트"
            value={field.help_text}
            onChange={(e) => onUpdate(index, { help_text: e.target.value })}
            size="small"
          />
        </div>
      )}
    </Card>
  );
};

export default OrderFormEditModal;

