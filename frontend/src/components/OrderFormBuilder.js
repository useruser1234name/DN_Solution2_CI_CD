import React, { useState } from 'react';
import { Modal, Form, Input, Select, Button, Space, Card, Switch, message } from 'antd';
import { PlusOutlined, DeleteOutlined, DragOutlined } from '@ant-design/icons';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import { post } from '../services/api';
import './OrderFormBuilder.css';

const { Option } = Select;
const { TextArea } = Input;

const OrderFormBuilder = ({ visible, onClose, policyId, policyTitle }) => {
  const [form] = Form.useForm();
  const [fields, setFields] = useState([
    {
      id: 'price_a',
      field_name: 'price_a',
      field_label: 'A단가',
      field_type: 'number',
      is_required: true,
      placeholder: 'A단가를 입력하세요',
      order: 0
    },
    {
      id: 'price_b',
      field_name: 'price_b',
      field_label: 'B단가',
      field_type: 'number',
      is_required: true,
      placeholder: 'B단가를 입력하세요',
      order: 1
    },
    {
      id: 'carrier',
      field_name: 'carrier',
      field_label: '통신사',
      field_type: 'select',
      is_required: true,
      field_options: {
        choices: ['SKT', 'KT', 'LG U+', '알뜰폰']
      },
      order: 2
    }
  ]);
  const [saving, setSaving] = useState(false);

  const fieldTypes = [
    { value: 'text', label: '텍스트' },
    { value: 'number', label: '숫자' },
    { value: 'select', label: '선택박스' },
    { value: 'textarea', label: '긴 텍스트' },
    { value: 'date', label: '날짜' },
    { value: 'phone', label: '전화번호' },
    { value: 'email', label: '이메일' },
    { value: 'carrier_plan', label: '통신사 요금제' },
    { value: 'device_model', label: '기기 모델' },
    { value: 'device_color', label: '기기 색상' },
    { value: 'sim_type', label: '유심 타입' },
    { value: 'contract_period', label: '계약 기간' },
    { value: 'payment_method', label: '결제 방법' },
    { value: 'rebate_table', label: '리베이트 테이블' }
  ];

  const handleAddField = () => {
    const newField = {
      id: `field_${Date.now()}`,
      field_name: '',
      field_label: '',
      field_type: 'text',
      is_required: false,
      placeholder: '',
      help_text: '',
      order: fields.length
    };
    setFields([...fields, newField]);
  };

  const handleRemoveField = (fieldId) => {
    setFields(fields.filter(f => f.id !== fieldId));
  };

  const handleFieldChange = (fieldId, key, value) => {
    setFields(fields.map(field => 
      field.id === fieldId ? { ...field, [key]: value } : field
    ));
  };

  const handleDragEnd = (result) => {
    if (!result.destination) return;

    const items = Array.from(fields);
    const [reorderedItem] = items.splice(result.source.index, 1);
    items.splice(result.destination.index, 0, reorderedItem);

    // Update order values
    const updatedItems = items.map((item, index) => ({
      ...item,
      order: index
    }));

    setFields(updatedItems);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);

      const formData = {
        title: values.title,
        description: values.description,
        is_active: true,
        fields: fields.map(field => ({
          field_name: field.field_name,
          field_label: field.field_label,
          field_type: field.field_type,
          is_required: field.is_required,
          placeholder: field.placeholder,
          help_text: field.help_text,
          field_options: field.field_options || {},
          order: field.order
        }))
      };

      await post(`policies/${policyId}/order-form/`, formData);
      message.success('주문서 양식이 저장되었습니다.');
      onClose();
    } catch (error) {
      if (error.errorFields) {
        message.error('필수 입력 항목을 확인해주세요.');
      } else {
        message.error('주문서 양식 저장에 실패했습니다.');
      }
      console.error('Error saving form:', error);
    } finally {
      setSaving(false);
    }
  };

  const renderFieldPreview = (field) => {
    switch (field.field_type) {
      case 'text':
      case 'number':
        return <Input placeholder={field.placeholder} disabled />;
      case 'phone':
        return <Input placeholder="010-1234-5678" disabled />;
      case 'email':
        return <Input placeholder="example@email.com" disabled />;
      case 'textarea':
        return <TextArea rows={3} placeholder={field.placeholder} disabled />;
      case 'select':
        return (
          <Select placeholder={field.placeholder} disabled style={{ width: '100%' }}>
            {field.field_options?.choices?.map(choice => (
              <Option key={choice} value={choice}>{choice}</Option>
            ))}
          </Select>
        );
      case 'carrier_plan':
        return (
          <Select placeholder="통신사 요금제를 선택하세요" disabled style={{ width: '100%' }}>
            <Option value="skt_basic">SKT - 초이스베이직 (30,000원)</Option>
            <Option value="kt_premium">KT - 프리미엄 (50,000원)</Option>
          </Select>
        );
      case 'device_model':
        return (
          <Select placeholder="기기 모델을 선택하세요" disabled style={{ width: '100%' }}>
            <Option value="galaxy_s24">Samsung Galaxy S24</Option>
            <Option value="iphone_15">Apple iPhone 15</Option>
          </Select>
        );
      case 'device_color':
        return (
          <Select placeholder="기기 색상을 선택하세요" disabled style={{ width: '100%' }}>
            <Option value="black">블랙</Option>
            <Option value="white">화이트</Option>
            <Option value="blue">블루</Option>
          </Select>
        );
      case 'sim_type':
        return (
          <Select placeholder="유심 타입을 선택하세요" disabled style={{ width: '100%' }}>
            <Option value="prepaid">선불 (본사 7,700원 지급)</Option>
            <Option value="postpaid">후불 (본사 7,700원 차감)</Option>
            <Option value="esim">eSIM</Option>
            <Option value="reuse">재사용</Option>
          </Select>
        );
      case 'contract_period':
        return (
          <Select placeholder="계약 기간을 선택하세요" disabled style={{ width: '100%' }}>
            <Option value="12">12개월</Option>
            <Option value="24">24개월</Option>
            <Option value="36">36개월</Option>
          </Select>
        );
      case 'payment_method':
        return (
          <Select placeholder="결제 방법을 선택하세요" disabled style={{ width: '100%' }}>
            <Option value="cash">현금</Option>
            <Option value="installment">할부</Option>
          </Select>
        );
      case 'date':
        return <Input type="date" disabled />;
      case 'rebate_table':
        return (
          <div className="rebate-table-preview">
            <table>
              <thead>
                <tr>
                  <th>요금제명</th>
                  <th>리베이트</th>
                  <th>작업</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><Input placeholder="요금제명" disabled size="small" /></td>
                  <td><Input placeholder="리베이트" disabled size="small" /></td>
                  <td><Button size="small" icon={<PlusOutlined />} disabled /></td>
                </tr>
              </tbody>
            </table>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <Modal
      title={`주문서 양식 설계 - ${policyTitle}`}
      visible={visible}
      onCancel={onClose}
      width={900}
      footer={[
        <Button key="cancel" onClick={onClose}>
          취소
        </Button>,
        <Button 
          key="save" 
          type="primary" 
          loading={saving}
          onClick={handleSave}
        >
          저장
        </Button>
      ]}
    >
      <Form form={form} layout="vertical">
        <Form.Item
          name="title"
          label="양식 제목"
          rules={[{ required: true, message: '양식 제목을 입력하세요' }]}
        >
          <Input placeholder="예: SKT 5G 요금제 주문서" />
        </Form.Item>

        <Form.Item
          name="description"
          label="양식 설명"
        >
          <TextArea rows={2} placeholder="이 양식에 대한 설명을 입력하세요" />
        </Form.Item>

        <div className="form-fields-section">
          <div className="section-header">
            <h3>주문서 필드</h3>
            <Button 
              type="dashed" 
              icon={<PlusOutlined />}
              onClick={handleAddField}
            >
              필드 추가
            </Button>
          </div>

          <DragDropContext onDragEnd={handleDragEnd}>
            <Droppable droppableId="fields">
              {(provided) => (
                <div {...provided.droppableProps} ref={provided.innerRef}>
                  {fields.map((field, index) => (
                    <Draggable key={field.id} draggableId={field.id} index={index}>
                      {(provided, snapshot) => (
                        <Card
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={`field-card ${snapshot.isDragging ? 'dragging' : ''}`}
                          style={{ ...provided.draggableProps.style }}
                        >
                          <div className="field-card-header">
                            <div {...provided.dragHandleProps} className="drag-handle">
                              <DragOutlined />
                            </div>
                            <Button
                              type="text"
                              danger
                              icon={<DeleteOutlined />}
                              onClick={() => handleRemoveField(field.id)}
                            />
                          </div>

                          <div className="field-config">
                            <Space size="middle" style={{ width: '100%' }}>
                              <Input
                                placeholder="필드명 (영문)"
                                value={field.field_name}
                                onChange={(e) => handleFieldChange(field.id, 'field_name', e.target.value)}
                                style={{ width: 150 }}
                              />
                              <Input
                                placeholder="표시 레이블"
                                value={field.field_label}
                                onChange={(e) => handleFieldChange(field.id, 'field_label', e.target.value)}
                                style={{ width: 150 }}
                              />
                              <Select
                                value={field.field_type}
                                onChange={(value) => handleFieldChange(field.id, 'field_type', value)}
                                style={{ width: 120 }}
                              >
                                {fieldTypes.map(type => (
                                  <Option key={type.value} value={type.value}>
                                    {type.label}
                                  </Option>
                                ))}
                              </Select>
                              <Switch
                                checked={field.is_required}
                                onChange={(checked) => handleFieldChange(field.id, 'is_required', checked)}
                                checkedChildren="필수"
                                unCheckedChildren="선택"
                              />
                            </Space>

                            {field.field_type === 'select' && (
                              <div className="field-options">
                                <Input
                                  placeholder="선택 옵션 (쉼표로 구분)"
                                  value={field.field_options?.choices?.join(', ') || ''}
                                  onChange={(e) => handleFieldChange(field.id, 'field_options', {
                                    choices: e.target.value.split(',').map(s => s.trim()).filter(s => s)
                                  })}
                                  style={{ marginTop: 8 }}
                                />
                              </div>
                            )}

                            <div className="field-preview">
                              <label>{field.field_label || '레이블'} {field.is_required && <span style={{ color: 'red' }}>*</span>}</label>
                              {renderFieldPreview(field)}
                            </div>
                          </div>
                        </Card>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        </div>
      </Form>
    </Modal>
  );
};

export default OrderFormBuilder;
