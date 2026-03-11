import Link from 'next/link';
import { LayoutDashboard, Lightbulb, Zap, BookOpen, MessageSquare } from 'lucide-react';

const Sidebar = () => {
  const links = [
    { href: '/', label: 'Dashboard', icon: <LayoutDashboard size={20} /> },
    { href: '/insights', label: 'Model Insights', icon: <Lightbulb size={20} /> },
    { href: '/what-if', label: 'What-If Analysis', icon: <Zap size={20} /> },
    { href: '/explanation', label: 'Scientific Science', icon: <BookOpen size={20} /> },
    { href: '/assistant', label: 'AI Assistant', icon: <MessageSquare size={20} /> },
  ];

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col h-screen fixed left-0 top-0 border-r border-gray-800">
      <div className="p-6">
        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-green-400 bg-clip-text text-transparent">
          Delhi AQI System
        </h1>
      </div>
      <nav className="flex-1 mt-4">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className="flex items-center gap-4 px-6 py-4 hover:bg-gray-800 transition-colors border-l-4 border-transparent hover:border-blue-500"
          >
            {link.icon}
            <span>{link.label}</span>
          </Link>
        ))}
      </nav>
      <div className="p-6 border-t border-gray-800 text-sm text-gray-400">
        &copy; 2026 AI Predict
      </div>
    </aside>
  );
};

export default Sidebar;
