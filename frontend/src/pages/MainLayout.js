import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import './MainLayout.css';

const MainLayout = ({ children }) => {
    console.log('[MainLayout] 컴포넌트 렌더링');

    return (
        <div className="main-layout">
            <Sidebar />
            <div className="main-content">
                {children || <Outlet />}
            </div>
        </div>
    );
};

export default MainLayout; 