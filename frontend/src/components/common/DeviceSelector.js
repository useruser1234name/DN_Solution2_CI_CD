import React, { useState, useEffect } from 'react';
import { Select, Spin, message, Row, Col } from 'antd';
import { get } from '../../services/api';
import './DeviceSelector.css';

const { Option } = Select;

const DeviceSelector = ({ 
  modelValue, 
  colorValue,
  onModelChange, 
  onColorChange,
  disabled = false,
  allowClear = true,
  onDeviceSelect = null // 기기 선택 시 추가 콜백
}) => {
  const [models, setModels] = useState([]);
  const [colors, setColors] = useState([]);
  const [loadingModels, setLoadingModels] = useState(false);
  const [loadingColors, setLoadingColors] = useState(false);

  // 기기 모델 로드
  const loadDeviceModels = async () => {
    setLoadingModels(true);
    try {
      const response = await get('/api/policies/device-models/?is_active=true');
      if (response.success) {
        setModels(response.data || []);
      } else {
        message.error('기기 모델 정보를 불러오는데 실패했습니다.');
        setModels([]);
      }
    } catch (error) {
      console.error('기기 모델 로드 오류:', error);
      message.error('기기 모델 정보를 불러오는 중 오류가 발생했습니다.');
      setModels([]);
    } finally {
      setLoadingModels(false);
    }
  };

  // 기기 색상 로드
  const loadDeviceColors = async (modelId) => {
    if (!modelId) {
      setColors([]);
      return;
    }

    setLoadingColors(true);
    try {
      const response = await get(`/api/policies/device-colors/?device_model=${modelId}&is_active=true`);
      if (response.success) {
        setColors(response.data || []);
      } else {
        message.error('기기 색상 정보를 불러오는데 실패했습니다.');
        setColors([]);
      }
    } catch (error) {
      console.error('기기 색상 로드 오류:', error);
      message.error('기기 색상 정보를 불러오는 중 오류가 발생했습니다.');
      setColors([]);
    } finally {
      setLoadingColors(false);
    }
  };

  // 컴포넌트 마운트 시 기기 모델 로드
  useEffect(() => {
    loadDeviceModels();
  }, []);

  // 모델 변경 시 색상 로드
  useEffect(() => {
    loadDeviceColors(modelValue);
  }, [modelValue]);

  // 모델 변경 시 선택된 색상 초기화
  useEffect(() => {
    if (colorValue && modelValue) {
      // 현재 선택된 색상이 새로운 모델의 색상인지 확인
      const currentColor = colors.find(color => color.id === colorValue);
      if (!currentColor) {
        onColorChange(null);
      }
    }
  }, [modelValue, colors, colorValue, onColorChange]);

  const handleModelChange = (modelId, option) => {
    onModelChange(modelId);
    
    // 선택된 모델 정보를 부모 컴포넌트에 전달
    if (onDeviceSelect && option) {
      const modelData = models.find(model => model.id === modelId);
      onDeviceSelect({ type: 'model', data: modelData });
    }
  };

  const handleColorChange = (colorId, option) => {
    onColorChange(colorId);
    
    // 선택된 색상 정보를 부모 컴포넌트에 전달
    if (onDeviceSelect && option) {
      const colorData = colors.find(color => color.id === colorId);
      onDeviceSelect({ type: 'color', data: colorData });
    }
  };

  const formatModelOption = (model) => {
    return `${model.manufacturer} ${model.model_name}`;
  };

  const formatColorOption = (color) => {
    return (
      <div className="color-option">
        <span className="color-name">{color.color_name}</span>
        {color.color_code && (
          <span 
            className="color-preview" 
            style={{ backgroundColor: color.color_code }}
            title={color.color_code}
          />
        )}
      </div>
    );
  };

  return (
    <div className="device-selector">
      <Row gutter={16}>
        <Col xs={24} sm={12}>
          <div className="device-model-selector">
            <label className="selector-label">기기 모델</label>
            <Select
              value={modelValue}
              onChange={handleModelChange}
              placeholder="기기 모델을 선택하세요"
              disabled={disabled || loadingModels}
              allowClear={allowClear}
              loading={loadingModels}
              showSearch
              filterOption={(input, option) =>
                option.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
              }
              style={{ width: '100%' }}
              notFoundContent={loadingModels ? <Spin size="small" /> : '기기 모델이 없습니다'}
            >
              {models.map(model => (
                <Option key={model.id} value={model.id} title={model.description}>
                  {formatModelOption(model)}
                </Option>
              ))}
            </Select>
          </div>
        </Col>
        
        <Col xs={24} sm={12}>
          <div className="device-color-selector">
            <label className="selector-label">기기 색상</label>
            <Select
              value={colorValue}
              onChange={handleColorChange}
              placeholder={modelValue ? "색상을 선택하세요" : "먼저 기기 모델을 선택하세요"}
              disabled={disabled || !modelValue || loadingColors}
              allowClear={allowClear}
              loading={loadingColors}
              showSearch
              filterOption={(input, option) =>
                option.props.children.props.children[0].props.children.toLowerCase().indexOf(input.toLowerCase()) >= 0
              }
              style={{ width: '100%' }}
              notFoundContent={loadingColors ? <Spin size="small" /> : '색상이 없습니다'}
            >
              {colors.map(color => (
                <Option key={color.id} value={color.id}>
                  {formatColorOption(color)}
                </Option>
              ))}
            </Select>
          </div>
        </Col>
      </Row>
      
      {modelValue && colors.length === 0 && !loadingColors && (
        <div className="no-colors-message">
          해당 모델의 색상이 등록되지 않았습니다.
        </div>
      )}
    </div>
  );
};

export default DeviceSelector;

