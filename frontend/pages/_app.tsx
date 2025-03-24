import '@/styles/globals.css';
import type { AppProps } from 'next/app';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { NotificationProvider } from '@/contexts/NotificationContext';
import { OnboardingProvider } from '@/contexts/OnboardingContext';
import { ShortcutProvider } from '@/contexts/ShortcutContext';

export default function App({ Component, pageProps }: AppProps) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <NotificationProvider>
          <ShortcutProvider>
            <OnboardingProvider>
              <AuthProvider>
                <Component {...pageProps} />
              </AuthProvider>
            </OnboardingProvider>
          </ShortcutProvider>
        </NotificationProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
