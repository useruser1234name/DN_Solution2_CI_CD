/**
 * 커스텀 모달 컴포넌트
 * 모든 다이얼로그의 기본 구조 제공
 */

import React from 'react';
import { Modal, Button, Space } from 'antd';
import './CustomModal.css';

const CustomModal = ({
  title,
  open,
  onCancel,
  onOk,
  children,
  width = 800,
  okText = '확인',
  cancelText = '취소',
  okButtonProps = {},
  cancelButtonProps = {},
  loading = false,
  destroyOnClose = true,
  maskClosable = false,
  footer = null,
  customFooter = false,
  ...props
}) => {
  // 기본 푸터
  const defaultFooter = [
    <Button key="cancel" onClick={onCancel} {...cancelButtonProps}>
      {cancelText}
    </Button>,
    <Button
      key="ok"
      type="primary"
      loading={loading}
      onClick={onOk}
      {...okButtonProps}
    >
      {okText}
    </Button>,
  ];

  return (
    <Modal
      title={title}
      open={open}
      onCancel={onCancel}
      width={width}
      destroyOnClose={destroyOnClose}
      maskClosable={maskClosable}
      footer={customFooter ? footer : defaultFooter}
      className="custom-modal"
      {...props}
    >
      {children}
    </Modal>
  );
};

export default CustomModal;

