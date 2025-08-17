import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from '../components/Sidebar';
import './MainLayout.css';

const MainLayout = ({ children }) => {


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