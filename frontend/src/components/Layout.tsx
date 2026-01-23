import React from 'react';
import { Header } from './Header';

interface LayoutProps {
    children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
    return (
        <div className="flex h-screen bg-gray-50 dark:bg-zinc-950 overflow-hidden font-sans">
            <div className="flex-1 flex flex-col overflow-hidden">
                <Header />
                <main className="flex-1 overflow-hidden p-4 md:p-6 lg:p-8 relative bg-zinc-50/50 dark:bg-zinc-950">
                    <div className="w-full h-full flex flex-col min-h-0">
                        {children}
                    </div>
                </main>
            </div>
        </div>
    );
};
