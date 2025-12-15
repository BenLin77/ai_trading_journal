'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { t } from '@/lib/i18n';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FileSearch,
  Target,
  FileBarChart,
  FlaskConical,
  Lightbulb,
  Bot,
  AlertCircle,
  Settings,
  ChevronLeft,
  BookOpen,
} from 'lucide-react';

const navItems = [
  { href: '/', icon: LayoutDashboard, labelKey: 'nav_dashboard' as const },
  { href: '/review', icon: FileSearch, labelKey: 'nav_review' as const },
  { href: '/journal', icon: BookOpen, labelKey: 'nav_journal' as const },
  { href: '/strategy', icon: Target, labelKey: 'nav_strategy' as const },
  { href: '/report', icon: FileBarChart, labelKey: 'nav_report' as const },
  { href: '/lab', icon: FlaskConical, labelKey: 'nav_lab' as const },
  { href: '/options', icon: Lightbulb, labelKey: 'nav_options' as const },
  { href: '/ai', icon: Bot, labelKey: 'nav_ai' as const },
];

export function Sidebar() {
  const pathname = usePathname();
  const { language, sidebarOpen, setSidebarOpen } = useAppStore();

  return (
    <aside
      className={cn(
        'fixed left-0 top-16 z-40 h-[calc(100vh-4rem)] border-r border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-950 transition-all duration-300',
        sidebarOpen ? 'w-64' : 'w-16'
      )}
    >
      {/* Toggle Button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="absolute -right-3 top-6 z-50 flex h-6 w-6 items-center justify-center rounded-full border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 shadow-sm hover:bg-gray-50 dark:hover:bg-gray-700"
      >
        <ChevronLeft
          className={cn(
            'h-4 w-4 text-gray-500 transition-transform',
            !sidebarOpen && 'rotate-180'
          )}
        />
      </button>

      {/* Navigation */}
      <nav className="flex flex-col gap-1 p-3">
        <div className={cn('mb-4 px-3 text-xs font-semibold uppercase text-gray-500', !sidebarOpen && 'hidden')}>
          {t('misc_navigation', language)}
        </div>

        {navItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                  : 'text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800',
                !sidebarOpen && 'justify-center'
              )}
              title={!sidebarOpen ? t(item.labelKey, language) : undefined}
            >
              <Icon className="h-5 w-5 flex-shrink-0" />
              {sidebarOpen && <span>{t(item.labelKey, language)}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Settings at bottom */}
      <div className="absolute bottom-4 left-0 right-0 px-3">
        <Link
          href="/settings"
          className={cn(
            'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors',
            !sidebarOpen && 'justify-center'
          )}
          title={!sidebarOpen ? t('settings_maintenance', language) : undefined}
        >
          <Settings className="h-5 w-5 flex-shrink-0" />
          {sidebarOpen && <span>{t('settings_maintenance', language)}</span>}
        </Link>
      </div>
    </aside>
  );
}
